from redbot.core.bot import Red

from .spideylifesim import SpideyLifeSim


async def setup(bot: Red) -> None:
    cog = SpideyLifeSim(bot)
    await bot.add_cog(cog)