from redbot.core.bot import Red

from .languify import Languify

async def setup(bot: Red) -> None:
    cog = Languify(bot)
    await bot.add_cog(cog)