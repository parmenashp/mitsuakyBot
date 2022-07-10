import os

import tomli

DEFAULT_FILE_LOCATION = "./config.toml"


class BotConfig:
    __slots__ = {"token", "prefix", "initial_extensions"}

    def __init__(self, toml_value):
        self.token = os.environ["DISCORD_TOKEN"]
        self.prefix = toml_value.get("prefix", ",,")
        self.initial_extensions = toml_value.get("initial_extensions", [])


class KarmaConfig:
    __slots__ = {"channels"}

    def __init__(self, toml_value):
        self.channels = toml_value.get("channels", [])


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
