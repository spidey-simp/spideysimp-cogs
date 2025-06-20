from .statusset import StatusSet

from redbot.core.bot import Red

async def setup(bot: Red) -> None:
    cog = StatusSet(bot)
    await bot.add_cog(cog)