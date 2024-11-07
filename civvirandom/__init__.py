from redbot.core.bot import Red

from .civvirandom import CivVIrandom


async def setup(bot: Red) -> None:
    cog = CivVIrandom(bot)
    await bot.add_cog(cog)