from redbot.core.bot import Red

from .smashorpass import SmashOrPass

async def setup(bot: Red) -> None:
    cog = SmashOrPass(bot)
    await bot.add_cog(cog)