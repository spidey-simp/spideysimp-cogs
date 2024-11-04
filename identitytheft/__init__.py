from .identitytheft import IdentityTheft


async def setup(bot):
    cog = IdentityTheft(bot)
    await bot.add_cog(cog)