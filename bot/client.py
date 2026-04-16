import discord
import structlog
from discord.ext import commands

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
