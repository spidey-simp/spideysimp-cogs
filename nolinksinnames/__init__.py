from redbot.core.bot import Red

from .nolinksinnames import NoLinksInNames

async def setup(bot: Red) -> None:
    cog = NoLinksInNames(bot)
    await bot.add_cog(cog)