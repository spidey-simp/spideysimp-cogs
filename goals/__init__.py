from .goals import Goals

from redbot.core.bot import Red

async def setup(bot: Red) -> None:
    cog = Goals(bot)
    await bot.add_cog(cog)