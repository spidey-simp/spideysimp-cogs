from .spideyutils import SpideyUtils

async def setup(bot):
    cog = SpideyUtils(bot)
    await bot.add_cog(cog)