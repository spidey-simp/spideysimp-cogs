from .spideyeconomy import SpideyEconomy

from redbot.core.bot import Red

async def setup(bot: Red) -> None:
    cog = SpideyEconomy(bot)
    await bot.add_cog(cog)