"""Slash commands for the TopServersDiscord bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
import structlog
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.client import TSDBot

log = structlog.get_logger()


class Commands(commands.Cog):
    """Public slash commands."""

    def __init__(self, bot: TSDBot) -> None:
        self.bot = bot

    # -- /info -----------------------------------------------------------------

    @app_commands.command(name="info", description="Learn about TopServersDiscord")
    async def info(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="TopServersDiscord",
            description=(
                "TopServersDiscord helps you discover, rank, and promote Discord servers.\n\n"
                "We track public server statistics like member count, activity, and boost level "
                "to build leaderboards and detailed server profiles.\n\n"
                "**Privacy:** We never read or store message content."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Website",
            value="[topserversdiscord.com](https://topserversdiscord.com)",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    # -- /stats ----------------------------------------------------------------

    @app_commands.command(name="stats", description="Show stats for this server")
    @app_commands.guild_only()
    async def stats(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None  # guaranteed by guild_only

        online_count = sum(
            1 for m in guild.members if m.status is not discord.Status.offline and not m.bot
        )

        embed = discord.Embed(
            title=f"Stats for {guild.name}",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Online", value=str(online_count), inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)

        await interaction.response.send_message(embed=embed)

    # -- /verify ---------------------------------------------------------------

    @app_commands.command(
        name="verify",
        description="Register this server with TopServersDiscord",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def verify(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        assert guild is not None

        # Extra runtime check for manage_guild
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the **Manage Server** permission to register this server.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Registering your server with TopServersDiscord...",
            ephemeral=True,
        )

        from bot.backend.client import BackendClient

        backend = BackendClient()
        try:
            ok = await backend.notify_guild_joined(guild)
        finally:
            await backend.close()

        if ok:
            await interaction.edit_original_response(
                content=(
                    "Your server has been registered! Visit "
                    "https://topserversdiscord.com/dashboard to customize your listing."
                ),
            )
        else:
            await interaction.edit_original_response(
                content="Registration failed. Please try again or contact support.",
            )

    # -- /settings -------------------------------------------------------------

    @app_commands.command(
        name="settings",
        description="View bot settings for this server",
    )
    @app_commands.guild_only()
    async def settings(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Settings",
            description=(
                "Settings will be available soon. "
                "Visit the [dashboard](https://topserversdiscord.com/dashboard) "
                "to configure tracking."
            ),
            color=discord.Color.greyple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: TSDBot) -> None:
    await bot.add_cog(Commands(bot))
