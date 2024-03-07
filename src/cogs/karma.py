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

    @app_commands.command()
    async def karma(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        """
        Get the karma of a user.
        """

        if member is None:
            user = interaction.user
        else:
            user = member

        prisma_user = await self.bot.prisma.user.find_unique(where={"id": user.id}, include={"karma": True})
        if hasattr(prisma_user, "karma"):
            karma = sum(message.upvotes - message.downvotes for message in prisma_user.karma)  # type: ignore
        else:
            karma = 0

        await interaction.response.send_message(
            f"{user.mention} tem {karma} de karma.",
            allowed_mentions=discord.AllowedMentions.none(),  # avoid ping the user
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        if message.channel.id not in self.bot.config.guild[message.guild.id].karma_channels:
            return
        if message.author.bot:
            return
        if not (message.attachments or message.content.startswith(("https://", "http://"))):
            return

        await message.add_reaction(self.bot.config.bot.upvote_emoji)
        await message.add_reaction(self.bot.config.bot.downvote_emoji)

        # Prisma "createOrUpdate" is not implemented yet, I need to do this manually
        # check https://github.com/RobertCraigie/prisma-client-py/issues/754

        await self.bot.prisma.user.upsert(
            where={"id": message.author.id},
            data={"create": {"id": message.author.id}, "update": {}},
        )

        await self.bot.prisma.channel.upsert(
            where={"id": message.channel.id},
            data={"create": {"id": message.channel.id}, "update": {}},
        )

        await self.bot.prisma.karmamessage.create(
            data={
                "message_id": message.id,
                "author_id": message.author.id,
                "channel_id": message.channel.id,
            }
        )

        logger.info(f"Added karma reactions to {message.id!r} by {message.author.name} on channel #{message.channel}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if payload.channel_id not in self.bot.config.guild[payload.guild_id].karma_channels:
            return
        if payload.member is None:
            return
        if payload.member.bot:
            return

        if payload.emoji == self.bot.config.bot.upvote_emoji:
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

        elif payload.emoji == self.bot.config.bot.downvote_emoji:
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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if payload.channel_id not in self.bot.config.guild[payload.guild_id].karma_channels:
            return
        # TODO: Get the user from the cache to check if it's a bot

        if payload.emoji == self.bot.config.bot.upvote_emoji:
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
        elif payload.emoji == self.bot.config.bot.downvote_emoji:
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


async def setup(bot: "MitBot"):
    await bot.add_cog(Karma(bot))
