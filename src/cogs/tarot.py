import asyncio
from datetime import datetime
import glob
import random
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger
from PIL import Image
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from src.main import MitBot


class Cartas(commands.Cog):

    def __init__(self, bot: "MitBot"):
        self.bot = bot
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.loop = asyncio.get_event_loop()

    async def cog_load(self) -> None:
        logger.info("Loading Tarot cog")
        self.loop.run_in_executor(self.executor, self.load_cards)

    async def cog_unload(self) -> None:
        logger.info("Unloading Tarot cog")

    def load_cards(self):
        Card = TypedDict("Card", {"name": str, "image": Image.Image})
        self.cards: list[Card] = []
        for card_file in glob.glob("./cards/*.png"):
            card_name = card_file.split("/")[-1].split(".")[0].title()
            card_image = Image.open(card_file)
            self.cards.append({"name": card_name, "image": card_image})

    @app_commands.command(
        name="tarot",
        description="Receba uma leitura de tarot",
    )
    @app_commands.describe(cartas="número de cartas a serem tiradas")
    async def tarot(self, interaction: discord.Interaction, cartas: Literal[1, 2, 3, 4, 5] = 3):
        def concat_images(im_list: list[Image.Image]):
            min_height = min(im.height for im in im_list)
            im_list_resize = [im.resize((int(im.width * min_height / im.height), min_height)) for im in im_list]
            total_width = sum(im.width for im in im_list_resize)
            dst = Image.new("RGBA", (total_width, min_height))
            pos_x = 0
            for im in im_list_resize:
                dst.paste(im, (pos_x, 0))
                pos_x += im.width
            return dst

        if cartas not in range(1, 6):  # 1 2 3 4 5
            return await interaction.response.send_message("O número de cartas deve estar entre 1 e 5", ephemeral=True)

        # Silly random seed to link the random number to the user
        random.seed(random.randint(-interaction.user.id, interaction.user.id) + datetime.now().microsecond)

        base_probability = 0.50
        variance = 0.05
        adjustment = random.uniform(-variance, variance)
        dynamic_probability = base_probability + adjustment

        final_cards = []
        final_names = []
        for card in random.sample(self.cards, cartas):
            final_names.append(card["name"])
            if random.random() < dynamic_probability:
                final_cards.append(card["image"].transpose(Image.Transpose.ROTATE_180))
            else:
                final_cards.append(card["image"])

        buffer = BytesIO()
        await self.loop.run_in_executor(self.executor, lambda: concat_images(final_cards).save(buffer, format="PNG"))
        buffer.seek(0)

        await interaction.response.send_message(
            file=discord.File(buffer, filename="resultado.png"), content=", ".join(final_names)
        )


async def setup(bot):
    await bot.add_cog(Cartas(bot))
