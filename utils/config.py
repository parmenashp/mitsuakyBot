import os

import tomli

DEFAULT_FILE_LOCATION = "./config.toml"


class BotConfig:
    __slots__ = {"token", "prefix"}

    def __init__(self, toml_value):
        self.token = os.environ["DISCORD_TOKEN"]
        self.prefix = toml_value.get("prefix", ",,")
        self.initial_extensions = toml_value.get("initial_extensions", [])


class DatabaseConfig:
    __slots__ = {"username", "password", "name"}

    username = os.getenv("POSTGRES_USERNAME")
    password = os.getenv("POSTGRES_PASSWORD")
    database_name = os.getenv("POSTGRES_DB_NAME")


class Config:
    __slots__ = {"bot", "db"}

    def __init__(self, toml_path: str = DEFAULT_FILE_LOCATION) -> None:
        with open(toml_path, "rb") as f:
            self.toml_values = tomli.load(f)

        self.db = DatabaseConfig
        self.bot = BotConfig(self.toml_values["bot"])
