import os
import re

import asyncpg
from discord import PartialEmoji
from loguru import logger
import json

import prisma

DEFAULT_FILE_LOCATION = "./config.toml"

# Regex for validate and extract discord custom emoji from a string.
CUSTOM_EMOJI_REGEX = re.compile(r"<?(?P<animated>a)?:?(?P<name>[A-Za-z0-9\_]+):(?P<id>[0-9]{13,20})>?")

SNOWFLAKE_REGEX = re.compile(r"[0-9]{15,20}")


def get_emoji(emoji: str, defult: str) -> PartialEmoji:
    """Try to get a custom emoji from `emoji` string,
    if it's not a custom emoji then return the `defult` emoji."""

    if re.match(CUSTOM_EMOJI_REGEX, emoji):
        return PartialEmoji.from_str(emoji)

    return PartialEmoji.from_str(defult)


class BotConfig:
    def __init__(self) -> None:
        self.token = os.environ["DISCORD_TOKEN"]
        self.prefix = os.environ["DISCORD_PREFIX"]
        self.initial_extensions: list[str] = json.loads(os.environ["INITIAL_EXTENSIONS"])
        self.upvote_emoji = get_emoji(os.environ["UPVOTE_EMOJI"], "⬆️")
        self.downvote_emoji = get_emoji(os.environ["DOWNVOTE_EMOJI"], "⬇️")
        self.dev_guild_id = os.environ["DEV_GUILD_ID"]


class DatabaseConfig:
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_DSN")


class GuildConfigManager:
    def __init__(self, db: prisma.Prisma):
        self._guilds = {}
        self._prisma = db

    async def load_config(self):
        """Initialize the guild config manager and load/reload
        the configs per guild from the database."""

        guildconfigs = await self._prisma.guildconfig.find_many()
        for guildconfig in guildconfigs:
            self._guilds[guildconfig.guild_id] = guildconfig

    def _get_guild_config(self, guild_id):
        if guild_id in self._guilds:
            return self._guilds[guild_id]
        return prisma.models.GuildConfig(guild_id=guild_id, karma_channels=[])

    def __getitem__(self, guild_id) -> prisma.models.GuildConfig:
        if not re.fullmatch(SNOWFLAKE_REGEX, str(guild_id)):
            raise ValueError(f"Invalid guild id: {guild_id}")

        return self._get_guild_config(guild_id)


class Config:
    def __init__(self) -> None:
        self.ready = False
        self.db = DatabaseConfig()
        self.bot = BotConfig()

    async def initialize(self, db: prisma.Prisma):
        """Initialize all the configs from the environment variables and database."""
        self._prisma = db
        self.guild = GuildConfigManager(db)
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
