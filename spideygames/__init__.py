from redbot.core.bot import Red

from .spideygames import SpideyGames

async def setup(bot: Red) -> None:
    cog = SpideyGames(bot)
    await bot.add_cog(cog)