from .spideygov import SpideyGov

from redbot.core.bot import Red

async def setup(bot: Red) -> None:
    cog = SpideyGov(bot)
    await bot.add_cog(cog)
