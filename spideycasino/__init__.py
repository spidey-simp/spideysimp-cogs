
from redbot.core.bot import Red

from .spideycasino import SpideyCasino

async def setup(bot: Red) -> None:
    cog = SpideyCasino(bot)
    await bot.add_cog(cog)

