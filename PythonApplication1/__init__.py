from redbot.core.bot import Red

from .[your code file] import [the class you have your commands in]


async def setup(bot: Red) -> None:
    cog = [classname](bot)
    await bot.add_cog(cog)

