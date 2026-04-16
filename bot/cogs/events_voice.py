from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.ingest.schema import DiscordEvent
from bot.utils.hashing import hash_user

if TYPE_CHECKING:
    from bot.client import TSDBot


class EventsVoice(commands.Cog):
    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        guild_id = member.guild.id
        user_h = hash_user(member.id, guild_id)
        now = datetime.now(UTC)

        # Left a channel (or moved away)
        if before.channel is not None and before.channel != after.channel:
            self.bot.emitter.emit(
                DiscordEvent(
                    ts=now,
                    event_type="voice_leave",
                    guild_id=guild_id,
                    channel_id=before.channel.id,
                    user_hash=user_h,
                )
            )

        # Joined a channel (or moved into)
        if after.channel is not None and after.channel != before.channel:
            self.bot.emitter.emit(
                DiscordEvent(
                    ts=now,
                    event_type="voice_join",
                    guild_id=guild_id,
                    channel_id=after.channel.id,
                    user_hash=user_h,
                )
            )


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(EventsVoice(bot))
