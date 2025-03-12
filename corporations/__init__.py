from .corporations import Corporations

async def setup(bot):
    cog = Corporations(bot)
    await bot.add_cog(cog)