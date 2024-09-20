import enum
from typing import TYPE_CHECKING

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger


if TYPE_CHECKING:
    from src.main import MitBot

MAX_AGE_SECONDS = 60 * 60 * 24  # 1 day

# ####################################################
# For this cog to work, the bot needs,
# besides the defualt permissions, theses permissions:
# Manage Channels
# Manage Guild
# Create Invites

REQUIRED_PERMISSIONS = discord.Permissions(
    manage_channels=True,
    manage_guild=True,
    create_instant_invite=True,
)


class InviteNotFound(Exception):  # Unessential, but I like it.
    pass


class VerifyRoles(enum.Enum):
    FURRY = enum.auto()
    FURRY_MINOR = enum.auto()
    NON_FURRY = enum.auto()


class GiveVerifyRole(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.role: VerifyRoles
        self.verifier: discord.Member

    @discord.ui.button(label="Furry")
    async def furry_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.role = VerifyRoles.FURRY
        assert isinstance(interaction.user, discord.Member)
        self.verifier: discord.Member = interaction.user
        self.stop()

    @discord.ui.button(label="Furry -18")
    async def furry_minor_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.role = VerifyRoles.FURRY_MINOR
        assert isinstance(interaction.user, discord.Member)
        self.verifier: discord.Member = interaction.user
        self.stop()

    @discord.ui.button(label="Non-furry")
    async def non_furry_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.role = VerifyRoles.NON_FURRY
        assert isinstance(interaction.user, discord.Member)
        self.verifier: discord.Member = interaction.user
        self.stop()


class Invite(commands.Cog):
    def __init__(self, bot: "MitBot") -> None:
        self.bot = bot
        self.invites: dict[int, list[discord.Invite]] = {}
        self.lock = asyncio.Lock()
        self.ready = False

    async def cog_load(self) -> None:
        logger.info("Loading Invite cog")

    async def cog_unload(self) -> None:
        logger.info("Unloading Invite cog")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.ready:
            return

        self.ready = True
        logger.debug("Caching invites")
        for guild in self.bot.guilds:
            await self._update_invite_cache(guild)

        self.musky_guild = self.bot.get_guild(self.bot.settings.musky.guild_id)
        if self.musky_guild:
            self.role_furry = self.musky_guild.get_role(self.bot.settings.musky.furry_role_id)
            if not self.role_furry:
                return logger.error("Furry role not found")
            self.role_furry_minor = self.musky_guild.get_role(self.bot.settings.musky.furry_minor_role_id)
            if not self.role_furry_minor:
                return logger.error("Furry -18 role not found")
            self.role_non_furry = self.musky_guild.get_role(self.bot.settings.musky.non_furry_role_id)
            if not self.role_non_furry:
                return logger.error("Non-furry role not found")
        else:
            return logger.warning("Musky guild not found")

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

        await self.bot.prisma.invite.create(
            data={
                "code": invite.code,
                "inviter_id": interaction.user.id,
            }
        )

        await interaction.response.send_message(
            f"Created a new invite valid for 1 day with 1 use.\n{invite.url}",
            ephemeral=True,
        )

    async def _update_invite_cache(self, guild: discord.Guild) -> None:
        try:
            if guild.unavailable:
                return logger.debug(f"Guild {guild.name} is unavailable, skipping invite cache update")
            self.invites[guild.id] = await guild.invites()
            logger.debug(f"Updated cached invites for guild {guild.name}")
        except discord.HTTPException:
            if not guild.me.guild_permissions > REQUIRED_PERMISSIONS:
                logger.warning(f"Bot does not have the required permissions to cache invites for guild {guild.name}")
                return

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

    async def find_inviter(self, after: list[discord.Invite], guild_id: int) -> discord.User | None:
        # In case of invites that reached the max uses, the invite doesn't exist anymore
        # So we need to check if after the member joined the guild, the invite still exists
        invite_diff: set[discord.Invite] = set(self.invites[guild_id]).difference(after)
        if len(invite_diff) == 1:
            invite = invite_diff.pop()
            if invite.inviter != self.bot.user:
                return invite.inviter

            db_invite = await self.bot.prisma.invite.delete(where={"code": invite.code})
            if db_invite is None:
                return
            return self.bot.get_user(db_invite.inviter_id)

        # If the invite still present, we use the other method to find the invite
        # Check which invite has a different uses count than the invite in the cache
        for invite in after:
            try:
                if invite.uses < self.find_invite_by_code(invite.code, guild_id).uses:  # type: ignore
                    return invite.inviter

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
            guild = self.bot.settings.guilds.get(member.guild.id)
            if guild is None or guild.invite_log_channel_id is None:
                return

            inviter: discord.User | None
            if member.guild.id in self.invites:
                invites_after = await member.guild.invites()
                inviter = await self.find_inviter(invites_after, member.guild.id)
                self.invites[member.guild.id] = invites_after
                if inviter is not None and inviter is not None:
                    logger.info(f"Member {member.name} joined in {member.guild.name} invited by {inviter.name}")
                else:
                    logger.info(f"Member {member.name} joined in {member.guild.name} but could not resolve inviter")

            embed = discord.Embed(color=discord.Colour.green())
            embed.set_thumbnail(url=member.display_avatar.with_static_format("png"))
            embed.title = "Member joined"
            embed.description = (
                f"{member.mention} joined the guild.\n\n" f"Invited by {inviter.mention if inviter else 'unknown'}"
            )

            channel = self.bot.get_channel(guild.invite_log_channel_id)
            if not isinstance(channel, discord.TextChannel):
                return logger.warning(f"Invite log channel not found or not a text channel in {member.guild.name}")

            if member.guild != self.musky_guild:
                await channel.send(embed=embed)
                return

            view = GiveVerifyRole()
            embed.set_footer(text="Select a role to verify the user:")
            message = await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
            await view.wait()
            if view.role == VerifyRoles.FURRY:
                role = self.role_furry
            elif view.role == VerifyRoles.FURRY_MINOR:
                role = self.role_furry_minor
            elif view.role == VerifyRoles.NON_FURRY:
                role = self.role_non_furry
            else:
                return logger.error("Invalid role selected in the view")

            if role is None:
                await channel.send("[Error] Role not found in the guild", delete_after=10)
                logger.error("Role not found in the musky guild")
            elif role in member.roles:
                await channel.send(
                    f"Member {member.mention} already has the role {role.mention}",
                    delete_after=10,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                logger.info(f"Member {member.name} already has the role {role.name} in {member.guild.name}")
            else:
                logger.info(
                    f"Member {member.name} verified as {role.name} by {view.verifier.name} in {member.guild.name}"
                )
                await member.add_roles(role, reason=f"User verified by {view.verifier.name}")
                embed.description += f"\nVerified by: {view.verifier.mention} as {role.mention}"
            embed.remove_footer()
            await message.edit(embed=embed, view=None, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: "MitBot") -> None:
    await bot.add_cog(Invite(bot))
