from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.ingest.schema import DiscordEvent
from bot.utils.hashing import hash_user

if TYPE_CHECKING:
    from bot.client import TSDBot


class EventsMessages(commands.Cog):
    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if message.author.bot:
            return

        event = DiscordEvent(
            ts=datetime.now(UTC),
            event_type="message",
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            user_hash=hash_user(message.author.id, message.guild.id),
        )
        self.bot.emitter.emit(event)


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(EventsMessages(bot))
