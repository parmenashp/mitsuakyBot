from typing import TYPE_CHECKING

import asyncio
import asyncpg
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger


if TYPE_CHECKING:
    from bot import MitBot

MAX_AGE_SECONDS = 60 * 60 * 24  # 1 day

# ####################################################
# For this cog to work, the bot needs,
# besides the defualt permissions, theses permissions:
# Manage Channels
# Manage Guild
# Create Invites


class InviteNotFound(Exception):  # Unessential, but I like it.
    pass


class Invite(commands.Cog):
    def __init__(self, bot: "MitBot") -> None:
        self.bot = bot
        self.invites: dict[int, list[discord.Invite]] = {}
        self.lock = asyncio.Lock()
        self.ready = False

    async def cog_load(self) -> None:
        # Cache the invites for resolving which invite a member used to join a server
        logger.info("cogs.invite loaded")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.ready:
            return

        self.ready = True
        logger.debug("Caching invites")
        for guild in self.bot.guilds:
            await self._update_invite_cache(guild)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(create_instant_invite=True)
    async def invite(self, interaction: discord.Interaction) -> None:
        """Create a new invite for this channel valid for 1 day and with 1 use."""
        if isinstance(interaction.channel, discord.TextChannel):
            channel = interaction.channel
        elif isinstance(interaction.channel, discord.Thread):
            channel = interaction.channel.parent
        else:
            return

        # check if the bot has the permission to create an invite
        if not interaction.channel.permissions_for(interaction.guild.me).create_instant_invite:  # type: ignore
            return await interaction.response.send_message(
                "The bot does not have permission to create invites here.",
                ephemeral=True,
            )
        # check if the user has the permission to create invites
        if not interaction.channel.permissions_for(interaction.user).create_instant_invite:  # type: ignore
            return await interaction.response.send_message(
                "You do not have permission to create invites here.", ephemeral=True
            )

        if channel is None:
            # I don't think this will happen, but it's better to be safe
            return await interaction.response.send_message(
                "Something went wrong. Try again in a different channel",
                ephemeral=True,
            )

        invite = await channel.create_invite(max_age=MAX_AGE_SECONDS, max_uses=1)

        await interaction.response.send_message(
            f"Created a new invite valid for 1 day with 1 use.\n{invite.url}",
            ephemeral=True,
        )

    async def _update_invite_cache(self, guild: discord.Guild) -> None:
        try:
            self.invites[guild.id] = await guild.invites()
            logger.debug(f"Updated cached invites for guild {guild.name}")
        except discord.HTTPException:
            logger.warning(f"Failed to cache invites for guild {guild.name}")

    async def _handle_invite_change(self, invite: discord.Invite):
        if invite.guild is not None:
            guild = self.bot.get_guild(invite.guild.id)
            if guild is not None:
                await self._update_invite_cache(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        logger.debug(f"Invite created: {invite.code} for guild {invite.guild}")
        await self._handle_invite_change(invite)

    def find_invite_by_code(self, code: str, guild_id: int) -> discord.Invite:
        try:
            for invite in self.invites[guild_id]:
                if invite.code == code:
                    return invite
        except KeyError:
            pass  # No invites cached for this guild, treat as not found

        raise InviteNotFound("An invite with this code was not found")

    def find_used_invite(
        self, after: list[discord.Invite], guild_id: int
    ) -> discord.Invite | None:
        # In case of invites that reached the max uses, the invite doesn't exist anymore
        # So we need to check if after the member joined the guild, the invite still exists
        invite = set(self.invites[guild_id]).difference(after)
        if len(invite) == 1:
            return invite.pop()

        # If the invite still present, we use the other method to find the invite
        # Check which invite has a different uses count than the invite in the cache
        for invite in after:
            try:
                if invite.uses < self.find_invite_by_code(invite.code, guild_id).uses:  # type: ignore
                    return invite

            except InviteNotFound:
                continue

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        # This is a complicated situation. When a invite reaches the max uses, it is deleted
        # and triggers this event. But the thing is, discord send the delete_invite event before
        # the event of a member joining the guild, so if we update the cache here, before processing
        # the member join event, the invite will be missing. The easy solution i found that fits my needs
        # is to wait a bit before updating the cache to wait for the member join event to be processed.
        logger.debug(
            f"Invite deleted: {invite.code} for guild {invite.guild}, waiting for potential member join event"
        )
        await asyncio.sleep(1)
        await self._handle_invite_change(invite)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        async with self.lock:
            try:
                channel_id = self.bot.config.guild[member.guild.id].invite_log_channel
            except AttributeError:
                return

            inviter = None
            if member.guild.id in self.invites:
                invites_after = await member.guild.invites()
                used_invite = self.find_used_invite(invites_after, member.guild.id)
                self.invites[member.guild.id] = invites_after
                if used_invite is not None and used_invite.inviter is not None:
                    inviter = used_invite.inviter
                    logger.info(
                        f"Member {member.name} joined in {member.guild.name} invited by {inviter.name}"
                    )
                else:
                    logger.info(
                        f"Member {member.name} joined in {member.guild.name} but could not resolve inviter"
                    )

            embed = discord.Embed(color=discord.Colour.green())
            embed.set_thumbnail(url=member.display_avatar.with_static_format("png"))
            embed.title = "Member joined"
            embed.description = (
                f"{member.mention} joined the guild.\n\n"
                f"Invited by {inviter.mention if inviter else 'unknown'}"
            )

            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)


async def setup(bot: "MitBot") -> None:
    await bot.add_cog(Invite(bot))
