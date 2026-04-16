from __future__ import annotations

from datetime import UTC, datetime

import discord
from discord.ext import commands

from bot.ingest.schema import DiscordEvent
from bot.utils.hashing import hash_user

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.client import TSDBot


class EventsMembers(commands.Cog):
    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        self.bot.emitter.emit(
            DiscordEvent(
                ts=datetime.now(UTC),
                event_type="member_join",
                guild_id=member.guild.id,
                channel_id=0,
                user_hash=hash_user(member.id, member.guild.id),
            )
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.bot:
            return

        self.bot.emitter.emit(
            DiscordEvent(
                ts=datetime.now(UTC),
                event_type="member_leave",
                guild_id=member.guild.id,
                channel_id=0,
                user_hash=hash_user(member.id, member.guild.id),
            )
        )


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(EventsMembers(bot))
