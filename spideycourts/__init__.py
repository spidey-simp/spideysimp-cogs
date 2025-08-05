from redbot.core.bot import Red

from .spideycourts import SpideyCourts

async def setup(bot: Red) -> None:
    cog = SpideyCourts(bot)
    await bot.add_cog(cog)