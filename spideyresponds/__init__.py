from .spideyresponds import SpideyResponds

async def setup(bot):
    await bot.add_cog(SpideyResponds(bot))