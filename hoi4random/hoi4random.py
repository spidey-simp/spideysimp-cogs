from __future__ import annotations

import random

import discord
from discord import app_commands
from redbot.core import commands

from .hoi4leaderlist import COUNTRYLIST, HISTORICAL_EMPIRES



alignment = [
    "Democratic",
    "Fascist",
    "Communist",
    "Authoritarian/Unaligned"
]

class Hoi4Random(commands.Cog):
    """Pick a random Hoi 4 leader using the following commands!"""

    def __init__(self, bot):
        self.bot = bot
        

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return
    
    hoi4random = app_commands.Group(name="hoi4random", description="Hoi 4 Random Leader Generator")

    @hoi4random.command(name="index", description="See the full list of leaders selectable.")
    async def index(self, interaction: discord.Interaction):
        """See the full list of leaders selectable."""
        indexseparator = "\n- "
        await interaction.response.send_message(f"```The full HOI 4 Leader list is:\n- {indexseparator.join(COUNTRYLIST.keys())}```")

    @hoi4random.command(name="random", description="Get a random leader from the full list.")
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def random(self, interaction: discord.Interaction):
        """Get a random leader selected from the full list."""
        civtitle = "Your Hearts of Iron IV leader generation has generated:"
        civresult, civimage = random.choice(list(COUNTRYLIST.items()))



        alignment_choice = random.choice(alignment)
        civresult += f"\n\n**Alignment:** {alignment_choice}"

        em = discord.Embed(
            title=civtitle, description=civresult, color=discord.Color.red()
        )
        if civimage:
            em.set_image(url=civimage)
        await interaction.response.send_message(embed=em)

    @hoi4random.command(name="empire_form", description="Get a random Empire to form.")
    @app_commands.checks.bot_has_permissions(embed_links=True)
    async def empire_form(self, interaction: discord.Interaction):
        """Get a random Empire to form."""
        empiretitle = "Your Hearts of Iron IV Empire generation has generated:"
        empire_result, empire_info = random.choice(list(HISTORICAL_EMPIRES.items()))
        empiretitle += f" **{empire_result}**"
        empire_description = empire_info.get("description", "No description available.")
        empire_image = empire_info.get("image", None)



        em = discord.Embed(
            title=empiretitle, description=empire_description, color=discord.Color.red()
        )
        if empire_image:
            em.set_image(url=empire_image)
        await interaction.response.send_message(embed=em)