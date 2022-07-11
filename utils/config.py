import os
from discord import PartialEmoji
import tomli
import re

DEFAULT_FILE_LOCATION = "./config.toml"

# Regex for validate and extract discord custom emoji from a string.
CUSTOM_EMOJI_REGEX = re.compile(
    r"<?(?P<animated>a)?:?(?P<name>[A-Za-z0-9\_]+):(?P<id>[0-9]{13,20})>?"
)


def extract_emoji(emoji_str: str, emoji_name: str) -> PartialEmoji:
    """Extract an emoji from a string, returning a `PartialEmoji` object.
    If the string is not a valid emoji, then it raises a ValueError."""
    match = CUSTOM_EMOJI_REGEX.match(emoji_str)
    if match is not None:
        groups = match.groupdict()
        animated = bool(groups["animated"])
        emoji_id = int(groups["id"])
        name = groups["name"]
        return PartialEmoji(name=name, animated=animated, id=emoji_id)

    raise ValueError(f"Invalid config emoji string for emoji {emoji_name}")


class BotConfig:
    __slots__ = {"token", "prefix", "initial_extensions"}

    def __init__(self, toml_value):
        self.token = os.environ["DISCORD_TOKEN"]
        self.prefix = toml_value.get("prefix", ",,")
        self.initial_extensions = toml_value.get("initial_extensions", [])


class KarmaConfig:
    __slots__ = {"channels", "upvote_emoji", "downvote_emoji"}

    def __init__(self, toml_value):
        self.channels = toml_value.get("channels", [])
        self.upvote_emoji = extract_emoji(
            toml_value.get("upvote_emoji"), "upvote_emoji"
        )
        self.downvote_emoji = extract_emoji(
            toml_value.get("downvote_emoji"), "downvote_emoji"
        )


class DatabaseConfig:
    __slots__ = {"username", "password", "database_name"}

    def __init__(self):
        self.username = os.getenv("POSTGRES_USERNAME")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.database_name = os.getenv("POSTGRES_DB_NAME")


class Config:
    __slots__ = {"toml_values", "bot", "db", "karma"}

    def __init__(self, toml_path: str = DEFAULT_FILE_LOCATION) -> None:
        with open(toml_path, "rb") as f:
            self.toml_values = tomli.load(f)

        self.db = DatabaseConfig()
        self.bot = BotConfig(self.toml_values["bot"])
        self.karma = KarmaConfig(self.toml_values["karma"])
