"""Guild join/leave lifecycle events."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
import structlog
from discord.ext import commands

from bot.backend.client import BackendClient

if TYPE_CHECKING:
    from bot.client import TSDBot

log = structlog.get_logger()


class GuildLifecycle(commands.Cog):
    """Handles guild join and remove events."""

    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot
        self._backend = BackendClient()

    async def cog_unload(self) -> None:
        await self._backend.close()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info(
            "guild.joined",
            guild_id=guild.id,
            name=guild.name,
            member_count=guild.member_count,
        )
        await self._backend.notify_guild_joined(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        log.info(
            "guild.removed",
            guild_id=guild.id,
            name=guild.name,
        )
        await self._backend.notify_guild_left(guild.id)


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(GuildLifecycle(bot))
