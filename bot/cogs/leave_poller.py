"""Periodically poll the backend for guilds the bot should leave.

Owners can delete their server listing from the dashboard; the backend
queues the guild ID and this cog makes the bot actually leave.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from discord.ext import commands, tasks

from bot.backend.client import BackendClient

if TYPE_CHECKING:
    from bot.client import TSDBot

log = structlog.get_logger()


class LeavePoller(commands.Cog):
    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot
        self._backend = BackendClient()
        self._poll.start()

    async def cog_unload(self) -> None:
        self._poll.cancel()
        await self._backend.close()

    @tasks.loop(seconds=60.0)
    async def _poll(self) -> None:
        guild_ids = await self._backend.fetch_pending_leaves()
        for gid in guild_ids:
            guild = self.bot.get_guild(gid)
            if guild is None:
                log.info("leave_poller.guild_not_found", guild_id=gid)
                continue
            try:
                await guild.leave()
                log.info("leave_poller.left", guild_id=gid, name=guild.name)
            except Exception:
                log.exception("leave_poller.leave_failed", guild_id=gid)

    @_poll.before_loop
    async def _before_poll(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(LeavePoller(bot))
