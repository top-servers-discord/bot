from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.ingest.schema import DiscordEvent
from bot.utils.hashing import hash_user

if TYPE_CHECKING:
    from bot.client import TSDBot


class EventsReactions(commands.Cog):
    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return
        if payload.member is not None and payload.member.bot:
            return

        extra = json.dumps({"emoji": str(payload.emoji)})

        self.bot.emitter.emit(
            DiscordEvent(
                ts=datetime.now(UTC),
                event_type="reaction",
                guild_id=payload.guild_id,
                channel_id=payload.channel_id,
                user_hash=hash_user(payload.user_id, payload.guild_id),
                extra=extra,
            )
        )


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(EventsReactions(bot))
