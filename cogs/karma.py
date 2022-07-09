from typing import TYPE_CHECKING
from discord.ext import commands
import discord

if TYPE_CHECKING:
    from bot import MitBot


class Karma(commands.Cog):
    def __init__(self, bot: MitBot) -> None:
        self.bot = bot


async def setup(bot: MitBot):
    await bot.add_cog(Karma(bot))
