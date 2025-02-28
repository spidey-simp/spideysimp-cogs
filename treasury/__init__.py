from redbot.core.bot import Red

from .treasury import Treasury

async def setup(bot: Red) -> None:
    cog = Treasury(bot)
    await bot.add_cog(cog)