from redbot.core.bot import Red

from .fandomsearch import FandomSearch

async def setup(bot: Red) -> None:
    cog = FandomSearch(bot)
    await bot.add_cog(cog)