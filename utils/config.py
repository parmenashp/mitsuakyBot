import os
import re

import asyncpg
from discord import PartialEmoji
from loguru import logger

DEFAULT_FILE_LOCATION = "./config.toml"

# Regex for validate and extract discord custom emoji from a string.
CUSTOM_EMOJI_REGEX = re.compile(
    r"<?(?P<animated>a)?:?(?P<name>[A-Za-z0-9\_]+):(?P<id>[0-9]{13,20})>?"
)

SNOWFLAKE_REGEX = re.compile(r"[0-9]{15,20}")


def get_emoji(emoji_key: str, defult: str, data: dict) -> PartialEmoji:
    """Return an `PartialEmoji` from the value of key if it exists in the data.
    If the string is not a valid custom emoji, then it uses the default emoji."""
    value: str | None = data.get(emoji_key)
    if value:
        if re.match(CUSTOM_EMOJI_REGEX, value):
            return PartialEmoji.from_str(value)

    return PartialEmoji.from_str(defult)


class BotConfig:
    def __init__(self, data: dict) -> None:
        self.token = os.environ["DISCORD_TOKEN"]
        self.prefix = os.getenv("DISCORD_PREFIX", ",,")
        self.initial_extensions: list[str] | None = data.get("initial_extensions")
        self.upvote_emoji = get_emoji("upvote_emoji", "⬆️", data)
        self.downvote_emoji = get_emoji("downvote_emoji", "⬇️", data)
        self.dev_guild_id = data.get("dev_guild_id")


class DatabaseConfig:
    def __init__(self):
        self.username = os.getenv("POSTGRES_USER")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.database_name = os.getenv("POSTGRES_DB")
        self.host = os.getenv("POSTGRES_HOST")
        self.port = os.getenv("POSTGRES_PORT")


class GuildConfig:
    def __init__(self, record: dict):
        self.karma_channels: list[int | None] = record.get("karma_channels", [])
        self.invite_log_channel: int = record.get("invite_log_channel", None)


class GuildConfigManager:
    def __init__(self, pool: asyncpg.pool.Pool):
        self._guilds = {}
        self._pool = pool

    async def load_config(self):
        """Initialize the guild config manager and load/reload
        the configs per guild from the database."""
        async with self._pool.acquire() as conn:
            records = await conn.fetch("SELECT * FROM guilds_config")
            for record in records:
                self._guilds[record["guild_id"]] = GuildConfig(record)

    def _get_guild_config(self, guild_id):
        if guild_id in self._guilds:
            return self._guilds[guild_id]
        return GuildConfig({})  # No custom config, use default config.

    def __getitem__(self, guild_id):
        if not re.fullmatch(SNOWFLAKE_REGEX, str(guild_id)):
            raise ValueError(f"Invalid guild id: {guild_id}")

        return self._get_guild_config(guild_id)


class Config:
    def __init__(self) -> None:
        self.ready = False
        self.db = DatabaseConfig()
        self.bot = BotConfig({})

    async def initialize(self, pool: asyncpg.pool.Pool):
        """Initialize all the configs from the environment variables and database."""
        self._pool = pool
        self.guild = GuildConfigManager(pool)
        await self._load_config()
        self.ready = True

    async def reload(self):
        """Tries to reload the all the configs."""
        if not self.ready:
            logger.error("Config not ready but trying to reload it")
            return
        await self._load_config()

    async def _load_config(self):
        await self.guild.load_config()
        async with self._pool.acquire() as conn:
            conn: asyncpg.Connection
            record: dict | None = await conn.fetchrow("SELECT * FROM bot_config")
            if not record:
                raise ValueError("No bot config found in database.")
            self.bot = BotConfig(record)
