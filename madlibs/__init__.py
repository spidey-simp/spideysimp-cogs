from redbot.core.bot import Red

from .madlibs import MadLibs

async def setup(bot: Red) -> None:
    cog = MadLibs(bot)
    await bot.add_cog(cog)