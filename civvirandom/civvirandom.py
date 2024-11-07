from __future__ import annotations
import discord
import logging
import random
from random import choice
import aiohttp
from typing import Dict, List, Literal, Optional, Any, NoReturn
from abc import ABC
from discord import Member

from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.commands import Cog
from redbot.core.i18n import Translator

from .civleaderlist import LEADERLIST

log = logging.getLogger("red.spideysimp-cogs.SwgohTools")



async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.json()

class CivVIrandom(Cog):
    """Pick a random Civ VI leader using the following commands!"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=684457913250480143, force_registration=True)
        

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return
    
    @commands.group(aliases=["civr"])
    async def civvirandom(self, ctx: commands.Context):
        """Civ VI random generates a random leader based on the filter you apply."""
        pass

    @civvirandom.command(name="index", aliases=["i"])
    async def civvirandom_index(self, ctx: commands.Context):
        """See the full list of leaders selectable."""
        indexseparator = "\n- "
        await ctx.send(f"```The full Civ VI Leader list is:\n- {indexseparator.join(LEADERLIST.keys())}```")

    @civvirandom.command(name="fulllist", aliases=["fl"])
    async def civvirandom_fulllist(self, ctx: commands.Context):
        """Get a random leader selected from the full list."""
        civtitle = "Your Civilization VI leader generation has generated:"
        civresult, civimage = random.choice(list(LEADERLIST.items()))

        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(civimage, ssl=False) as response:
                assert response.status == 200



        em = discord.Embed(
            title=civtitle, description=civresult, color=discord.Color.red(), url=civimage
        )
        em.set_image(url=civimage)
        await ctx.send(embed=em)
