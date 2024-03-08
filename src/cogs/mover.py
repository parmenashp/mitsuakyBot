import asyncio
from discord.ext import commands
from discord import app_commands
from typing import TYPE_CHECKING
import discord

if TYPE_CHECKING:
    from src.main import MitBot


class Mover(commands.Cog):
    def __init__(self, bot: "MitBot") -> None:
        self.bot = bot

    @app_commands.command(
        name="move-all",
        description="Move all users from one voice channel to another.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def move_all(
        self,
        interaction: discord.Interaction,
        from_channel: discord.VoiceChannel,
        to_channel: discord.VoiceChannel,
    ):
        """
        Move all users from one voice channel to another.
        """
        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            return  # doing this so pyright stops whining.

        if from_channel is None:
            await interaction.response.send_message(
                "Origin channel not found.",
                ephemeral=True,
            )
            return

        if to_channel is None:
            await interaction.response.send_message(
                "Destination channel not found.",
                ephemeral=True,
            )
            return

        if from_channel == to_channel:
            await interaction.response.send_message(
                "Origin and destination channels are the same.",
                ephemeral=True,
            )
            return

        if not from_channel.members:
            await interaction.response.send_message(
                "Origin channel is empty.",
                ephemeral=True,
            )
            return

        if not to_channel.permissions_for(interaction.guild.me).move_members:
            await interaction.response.send_message(
                "I don't have permission to move members to the destination channel.",
                ephemeral=True,
            )
            return

        if (
            not from_channel.permissions_for(interaction.user).move_members
            or not to_channel.permissions_for(interaction.user).move_members
            or not from_channel.permissions_for(interaction.user).connect
            or not to_channel.permissions_for(interaction.user).connect
        ):
            await interaction.response.send_message(
                "You don't have enough permissions to move members between these channels.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Moving {len(from_channel.members)} members from {from_channel.mention} to {to_channel.mention}.",
            ephemeral=True,
        )

        total_members = len(from_channel.members)
        futures = [member.move_to(to_channel) for member in from_channel.members]
        results = await asyncio.gather(*futures, return_exceptions=True)

        moved_members = results.count(None)
        await interaction.edit_original_response(
            content=f"Moved {moved_members} of {total_members} members from {from_channel.mention} to {to_channel.mention}."
        )

        erros = []
        for i, result in enumerate(results):
            if isinstance(result, discord.errors.HTTPException):
                erros.append(f"{i+1} - {result.text}")
            elif isinstance(result, Exception):
                erros.append(f"{i+1} - {result}")

        if erros:
            await interaction.followup.send(
                f"While moving members, the following errors occurred:\n\n" + "\n".join(erros)
            )


async def setup(bot: "MitBot") -> None:
    await bot.add_cog(Mover(bot))
