from .swgohtools import SwgohTools


async def setup(bot):
    await bot.add_cog(SwgohTools(bot))