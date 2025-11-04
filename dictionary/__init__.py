from redbot.core.bot import Red

from .dictionary import Dictionary

async def setup(bot: Red) -> None:
    cog = Dictionary(bot)
    await bot.add_cog(cog)