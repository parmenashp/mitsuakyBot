from discord.ext import commands
import discord


# Custom commands.Context
class MitsuakyContext(commands.Context):
    async def tick(self, value):
        """
        Reacts to a message with a tick emoji depending on the `value`.
        If `value` is True, with ✅, otherwise with a ❌.
        """
        emoji = "\N{WHITE HEAVY CHECK MARK}" if value else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            # sometimes errors occur during this, for example
            # maybe you dont have permission to do that, so whatever
            pass
