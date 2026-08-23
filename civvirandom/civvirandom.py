from __future__ import annotations

import discord
import random

from redbot.core import commands
from redbot.core.commands import Cog

from .civleaderlist import LEADERLIST, CHALLENGELIST

log = logging.getLogger("red.spideysimp-cogs.CivVIRandom")


class CivVIrandom(Cog):
    """Pick a random Civ VI leader using the following commands!"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return
    
    @commands.group(aliases=["civr"], invoke_without_command=True)
    async def civvirandom(self, ctx: commands.Context):
        """Civ VI random generates a random leader or challenge."""
        await ctx.send_help()

    @civvirandom.command(name="index", aliases=["i"])
    async def civvirandom_index(self, ctx: commands.Context):
        """See the full list of leaders selectable."""
        indexseparator = "\n- "
        await ctx.send(f"```The full Civ VI Leader list is:\n- {indexseparator.join(LEADERLIST.keys())}```")

    @civvirandom.command(name="fulllist", aliases=["fl"])
    @commands.bot_has_permissions(embed_links=True)
    async def civvirandom_fulllist(self, ctx: commands.Context):
        """Get a random leader selected from the full list."""
        civtitle = "Your Civilization VI leader generation has generated:"
        civresult, civimage = random.choice(list(LEADERLIST.items()))


        em = discord.Embed(
            title=civtitle, description=civresult, color=discord.Color.red(), url=civimage
        )
        em.set_image(url=civimage)
        await ctx.send(embed=em)

    @civvirandom.command(name="challenge", aliases=["c"])
    @commands.bot_has_permissions(embed_links=True)
    async def civvirandom_challenge(self, ctx: commands.Context):
        """Get a random challenge to try in the game!"""
        civtitle, civresult = random.choice(list(CHALLENGELIST.items()))

        em = discord.Embed(
            title=civtitle, description=civresult, color=discord.Color.red()
        )
        await ctx.send(embed=em)
