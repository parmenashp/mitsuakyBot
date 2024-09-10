from typing import TYPE_CHECKING

import discord
from discord import RawReactionActionEvent, app_commands
from discord.ext import commands
from loguru import logger

if TYPE_CHECKING:
    from src.main import MitBot


class Karma(commands.Cog):
    def __init__(self, bot: "MitBot") -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        logger.info("Loading Karma cog")

    async def cog_unload(self) -> None:
        logger.info("Unloading Karma cog")

    @app_commands.command()
    async def karma(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        """Get the karma of a user."""
        if member is None:
            user = interaction.user
        else:
            user = member

        logger.info(f"Retrieving karma for user {user.name}")
        messages = await self.bot.prisma.karmamessage.find_many(
            where={
                "author_id": user.id,
            },
        )
        sum_karma = sum([message.upvotes - message.downvotes for message in messages])

        await interaction.response.send_message(
            f"{user.mention} tem {sum_karma} de karma.",
            allowed_mentions=discord.AllowedMentions.none(),  # avoid ping the user
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if not (message.attachments or message.content.startswith(("https://", "http://"))):
            return
        if message.author.bot:
            return
        guild_settings = self.bot.settings.guilds.get(message.guild.id)
        if guild_settings is None or message.channel.id not in guild_settings.karma_channels_ids:
            return

        logger.info(
            f"Adding karma reactions to message {message.id!r} by {message.author.name} on channel #{message.channel}"
        )

        await message.add_reaction(self.bot.settings.emojis.upvote)
        await message.add_reaction(self.bot.settings.emojis.downvote)

        await self.bot.prisma.karmamessage.create(
            data={
                "message_id": message.id,
                "author_id": message.author.id,
                "channel_id": message.channel.id,
            }
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if payload.member is None:
            return
        if payload.member.bot:
            return
        guild_settings = self.bot.settings.guilds.get(payload.guild_id)
        if guild_settings is None or payload.channel_id not in guild_settings.karma_channels_ids:
            return

        if payload.emoji == self.bot.settings.emojis.upvote:
            karma_message = await self.bot.prisma.karmamessage.update_many(
                where={
                    "message_id": payload.message_id,
                    "author_id": {"not": payload.user_id},
                },
                data={
                    "upvotes": {"increment": 1},
                },
            )
            if karma_message > 0:
                logger.info(f"User {payload.member.name} upvoted message id {payload.message_id!r}")
            else:
                logger.info(f"User {payload.member.name} tried to upvote his own message id {payload.message_id!r}")

        elif payload.emoji == self.bot.settings.emojis.downvote:
            karma_message = await self.bot.prisma.karmamessage.update_many(
                where={
                    "message_id": payload.message_id,
                    "author_id": {"not": payload.user_id},
                },
                data={
                    "downvotes": {"increment": 1},
                },
            )
            if karma_message > 0:
                logger.info(f"User {payload.member.name} downvoted message id {payload.message_id!r}")
            else:
                logger.info(f"User {payload.member.name} tried to downvote his own message id {payload.message_id!r}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if payload.guild_id is None:
            return
        guild_settings = self.bot.settings.guilds.get(payload.guild_id)
        if guild_settings is None or payload.channel_id not in guild_settings.karma_channels_ids:
            return

        # To check if the user is bot, we need to get the member object. Won't be doing that here for now.

        if payload.emoji == self.bot.settings.emojis.upvote:
            karma_message = await self.bot.prisma.karmamessage.update_many(
                where={
                    "message_id": payload.message_id,
                    "author_id": {"not": payload.user_id},
                },
                data={
                    "upvotes": {"decrement": 1},
                },
            )
            if karma_message > 0:
                logger.info(f"User id {payload.user_id!r} removed upvote from message id {payload.message_id!r}")
            else:
                logger.info(
                    f"User id {payload.user_id!r} tried to remove upvote from his own message id {payload.message_id!r}"
                )

        elif payload.emoji == self.bot.settings.emojis.downvote:
            karma_message = await self.bot.prisma.karmamessage.update_many(
                where={
                    "message_id": payload.message_id,
                    "author_id": {"not": payload.user_id},
                },
                data={
                    "downvotes": {"decrement": 1},
                },
            )
            if karma_message > 0:
                logger.info(f"User id {payload.user_id!r} removed downvote from message id {payload.message_id!r}")
            else:
                logger.info(
                    f"User id {payload.user_id!r} tried to remove downvote from his own message id {payload.message_id!r}"
                )


async def setup(bot: "MitBot"):
    await bot.add_cog(Karma(bot))
