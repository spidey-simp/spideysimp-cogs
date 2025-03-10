from .spideystocks import SpideyStocks

async def setup(bot):
    cog = SpideyStocks(bot)
    await bot.add_cog(cog)