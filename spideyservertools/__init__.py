from redbot.core.bot import Red

from .spideyservertools import SpideyServerTools

async def setup(bot: Red) -> None:
    cog = SpideyServerTools(bot)
    await bot.add_cog(cog)