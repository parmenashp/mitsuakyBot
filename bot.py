import asyncio

import asyncpg
import discord
from aiohttp import ClientSession
from discord.ext import commands
from loguru import logger

from utils.config import Config
from utils.context import MitsuakyContext
from utils.logging import setup_logger


class MitBot(commands.Bot):
    def __init__(
        self,
        config: Config,
        db_pool: asyncpg.Pool,
        web_client: ClientSession,
    ):
        self.db_pool = db_pool
        self.web_client = web_client
        self.config = config

        allowed_mentions = discord.AllowedMentions(
            roles=False,
            everyone=False,
            users=True,
        )
        intents = discord.Intents.default()
        intents.invites = True
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(self.config.bot.prefix),
            pm_help=None,
            chunk_guilds_at_startup=False,
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True,
        )

    async def get_or_fetch_guild(self, guild_id: int) -> discord.Guild | None:
        """Looks up a guild in cache or fetches if not found.
        Parameters
        -----------
        guild_id: int
            The guild ID to search for.
        Returns
        ---------
        Optional[Guild]
            The guild or None if not found.
        """
        guild = self.get_guild(guild_id)
        if guild is not None:
            return guild

        if not self.is_ws_ratelimited():
            try:
                guild = await self.fetch_guild(guild_id)
            except discord.HTTPException:
                return None
            else:
                return guild

    async def get_or_fetch_member(
        self, guild: discord.Guild | int, member_id: int
    ) -> discord.Member | None:
        """Looks up a member in cache or fetches if not found.
        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.
        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """
        # Tries to get the guild if only guild id was passed
        if isinstance(guild, int):
            _guild = await self.get_or_fetch_guild(guild)
            if _guild is None:
                return None
            guild = _guild

        member = guild.get_member(member_id)
        if member is not None:
            return member

        if self.is_ws_ratelimited():
            try:
                # Get member from api
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member
        # Get member from websocket
        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    async def setup_hook(self):
        initial_extensions = self.config.bot.initial_extensions
        if initial_extensions:
            for extension in initial_extensions:
                try:
                    await self.load_extension(extension)
                except Exception:
                    logger.exception(f"Error while loading extension {extension}")

    async def on_ready(self):
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

    async def on_message(self, message: discord.Message) -> None:
        ctx = await self.get_context(message, cls=MitsuakyContext)
        await self.invoke(ctx)


async def main():
    setup_logger()  # setup loguru
    config = Config()
    pool_kwargs = {
        "user": config.db.username,
        "password": config.db.password,
        "database": config.db.database_name,
        "host": config.db.host,
        "port": config.db.port,
        "command_timeout": 30,
    }

    async with asyncpg.create_pool(**pool_kwargs) as pool:
        async with ClientSession() as aio_client:
            await config.initialize(pool)
            async with MitBot(config, pool, aio_client) as bot:
                # always load jishaku to have at least basic remote control/debug
                await bot.load_extension("jishaku")
                await bot.start(config.bot.token)


if __name__ == "__main__":
    asyncio.run(main())
