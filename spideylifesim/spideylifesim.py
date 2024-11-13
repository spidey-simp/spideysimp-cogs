from __future__ import annotations
import discord
import logging
import asyncio
import datetime
import random
from discord.ext import tasks, commands
from random import choice
import aiohttp
from typing import Dict, List, Literal, Optional, Any, NoReturn
from abc import ABC
from discord import Member, Guild


from redbot.core import Config, checks, commands, bank
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.commands import Cog
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.errors import BankPruneError

from .storestuff import FOODITEMS, SKILLITEMS, VEHICLES, ENTERTAINMENT, LUXURYITEMS, ALLITEMS
from .skills import SKILLSLIST

log = logging.getLogger("red.spideysimp-cogs.SpideyLifeSim")

_ = Translator("Bank API", __file__)
__all__ = (
    "is_owner_if_bank_global",
    "Account",
    "get_balance",
    "can_spend",
    "set_balance",
    "withdraw_credits",
    "deposit_credits",
    "transfer_credits",
    "wipe_bank",
    "bank_prune",
    "get_leaderboard",
    "get_leaderboard_position",
    "get_account",
    "is_global",
    "set_global",
    "get_bank_name",
    "set_bank_name",
    "get_currency_name",
    "set_currency_name",
    "get_max_balance",
    "set_max_balance",
    "get_default_balance",
    "set_default_balance",
    "AbortPurchase",
    "cost",
)



times = [
    datetime.time(hour=0, minute=0),
    datetime.time(hour=6, minute=0),
    datetime.time(hour=12, minute=0),
    datetime.time(hour=18, minute=0)
]
store_slots = []

userinventory = []
username = ""
userjob = ""
userpic = ""
usergender = ""
usertraits = []

async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.json()

class SpideyLifeSim(Cog):
    """Various life simulation functions to play around with!"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=684457913250480143, force_registration=True)
        fooddefault = random.choice(list(FOODITEMS.keys()))
        self.config.register_member()
        self.config.register_user()
        skilldefault = random.choice(list(SKILLITEMS.keys()))
        vehicledefault = random.choice(list(VEHICLES.keys()))
        entertainmentdefault = random.choice(list(ENTERTAINMENT.keys()))
        luxurydefault = random.choice(list(LUXURYITEMS.keys()))
        store_slots.insert(0, fooddefault)
        store_slots.insert(1, skilldefault)
        store_slots.insert(2, vehicledefault)
        store_slots.insert(3, entertainmentdefault)
        store_slots.insert(4, luxurydefault)

        self.storerefresh.start()

        self.config.register_user(
            userinventory=[],
            username = "None",
            userjob = "Unemployed",
            userpic = "https://i.pinimg.com/originals/40/a4/59/40a4592d0e7f4dc067ec0cdc24e038b9.png",
            usergender = "Not set",
            usertraits = [],
            skillslist = SKILLSLIST
        )
        self.config.register_member(
            userinventory=[],
            username = "None",
            userjob = "Unemployed",
            userpic = "https://i.pinimg.com/originals/40/a4/59/40a4592d0e7f4dc067ec0cdc24e038b9.png",
            usergender = "Not set",
            usertraits = [],
            skillslist = SKILLSLIST
        )


        
    def cog_unload(self):
        self.storerefresh.cancel()

    
    @tasks.loop(time=times)
    async def storerefresh(self):
        del store_slots[0:4]
        fooditem = random.choice(list(FOODITEMS.keys()))
        skillitem = random.choice(list(SKILLITEMS.keys()))
        vehicleitem = random.choice(list(VEHICLES.keys()))
        entertainmentitem = random.choice(list(ENTERTAINMENT.keys()))
        luxuryitem = random.choice(list(LUXURYITEMS.keys()))
        store_slots.insert(0, fooditem)
        store_slots.insert(1, skillitem)
        store_slots.insert(2, vehicleitem)
        store_slots.insert(3, entertainmentitem)
        store_slots.insert(4, luxuryitem)




    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return
    
    @commands.group(aliases=["sls"])
    async def spideylifesim(self, ctx: commands.Context):
        """Don't forget to set up your profile first!"""
        return

    
    @commands.group(aliases=["slss"])
    async def slsstore(self, ctx: commands.Context):
        """Purchaseable items are shown here and they cycle every 6 hours."""
        return
    
    @slsstore.command(name="storeview", aliases=["sv"])
    async def slsstore_storeview(self, ctx: commands.Context):
        """View the currently in-store items!"""
        currency = await bank.get_currency_name(ctx.guild)
        slot1 = FOODITEMS.get(store_slots[0])
        slot2 = SKILLITEMS.get(store_slots[1])
        slot3 = VEHICLES.get(store_slots[2])
        slot4 = ENTERTAINMENT.get(store_slots[3])
        slot5 = LUXURYITEMS.get(store_slots[4])
        storetitle = "Here's what's available in the shop right now:"
        storeitems = (
            f"Slot 1: {slot1} {currency} for {store_slots[0]}\n"
            f"Slot 2: {slot2} {currency} for {store_slots[1]}\n"
            f"Slot 3: {slot3} {currency} for {store_slots[2]}\n"
            f"Slot 4: {slot4} {currency} for {store_slots[3]}\n"
            f"Slot 5: {slot5} {currency} for {store_slots[4]}"
            )
        storeimage = "https://mydigitalwirral.co.uk/wp-content/uploads/2020/02/bigstock-Empty-Store-Front-With-Window-324188686.jpg"
        
        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(storeimage, ssl=False) as response:
                assert response.status == 200

        em = discord.Embed(
            title=storetitle, description=storeitems, color=discord.Color.red()
        )
        em.set_image(url=storeimage)
        await ctx.send(embed=em)
    
    @slsstore.command(name="purchase", aliases=["p"])
    async def slsstore_purchase(self, ctx: commands.Context, storeslot: int = 0, itemcount: int = 1):
        """Input the store slot of the item you want to purchase in the command!"""
        storepurchase = storeslot - 1
        itemforpurchase = store_slots[storepurchase]
        instore = itemforpurchase in store_slots
        if not instore:
            await ctx.send("```The store slot provided doesn't exist. Please input one of the store slots from 1-5.```")
            return
        
        itemcost = ALLITEMS.get(itemforpurchase)
        
        if itemcount > 1:
            spresence = "s"
        else:
            spresence = ""

        if itemcount > 10:
            await ctx.send("```That seems like a lot... Maybe buy a little less!```")
            return

        if itemcount <= 0:
            await ctx.send(f"```I don't think it's possible to buy {itemcount} items.```")
            return
        
        currency = await bank.get_currency_name(ctx.guild)
        for i in range(itemcount):
            bankbool  = await bank.can_spend(ctx.author, itemcost)
            if not bankbool:
                await ctx.send(f"```You have an insuffienct balance! Please try again when you have more {currency}.```")
                if i > 1:
                    userbalance = await bank.get_balance(ctx.author)
                    await ctx.send(f"```You have successfully purchased {itemcount} {itemforpurchase}{spresence} and your remaining account balance is {userbalance} {currency}.```")
                return
        
            await bank.withdraw_credits(ctx.author, itemcost)

            async with self.config.member(ctx.author).userinventory() as lst:
                lst.append(itemforpurchase)
        
        userbalance = await bank.get_balance(ctx.author)
        await ctx.send(f"```You have successfully purchased {itemcount} {itemforpurchase}{spresence} and your remaining account balance is {userbalance} {currency}.```")

    @slsstore.command(name="sellitem", aliases=["si"])
    async def slsstore_sellitem(self, ctx: commands.Context,  count: int = 1, *, itemtosell: str = None):
        """Sell items which returns 80% of their original value. Make sure items use same typecase as is seen in your inventory!"""
        if itemtosell == None:
            await ctx.send("```Whoops maybe you forgot to type the item!```")
            return
        
        if count <= 0:
            await ctx.send("How can you sell items you don't have? :thinking:")
            return
        
        userinventory = await self.config.member(ctx.author).userinventory()

        if itemtosell not in userinventory:
            await ctx.send(f"How can you sell {itemtosell} if you don't have it? :thinking: Maybe you typed it wrong. :shrug:\nPlease view your inventory to check how to spell and the case.")
            return
        
        originalprice = ALLITEMS.get(itemtosell)
        sellprice = originalprice * .8
        finalsell = round(sellprice)
        currency = await bank.get_currency_name(ctx.guild)
        if count > 1:
            spresence = "s"
        else:
            spresence = ""

        for i in range(count):
            await bank.deposit_credits(ctx.author, finalsell)
            async with self.config.member(ctx.author).userinventory() as lst:
                lst.remove(itemtosell)
            
        userbalance = await bank.get_balance(ctx.author)
        await ctx.send(f"```You have successfully sold {count} {itemtosell}{spresence} and your new account balance is {userbalance} {currency}.```")
        
    @commands.group(aliases=["slsp"])
    async def slsprofile(self, ctx: commands.Context):
        """See everything about your profile in these settings!"""
    
    @slsprofile.command(name="userprofile", aliases=["up"])
    async def slsprofile_userprofile(self, ctx: commands.Context):
        """See your user profile."""
        username = await self.config.member(ctx.author).username()
        usergender = await self.config.member(ctx.author).usergender()
        userjob = await self.config.member(ctx.author).userjob()
        usertraits = await self.config.member(ctx.author).usertraits()
        userpic = await self.config.member(ctx.author).userpic()
        if username == "None":
            profilename = ctx.author.display_name
        else:
            profilename = username
        
        currency = await bank.get_currency_name(ctx.guild)
        userbalance = await bank.get_balance(ctx.author)

        profileheader = "Here is your profile!"

        profiledescription = (
            f"**Name:** {profilename}\n"
            f"**Gender:** {usergender}\n"
            f"**Profession:** {userjob}\n"
            f"**Traits:** {usertraits}\n"
            f"**Account Balance:** {userbalance} {currency}\n"
        )

        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(userpic, ssl=False) as response:
                assert response.status == 200
        
        em = discord.Embed(
            title=profileheader, description=profiledescription, color=discord.Color.red()
        )
        em.set_image(url=userpic)
        await ctx.send(embed=em)
    
    @slsprofile.command(name="setname", aliases=["sn"])
    async def slsprofile_setname(self, ctx: commands.Context, *, name: str):
        """Change your profile name!"""
        await self.config.member(ctx.author).username.set(name)
        username = await self.config.member(ctx.author).username()
        await ctx.send(f"Your name has been changed to {username}.")
    
    @slsprofile.command(name="setgender", aliases=["sg"])
    async def slsprofile_setgender(self, ctx: commands.Context, *, gender: str):
        """Input Male or Female if you want he/him or she/her in responses! Otherwise feel free to input literally anything and it will use gender neutral language!"""
        await self.config.member(ctx.author).usergender.set(gender)
        usergender = await self.config.member(ctx.author).usergender()
        await ctx.send(f"Your gender has been changed to {usergender}.")
    
    @slsprofile.command(name="setpic", aliases=["sp"])
    async def slsprofile_setpic(self, ctx: commands.Context, *, link: str):
        """Input the link to an image that you'd like your profile image to be set as! Make sure it has .png, .jpg, etc. in the link because the bot isn't set to parse links."""
        await self.config.member(ctx.author).userpic.set(link)
        userpic = await self.config.member(ctx.author).userpic()
        await ctx.send(f"Your profile pic has been changed to {userpic}.")
    
    @slsprofile.command(name="inventory", aliases=["i"])
    async def slsprofile_inventory(self, ctx: commands.Context):
        """View the items you have in your inventory!"""
        userinventory = await self.config.member(ctx.author).userinventory()
        indexseparator = "\n- "
        await ctx.send(f"```Here are all the items you have:\n- {indexseparator.join(userinventory)}```")

    @slsprofile.command(name="otherprofile", aliases=["op"])
    async def slsprofile_otherprofile(self, ctx: commands.Context, user: discord.Member = None) -> None:
        """See your user profile."""
        if user == None:
            await ctx.send("```I think you forgot to put the other user in the parameters!```")
            return
        username = await self.config.member(user).username()
        usergender = await self.config.member(user).usergender()
        userjob = await self.config.member(user).userjob()
        usertraits = await self.config.member(user).usertraits()
        userpic = await self.config.member(user).userpic()
        if username == "None":
            profilename = user.display_name
        else:
            profilename = username
        
        currency = await bank.get_currency_name(ctx.guild)
        userbalance = await bank.get_balance(user)

        profileheader = "Here is your profile!"

        profiledescription = (
            f"**Name:** {profilename}\n"
            f"**Gender:** {usergender}\n"
            f"**Profession:** {userjob}\n"
            f"**Traits:** {usertraits}\n"
            f"**Account Balance:** {userbalance} {currency}\n"
        )

        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(userpic, ssl=False) as response:
                assert response.status == 200
        
        em = discord.Embed(
            title=profileheader, description=profiledescription, color=discord.Color.red()
        )
        em.set_image(url=userpic)
        await ctx.send(embed=em)
