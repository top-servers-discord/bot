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

    async def _create_invite(self, guild: discord.Guild) -> str | None:
        """Create a permanent invite for the guild's first available text channel."""
        for channel in guild.text_channels:
            try:
                perms = channel.permissions_for(guild.me)
                if perms.create_instant_invite:
                    invite = await channel.create_invite(
                        max_age=0,
                        max_uses=0,
                        unique=False,
                        reason="TopServersDiscord — permanent listing invite",
                    )
                    log.info("guild.invite_created", guild_id=guild.id, code=invite.code)
                    return invite.code
            except discord.Forbidden:
                continue
            except Exception:
                log.exception("guild.invite_error", guild_id=guild.id, channel_id=channel.id)
                continue
        log.warning("guild.no_invite_channel", guild_id=guild.id)
        return None

    def _collect_metadata(self, guild: discord.Guild) -> dict:
        """Collect server metadata for AI description generation."""
        categories = []
        for cat in guild.categories:
            channels = [ch.name for ch in cat.channels if isinstance(ch, discord.TextChannel)]
            categories.append({"name": cat.name, "channels": channels[:10]})

        uncategorized = [ch.name for ch in guild.text_channels if ch.category is None][:10]

        return {
            "name": guild.name,
            "description": guild.description or "",
            "member_count": guild.member_count,
            "categories": categories[:15],
            "uncategorized_channels": uncategorized,
            "features": list(guild.features)[:10],
            "premium_tier": guild.premium_tier,
            "preferred_locale": str(guild.preferred_locale),
        }

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info(
            "guild.joined",
            guild_id=guild.id,
            name=guild.name,
            member_count=guild.member_count,
        )

        invite_code = await self._create_invite(guild)
        metadata = self._collect_metadata(guild)

        await self._backend.notify_guild_joined(
            guild,
            invite_code=invite_code,
            metadata=metadata,
        )

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
