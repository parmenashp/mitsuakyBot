import discord
from discord.ext import commands
from utils.config import ConfigLoader


class MitBot(commands.Bot):
    def __init__(self, config: ConfigLoader):
        self.config = config
        allowed_mentions = discord.AllowedMentions(
            roles=False, everyone=False, users=True
        )
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned_or(self.config.bot["prefix"]),
            pm_help=None,
            chunk_guilds_at_startup=False,
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True,
        )
