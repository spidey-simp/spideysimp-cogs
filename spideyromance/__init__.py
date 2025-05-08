from redbot.core.bot import Red

from spideyromance import SpideyRomance

async def setup(bot: Red) -> None:
    cog = SpideyRomance(bot)
    await bot.add_cog(cog)
