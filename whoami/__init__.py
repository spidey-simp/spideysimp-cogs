from redbot.core.bot import Red

from .whoami import WhoAmI

async def setup(bot: Red) -> None:
    cog = WhoAmI(bot)
    await bot.add_cog(cog)