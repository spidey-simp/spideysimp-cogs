from .spideyrandom import SpideyRandom

from redbot.core.bot import Red

async def setup(bot: Red) -> None:
    cog = SpideyRandom(bot)
    await bot.add_cog(cog)