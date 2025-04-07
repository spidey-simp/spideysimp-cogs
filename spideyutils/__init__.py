from .spideyutils import SpideyUtils, RequestRoll

async def setup(bot):
    await bot.add_cog(SpideyUtils(bot))
    await bot.add_cog(RequestRoll(bot))