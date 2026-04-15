import discord
import structlog
from discord.ext import commands

from bot.config import get_settings

log = structlog.get_logger()


def build_intents() -> discord.Intents:
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.messages = True
    intents.voice_states = True
    intents.reactions = True
    return intents


class TSDBot(commands.AutoShardedBot):
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

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info("bot.ready", user=str(self.user), guild_count=len(self.guilds))
