from redbot.core.bot import Red

from .thirtyyearswarrp import ThirtyYearsWarRP

async def setup(bot: Red) -> None:
    cog = ThirtyYearsWarRP(bot)
    await bot.add_cog(cog)