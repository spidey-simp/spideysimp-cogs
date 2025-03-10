from .spideynations import SpideyNations

async def setup(bot):
    cog = SpideyNations(bot)
    await bot.add_cog(cog)