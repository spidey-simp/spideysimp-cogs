from redbot.core.bot import Red

from .worldofapis import WorldOfApis

async def setup(bot: Red) -> None:
    cog = WorldOfApis(bot)
    await bot.add_cog(cog)