import asyncio

import discord
import structlog
from discord.ext import commands, tasks

from bot.config import get_settings
from bot.ingest.clickhouse_client import ClickHouseClient
from bot.ingest.emitter import EventEmitter

log = structlog.get_logger()

_COG_EXTENSIONS = [
    "bot.cogs.events_messages",
    "bot.cogs.events_voice",
    "bot.cogs.events_members",
    "bot.cogs.events_reactions",
    "bot.cogs.commands",
    "bot.cogs.guild_lifecycle",
    "bot.cogs.leave_poller",
]


def build_intents() -> discord.Intents:
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.messages = True
    intents.voice_states = True
    intents.reactions = True
    return intents


class TSDBot(commands.AutoShardedBot):
    ch_client: ClickHouseClient
    emitter: EventEmitter

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=build_intents(),
            shard_count=settings.shard_count,
            shard_ids=settings.shard_ids,
        )

    async def setup_hook(self) -> None:
        log.info("bot.setup_hook", shards=self.shard_count)

        # Initialize ClickHouse client and event emitter
        self.ch_client = ClickHouseClient()
        await self.ch_client.open()
        self.emitter = EventEmitter(self.ch_client)
        self.emitter.start()
        log.info("bot.emitter_started")

        # Load cogs — each wrapped so one failure doesn't block the rest
        for ext in _COG_EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info("bot.cog_loaded", extension=ext)
            except Exception:
                log.exception("bot.cog_load_failed", extension=ext)

        # Sync slash command tree with Discord
        try:
            synced = await self.tree.sync()
            log.info("bot.tree_synced", command_count=len(synced))
        except Exception:
            log.exception("bot.tree_sync_failed")

    async def close(self) -> None:
        log.info("bot.closing")
        # Flush remaining events before shutdown
        if hasattr(self, "emitter"):
            await self.emitter.stop()
            log.info("bot.emitter_stopped")
        if hasattr(self, "ch_client"):
            await self.ch_client.close()
            log.info("bot.clickhouse_closed")
        await super().close()

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info("bot.ready", user=str(self.user), guild_count=len(self.guilds))

        # Start rotating status
        if not self._rotate_status.is_running():
            self._rotate_status.start()

    @tasks.loop(seconds=15)
    async def _rotate_status(self) -> None:
        statuses = [
            discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servidores activos",
            ),
            discord.Activity(
                type=discord.ActivityType.playing,
                name="topserversdiscord.com",
            ),
            discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} active servers",
            ),
            discord.Activity(
                type=discord.ActivityType.listening,
                name="real-time stats",
            ),
            discord.Activity(
                type=discord.ActivityType.playing,
                name="topserversdiscord.com",
            ),
            discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{sum(g.member_count or 0 for g in self.guilds):,} members tracked",
            ),
        ]
        idx = int(asyncio.get_event_loop().time() / 15) % len(statuses)
        await self.change_presence(activity=statuses[idx])

        # Sync all existing guilds with backend on startup
        lifecycle_cog = self.get_cog("GuildLifecycle")
        if lifecycle_cog is not None:
            for guild in self.guilds:
                try:
                    # Reuse the guild_lifecycle cog's logic
                    invite_code = await lifecycle_cog._create_invite(guild)
                    metadata = lifecycle_cog._collect_metadata(guild)
                    await lifecycle_cog._backend.notify_guild_joined(
                        guild,
                        invite_code=invite_code,
                        metadata=metadata,
                    )
                    log.info("bot.guild_synced", guild_id=guild.id, name=guild.name)
                except Exception:
                    log.exception("bot.guild_sync_failed", guild_id=guild.id)
