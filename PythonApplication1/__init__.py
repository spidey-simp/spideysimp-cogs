from redbot.core.bot import Red

from .Duel import DuelManager


async def setup(bot: Red) -> None:
    cog = Duel(bot)
    await bot.add_cog(cog)

