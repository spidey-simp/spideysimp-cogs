from redbot.core.bot import Red

from .hoi4random import Hoi4Random


async def setup(bot: Red) -> None:
    cog = Hoi4Random (bot)
    await bot.add_cog(cog)