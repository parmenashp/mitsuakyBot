import os
import re
from typing import Annotated, Dict, Generic, Tuple, Type, TypeVar

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource
from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, ValidationError, field_validator
import discord

from loguru import logger

DEFAULT_FILE_LOCATION = "./settings.toml"
SNOWFLAKE_REGEX = re.compile(r"[0-9]{15,20}")


def validate_snowflake_id(snowflake_id: int) -> int:
    if not SNOWFLAKE_REGEX.fullmatch(str(snowflake_id)):
        raise ValidationError("Invalid snowflake ID")
    return snowflake_id


Snowflake = Annotated[int, AfterValidator(validate_snowflake_id)]

PartialEmoji = Annotated[
    discord.PartialEmoji,
    BeforeValidator(lambda x: discord.PartialEmoji.from_str(x)),
]


class BotSettings(BaseModel):
    token: str = "TOKEN"
    initial_extensions: list[str]


class MuskySettings(BaseModel):
    guild_id: Snowflake
    furry_role_id: Snowflake
    furry_minor_role_id: Snowflake
    non_furry_role_id: Snowflake

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


class GuildSettings(BaseModel):
    invite_log_channel_id: Snowflake | None = None
    karma_channels_ids: list[Snowflake] = []

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


class EmojiSettings(BaseModel):
    upvote: PartialEmoji = discord.PartialEmoji.from_str("⬆️")
    downvote: PartialEmoji = discord.PartialEmoji.from_str("⬇️")

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


class Settings(BaseSettings):
    bot: BotSettings
    musky: MuskySettings
    guilds: dict[Snowflake, GuildSettings]
    emojis: EmojiSettings

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        env_nested_delimiter="__",
        toml_file=DEFAULT_FILE_LOCATION,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )
