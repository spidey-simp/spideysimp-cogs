from __future__ import annotations
import discord
import asyncio
import logging
from dataclasses import make_dataclass
from typing import Dict, List, Literal, Optional, Tuple, Type, Union
from abc import ABC, ABCMeta, abstractmethod
from discord import Member
from discord import app_commands
from typing import Any, NoReturn
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import BadArgument, Cog, CogMeta, Context, Converter
from redbot.core.config import Config


EMOJIS = {
    "ccbs": "<:CCB:1336246037140082759>",  
    "bw": "<:BW:1336246065778786388>",
    "ct": "<:CT:1336246096405594142>",
    "grid_sd": "<:FSD:1336246292665466900>",
    "radar_sd": "<:ISD:1336246308020817932>",
    "tube_sd": "<:FlSD:1336246318418624512>",
    "ah": "<:AH:1336246115133165660>",
    "ec": "<:EC:1336246132681998438>",
    "z": "<:ZC:1336246154861744182>",
    "a": "<:A_:1336246216958152766>",
    "id": "<:ID:1336246197765017610>",
    "gk": "<:GK:1336246251598909483>",
    "db": "<:DB:1336246278568280101>"
}

RELIC_MATERIALS = {
    1: {"ccbs": 40},
    2: {"ccbs": 70, "bw": 40, "grid_sd": 15},
    3: {"ccbs": 100, "bw": 80, "ct": 20, "grid_sd": 35, "radar_sd": 15},
    4: {"ccbs": 130, "bw": 120, "ct": 60, "grid_sd": 55, "radar_sd": 40},
    5: {"ccbs": 160, "bw": 160, "ct": 90, "ah": 20, "grid_sd": 75, "radar_sd": 65, "tube_sd": 15},
    6: {"ccbs": 180, "bw": 190, "ct": 120, "ah": 40, "ec": 20, "grid_sd": 95, "radar_sd": 90, "tube_sd": 40},
    7: {"ccbs": 200, "bw": 220, "ct": 140, "ah": 60, "ec": 40, "z": 10, "grid_sd": 115, "radar_sd": 115, "tube_sd": 75},
    8: {"ccbs": 200, "bw": 220, "ct": 160, "ah": 80, "ec": 60, "z": 30, "a": 20, "id": 20, "grid_sd": 135, "radar_sd": 140, "tube_sd": 120},
    9: {"ccbs": 200, "bw": 220, "ct": 180, "ah": 100, "ec": 80, "z": 50, "a": 40, "id": 40, "gk": 20, "db": 20, "grid_sd": 165, "radar_sd": 170, "tube_sd": 175}
}



log = logging.getLogger("red.spideysimp-cogs.SwgohTools")


async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.json()

class SwgohTools(commands.Cog):
    """
    Swgoh Tools!
    
    This Cog includes some Swgoh tools to make it easier to plan farming.
    """

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=684457913250480143, force_registration=True)
        
        default_user = {
            "tbstar": 0,
            "getcurrency": False,
            "zeffo": False,
            "mandalore": False,
            "twgp": 0,
            "energy": 0,
            "abcompletion": 0
        }
        self.config.register_user(**default_user)


        
    async def red_delete_data_for_user(
        self, 
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester not in ("discord_deleted_user", "user"):
            return
        
        await self.config.user_from_id(user_id).clear()
    

    @commands.group()
    async def swgohtools(self, ctx: commands.Context):
        """Swgoh Tools is a cog with multiple tools for the game Star Wars: Galaxy of Heroes. It is currently a work in progress."""          
        pass
    
    @swgohtools.command(name="tbstar", aliases=["tbs"])
    async def swgohtools_tbstarset(self, ctx: commands.Context, star: int = 0):
        """Sets the amount of stars your guild gets in tb. - Only supports rote stars right now."""
        await self.config.user(ctx.author).tbstar.set(star)
        await ctx.send(f"Your territory battle stars are now set to {star} stars")

    @swgohtools.command(name="getspending", aliases=["gs"])
    async def swgohtools_getspending(self, ctx: commands.Context, geton: bool = True):
        """Toggles if you are using guild event tokens toward kyro spending. Add either true or false as a parameter."""
        await self.config.user(ctx.author).getcurrency.set(geton)
        await ctx.send(f"GET currency spending on kyros is now set to {geton}")

    @swgohtools.command(name="zeffo", aliases=["z"])
    async def swgohtools_zeffoset(self, ctx: commands.Context, zeffoon: bool = True):
        """Toggles if you have zeffo unlocked."""
        await self.config.user(ctx.author).zeffo.set(zeffoon)
        await ctx.send(f"You have set your zeffo completion to: {zeffoon}")

    @swgohtools.command(name="mandalore", aliases=["m"])
    async def swgohtools_mandaloreset(self, ctx: commands.Context, mandalorecompletion: bool = True):
        """Toggles if you have mandalore unlocked. Add either true or false as a parameter."""
        await self.config.user(ctx.author).mandalore.set(mandalorecompletion)
        await ctx.send(f"You have set your mandalore competion to: {mandalorecompletion}")
    
    @swgohtools.command(name="twgp")
    async def swgohtools_twgpset(self, ctx: commands.Context, twgpnumber: int = 0):
        """Sets the active territory war gp that your guild has. Input just what x would be in the following expression: tw gp = x million"""
        await self.config.user(ctx.author).twgp.set(twgpnumber)
        await ctx.send(f"Your active territory war gp is now {twgpnumber} million.")

    @swgohtools.command(name="energyspent", aliases=["es"])
    async def swgohtools_kyroenergy(self, ctx: commands.Context, energyamt: int = 0):
        """Sets how much energy you spend per day on kyros."""
        await self.config.user(ctx.author).energy.set(energyamt)
        await ctx.send(f"You are now spending {energyamt} campaign energy on kyros per day.")
    
    @swgohtools.command(name="abcompletion", aliases=["abc"])
    async def swgohtools_abcompletion(self, ctx: commands.Context, abamt: int = 0):
        """Sets how many of the Challenge Tier 1s you have completed for assault battles."""
        await self.config.user(ctx.author).abcompletion.set(abamt)
        await ctx.send(f"You have the setting of {abamt} assault battles completed.")

    @swgohtools.command(name="kyrocalc", aliases=["kc"])
    async def swgohtools_kyrocalc(self, ctx: commands.Context):
        """Kyro Calc calculates how many kyros a user gain in a month. Change the settings before using it."""
        tbstar = await self.config.user(ctx.author).tbstar()
        getcurrency = await self.config.user(ctx.author).getcurrency()
        zeffo = await self.config.user(ctx.author).zeffo()
        mandalore = await self.config.user(ctx.author).mandalore()
        twgp = await self.config.user(ctx.author).twgp()
        energy = await self.config.user(ctx.author).energy()
        abcompletion = await self.config.user(ctx.author).abcompletion()

        if tbstar == 0:
            tbkyrobox = 0
        elif tbstar <= 5:
            tbkyrobox = 22
        elif tbstar <= 9:
            tbkyrobox = 23
        elif tbstar <= 12:
            tbkyrobox = 24
        elif tbstar <= 14:
            tbkyrobox = 25
        elif tbstar <= 17:
            tbkyrobox = 26
        elif tbstar <= 18:
            tbkyrobox = 27
        elif tbstar <= 20:
            tbkyrobox = 28
        elif tbstar <= 22:
            tbkyrobox = 29
        elif tbstar <= 24:
            tbkyrobox = 30
        elif tbstar <= 26:
            tbkyrobox = 31
        elif tbstar <= 28:
            tbkyrobox = 32
        elif tbstar <= 30:
            tbkyrobox = 33
        elif tbstar <= 32:
            tbkyrobox = 34
        elif tbstar <= 34:
            tbkyrobox = 35
        elif tbstar <= 36:
            tbkyrobox = 36
        elif tbstar <= 38:
            tbkyrobox = 37
        elif tbstar <= 40:
            tbkyrobox = 38
        elif tbstar <= 41:
            tbkyrobox = 39
        elif tbstar <= 56:
            tbkyrobox = 40

        if getcurrency == True:
            if tbstar == 0:
                getvalue = 0
            elif tbstar <= 2:
                getvalue = 18
            elif tbstar <= 4:
                getvalue = 22
            elif tbstar <= 6:
                getvalue = 26
            elif tbstar <= 8:
                getvalue = 30
            elif tbstar == 9:
                getvalue = 34
            elif tbstar == 10:
                getvalue = 36
            elif tbstar == 11:
                getvalue = 38
            elif tbstar == 12:
                getvalue = 40
            elif tbstar == 13:
                getvalue = 42
            elif tbstar == 14:
                getvalue = 44
            elif tbstar == 15:
                getvalue = 46
            elif tbstar == 16:
                getvalue = 48
            elif tbstar == 17:
                getvalue = 52
            elif tbstar == 18:
                getvalue = 54
            elif tbstar == 19:
                getvalue = 56
            elif tbstar == 20:
                getvalue = 58
            elif tbstar <= 22:
                getvalue = 60
            elif tbstar <= 24:
                getvalue = 64
            elif tbstar <= 26:
                getvalue = 66
            elif tbstar <= 28:
                getvalue = 68
            elif tbstar <= 30:
                getvalue = 70
            elif tbstar <= 32:
                getvalue = 72
            elif tbstar <= 34:
                getvalue = 74
            elif tbstar <= 36:
                getvalue = 76
            elif tbstar <= 38:
                getvalue = 78
            elif tbstar <= 40:
                getvalue = 80
            elif tbstar <= 42:
                getvalue = 82
            elif tbstar <= 44:
                getvalue = 84
            else:
                getvalue = 0
        else:
            getvalue = 0

        if zeffo == True:
            zeffocurrency = 40
        else:
            zeffocurrency = 0

        if mandalore == True:
            mandalorecurrency = 100
        else:
            mandalorecurrency = 0
        
        if twgp <= 220:
            twvalue = 8
        else:
            twvalue = 11
        
        cenergy = energy * .02
        abkyros = abcompletion * 20

        tbbox = tbkyrobox * 2
        getrewards = getvalue * 2
        zefforewards = zeffocurrency * 2
        mandalorerewards = mandalorecurrency * 2
        twrewards = twvalue * 4
        campenergy = cenergy * 30.5

        totalkyro = tbbox + getrewards + zefforewards + mandalorerewards + twrewards + campenergy + abkyros
        await ctx.send(
            f"```Here is your kyro count:\nThe total amount of kyros you'll get in a month is: {totalkyro}"
            f"\nThe amount of kyros you'll get from the territory battle reward boxes is: {tbbox}"
            f"\nThe amount of kyros you'll get from spending territory rewards is: {getrewards}"
            f"\nThe amount of kyros you'll get from zeffo is: {zefforewards}"
            f"\nThe amount of kyros you'll get from mandalore is: {mandalorerewards}"
            f"\nThe amount of kyros you'll get from territory war reward boxes is: {twrewards}"
            f"\nThe amount of kyros you'll get from energy is an average of: {campenergy}"
            f"\nThe amount of kyros you'll get from assault battles is: {abkyros} ```"
        )

    
    @swgohtools.command(name="swgohset", aliases = ["ss"])
    async def swgohtools_swgohset(self, ctx: commands.Context):
        """View the settings that you have inputted in the bot."""
        tbstar = await self.config.user(ctx.author).tbstar()
        getcurrency = await self.config.user(ctx.author).getcurrency()
        zeffo = await self.config.user(ctx.author).zeffo()
        mandalore = await self.config.user(ctx.author).mandalore()
        twgp = await self.config.user(ctx.author).twgp()
        energy = await self.config.user(ctx.author).energy()
        abcompletion = await self.config.user(ctx.author).abcompletion()
        await ctx.send(
            f"Your current swgoh settings are set to:\nTerritory Battle Star count - {tbstar} stars"
            f"\nGet spending on Kyros - {getcurrency}"
            f"\nYour guild's zeffo unlock status is - {zeffo}"
            f"\nYour guild's mandalore unlock status is - {mandalore}"
            f"\nYou have the following active Territory War gp - {twgp} million"
            f"\nYou are spending {energy} energy on kyros per day (on average)."
            f"\nYou have completed the Challenge Tier 1 of {abcompletion} assault battles so far."
            )

    @app_commands.command(name="reliccalc", description="Calculates how many relic mats you'll need per relic tier.")
    @app_commands.describe(end_relic_tier="The relic tier you want to get to (1-9).", start_relic_tier="The relic tier you're starting at (0-8).", signal_data="Include signal data? Defaults to True.", relic_mat="Include relic mats? Defaults to True.")
    async def reliccalc(self, interaction: discord.Interaction, end_relic_tier: app_commands.Range[int, 1, 9], start_relic_tier: app_commands.Range[int, 0, 8] = 0, signal_data: bool=True, relic_mat: bool=True):
        if start_relic_tier >= end_relic_tier:
            await interaction.response.send_message("You can't have a starting relic value higher than your ending relic value.", ephemeral=True)
            return
        
        materials_needed = calculate_relic_mats(start_relic_tier, end_relic_tier)

        if not materials_needed:
            return await interaction.response.send_message("No materials are needed!", ephemeral=True)

        # Format results with emojis
        material_list = "\n".join(f"{EMOJIS.get(mat, '')}: {amount}" for mat, amount in materials_needed.items())

        # Create embed
        embed = discord.Embed(
            title=f"Relic Upgrade: R{start_relic_tier} ➡️ R{end_relic_tier}",
            description=material_list,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Star Wars: Galaxy of Heroes Relic Calculator")

        # Send embed response
        await interaction.response.send_message(embed=embed)

# Utility function for material calculation
def calculate_relic_mats(start: int, end: int):
    required_mats = {}
    for tier in range(start + 1, end + 1):  # Sum differences between tiers
        for mat, amount in RELIC_MATERIALS[tier].items():
            required_mats[mat] = required_mats.get(mat, 0) + amount
    return required_mats
