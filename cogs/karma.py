from typing import TYPE_CHECKING

import asyncpg
import discord
from discord import RawReactionActionEvent, app_commands
from discord.ext import commands
from loguru import logger

if TYPE_CHECKING:
    from bot import MitBot


class Karma(commands.Cog):
    def __init__(self, bot: "MitBot") -> None:
        self.bot = bot

    @app_commands.command()
    async def karma(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        """
        Get the karma of a user.
        """
        async with self.bot.db_pool.acquire() as conn:
            conn: asyncpg.Connection
            if member is None:
                user = interaction.user
            else:
                user = member

            karma = await conn.fetchval(
                "SELECT SUM(upvotes - downvotes) FROM karma_messages WHERE author_id = $1",
                user.id,
            )

            if karma is None:
                # User not in the database, so don't have any karma
                karma = 0

            await interaction.response.send_message(
                f"{user.mention} tem {karma} karma.",
                allowed_mentions=discord.AllowedMentions.none(),  # avoid ping the user
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if (
            message.channel.id
            not in self.bot.config.guild[message.guild.id].karma_channels
        ):
            return
        if message.author.bot:
            return
        if not (
            message.attachments or message.content.startswith(("https://", "http://"))
        ):
            return

        await message.add_reaction(self.bot.config.bot.upvote_emoji)
        await message.add_reaction(self.bot.config.bot.downvote_emoji)

        async with self.bot.db_pool.acquire() as conn:
            conn: asyncpg.Connection
            await conn.execute(
                "INSERT INTO karma_messages (message_id, channel_id, author_id) VALUES ($1, $2, $3)",
                message.id,
                message.channel.id,
                message.author.id,
            )

        logger.info(f"Added karma reactions to {message.id}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if (
            payload.channel_id
            not in self.bot.config.guild[payload.guild_id].karma_channels
        ):
            return
        if payload.member is None:
            return
        if payload.member.bot:
            return

        if payload.emoji == self.bot.config.bot.upvote_emoji:
            async with self.bot.db_pool.acquire() as conn:
                conn: asyncpg.Connection
                await conn.execute(
                    "UPDATE karma_messages SET upvotes = upvotes + 1 WHERE message_id = $1 AND author_id != $2",
                    payload.message_id,
                    payload.user_id,
                )
            logger.info(f"{payload.member.name} upvoted message {payload.message_id}")
        elif payload.emoji == self.bot.config.bot.downvote_emoji:
            async with self.bot.db_pool.acquire() as conn:
                conn: asyncpg.Connection
                await conn.execute(
                    "UPDATE karma_messages SET downvotes = downvotes + 1 WHERE message_id = $1 AND author_id != $2",
                    payload.message_id,
                    payload.user_id,
                )
            logger.info(f"{payload.member.name} downvoted message {payload.message_id}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if (
            payload.channel_id
            not in self.bot.config.guild[payload.guild_id].karma_channels
        ):
            return
        if payload.guild_id is None:
            return

        if payload.emoji == self.bot.config.bot.upvote_emoji:
            async with self.bot.db_pool.acquire() as conn:
                conn: asyncpg.Connection
                # To not allow users to remove their own upvote, we need to check if the user is the author of the message.
                # Because of discord limitations we don't have the message nor the author class in the payload,
                # so we need to do this check via SQL. We could just fetch the message and the author, but this is
                # unnecessary for my use and would be a small performance hit.
                await conn.execute(
                    "UPDATE karma_messages SET upvotes = upvotes - 1 WHERE message_id = $1 AND author_id != $2",
                    payload.message_id,
                    payload.user_id,
                )
            logger.debug(
                f"User id {payload.user_id} removed upvote from message id {payload.message_id}"
            )
        elif payload.emoji == self.bot.config.bot.downvote_emoji:
            async with self.bot.db_pool.acquire() as conn:
                conn: asyncpg.Connection
                await conn.execute(
                    "UPDATE karma_messages SET downvotes = downvotes - 1 WHERE message_id = $1 AND author_id != $2",
                    payload.message_id,
                    payload.user_id,
                )
            logger.debug(
                f"User id {payload.user_id} removed downvote from message id {payload.message_id}"
            )


async def setup(bot: "MitBot"):
    await bot.add_cog(Karma(bot))
