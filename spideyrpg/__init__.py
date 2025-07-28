from redbot.core.bot import Red

from .spideyrpg import SpideyRPG

async def setup(bot: Red) -> None:
    cog = SpideyRPG(bot)
    await bot.add_cog(cog)