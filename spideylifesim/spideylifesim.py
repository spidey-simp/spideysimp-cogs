from __future__ import annotations
import discord
import logging
import asyncio
from datetime import datetime, timedelta
import random
from discord.ext import tasks, commands
from random import choice
import aiohttp
from typing import Dict, List, Literal, Optional, Any, NoReturn
from abc import ABC
from discord import Member, Guild
from collections import Counter


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
from .jobs import ALLJOBS, Culinary, Business, Programming, Medicine, LawEnforcement, Artist, Film, Military, Writing, SocialMedia, Athletic, Legal, Journalism, Engineering, Music, Science, Education, Politics, Criminal, Astronaut, Fashion, Sith, SecretAgent

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



skill_cooldowns: Dict[str, Dict[str, datetime]] = {}

store_slots = []

userinventory = []
username = ""
userjob = ""
userpic = ""
usergender = ""
usertraits = []
careerlevel = 0
careerprog = 0
salary = 0
work_cooldowns = {}

next_refresh_time = None

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

        self.store_task = asyncio.create_task(self.storerefresh())

        self.config.register_user(
            userinventory=[],
            username = "None",
            userjob = "Unemployed",
            careerfield = "Unemployed",
            careerlevel = 0,
            careerprog = 0,
            salary = 0,
            userpic = "https://i.pinimg.com/originals/40/a4/59/40a4592d0e7f4dc067ec0cdc24e038b9.png",
            usergender = "Not set",
            usertraits = [],
            skillslist = SKILLSLIST
        )
        self.config.register_member(
            userinventory=[],
            username = "None",
            userjob = "Unemployed",
            careerfield = "Unemployed",
            careerlevel = 0,
            careerprog = 0,
            salary = 0,
            userpic = "https://i.pinimg.com/originals/40/a4/59/40a4592d0e7f4dc067ec0cdc24e038b9.png",
            usergender = "Not set",
            usertraits = [],
            skillslist = SKILLSLIST
        )


        
    def cog_unload(self):
        self.storerefresh.cancel()

    
    async def storerefresh(self):
        global next_refresh_time
        while True:
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
            next_refresh_time = datetime.now() + timedelta(hours=6)
            wait_seconds = (next_refresh_time - datetime.now()).total_seconds()
        
            await asyncio.sleep(wait_seconds)




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
        if next_refresh_time:
            remaining_time = next_refresh_time - datetime.now()
            hours, remainder = divmod(remaining_time.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            cooldown_timer = f"**Next refresh in:** {int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            cooldown_timer = "Next refresh time is being calculated."

        storeitems = (
            f"**Slot 1:** {slot1} {currency} for {store_slots[0]}\n"
            f"**Slot 2:** {slot2} {currency} for {store_slots[1]}\n"
            f"**Slot 3:** {slot3} {currency} for {store_slots[2]}\n"
            f"**Slot 4:** {slot4} {currency} for {store_slots[3]}\n"
            f"**Slot 5:** {slot5} {currency} for {store_slots[4]}\n"
            f"{cooldown_timer}"
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

        if itemcount > 100:
            await ctx.send("```That seems like a lot. Maybe try a smaller amount.```")
            return
        
        if itemcount > 1:
            spresence = "s"
        else:
            spresence = ""


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
        careerfield = await self.config.member(ctx.author).careerfield()
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
            f"**Profession:** {userjob} in the {careerfield} field\n"
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
        """View the items you have in your inventory, with duplicates stacked!"""
        userinventory = await self.config.member(ctx.author).userinventory()
        item_counts = Counter(userinventory)
        formatted_items = [f"{count}x - {item}" if count > 1 else item for item, count in item_counts.items()]
        indexseparator = "\n- "
        await ctx.send(f"```Here are all the items you have:\n- {indexseparator.join(formatted_items)}```")

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
        careerfield = await self.config.member(user).careerfield()
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
            f"**Profession:** {userjob} in the {careerfield} field\n"
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

    @slsprofile.command(name="resetprofile", aliases=["rp"])
    async def slsprofile_resetprofile(self, ctx: commands.Context):
        """Reset all profile data to their defaults!"""
        await ctx.send("This will completely reset your profile data completely! Are you sure you want to do this? `Confirm` or `Cancel`")
        
        def check(message):
            return message.author == ctx.author and message.content.lower() in ["confirm", "cancel"]

        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)

            if message.content.lower() == "confirm":
                await ctx.send("All data has been reset to its default values!")
                await self.config.member(ctx.author).userinventory.set([])
                await self.config.member(ctx.author).userjob.set("Unemployed")
                await self.config.member(ctx.author).careerfield.set("Unemployed")
                await self.config.member(ctx.author).careerlevel.set(0)
                await self.config.member(ctx.author).salary.set(0)
                await self.config.member(ctx.author).username.set("None")
                await self.config.member(ctx.author).careerprog.set(0)
                await self.config.member(ctx.author).userpic.set("https://i.pinimg.com/originals/40/a4/59/40a4592d0e7f4dc067ec0cdc24e038b9.png")
                await self.config.member(ctx.author).usergender.set("Not set")
                await self.config.member(ctx.author).usertraits.set([])
                await self.config.member(ctx.author).skillslist.set(SKILLSLIST)
            else:
                await ctx.send("You canceled your attempt to quit! Please try again if that was a mistake.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond! Command canceled.")
        
    @slsprofile.command(name="emptyaccount", aliases=["ea"])
    async def slsprofile_emptyaccount(self, ctx: commands.Context):
        """Your bank account will be reset to 0! If the bank is set to global (most likely your guild owner did set it that way), then it will reset your bank balance to 0 across all programs attached to this bot."""

        await ctx.send("This will empty your bank account attached to the bot! This action cannot be undone! Are you sure you want to proceed? `Confirm` or `Cancel`")
        balance = await bank.get_balance(ctx.author)
        def check(message):
            return message.author == ctx.author and message.content.lower() in ["confirm", "cancel"]

        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)

            if message.content.lower() == "confirm":
                await ctx.send("Your account balance has been reset to 0!")
                await bank.withdraw_credits(ctx.author, balance)
            else:
                await ctx.send("You canceled your attempt to erase your finances! Please try again if that was a mistake.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond! Command canceled.")
        
    @commands.group(aliases=["slssk"])
    async def slsskills(self, ctx: commands.Context):
        """Work on or check your skill levels!"""
        return

    @slsskills.command(name="skillindex", aliases=["si"])
    async def slsskills_skillindex(self, ctx: commands.Context):
        """See all available skills!"""
        indexseparator = "\n- "
        await ctx.send(f"```Here are all the available skills:\n- {indexseparator.join(SKILLSLIST)}```")
    
    @slsskills.command(name="skillprogress", aliases=["sp"])
    async def slsskills_skillprogress(self, ctx: commands.Context):
        """Here is your skill progress!"""
        async with self.config.member(ctx.author).skillslist() as skillslist:
            skillresult = "```Here are your skill levels:\n"
            for key, value in skillslist.items():
                skillresult += f"- {key} is at Level {value[0]} and {value[1]}% toward {value[0] + 1}.\n"
            skillresult += "```"
            await ctx.send(skillresult)
    
    @slsskills.command(name="practice", aliases=["p"])
    async def slsskills_practice(self, ctx: commands.Context, skillname: str = None) -> None:
        """Work on a skill of your choice! It is case sensitive! All skills start with capitals!"""
        skillexist = skillname in SKILLSLIST.keys()
        userinventory = await self.config.member(ctx.author).userinventory()

        if not skillexist:
            await ctx.send("```This skill is not one of the accepted skills! Please consult the skill index and try again!```")
            return
        current_time = datetime.now()
        

        user_cooldowns = skill_cooldowns.get(ctx.author.id, {})
        if skillname in user_cooldowns:
            cooldown_time = user_cooldowns[skillname]
            if current_time < cooldown_time:
                remaining_time = cooldown_time - current_time
                remaining_seconds = remaining_time.total_seconds()
                if remaining_seconds > 60:
                    remaining_minutes = remaining_seconds // 60
                    remaining_seconds = remaining_seconds % 60
                    await ctx.send(f"```You're so tired from practicing {skillname}. Try waiting {int(remaining_minutes)} minutes and {int(remaining_seconds)} seconds to practice again.```")
                    return
                else:
                    await ctx.send(f"```You're so tired from practicing {skillname}. Try waiting {int(remaining_seconds)} seconds to practice again.```")
                    return
        
        
        required_items = SKILLSLIST.get(skillname, [])[2:]
        if required_items and not any(item in userinventory for item in required_items):
            await ctx.send(f"```You need one of these items to practice {skillname}: {', '.join(required_items)}. Buy them from the store!```")
            return
        
        skillslist = await self.config.member(ctx.author).skillslist()
        skillvalues = skillslist.get(skillname)
        skilladdperc = random.randint(5, 33)
        newskillperc = skillvalues[1] + skilladdperc
        skilllevel = skillvalues[0]
        if newskillperc >= 100:
            newskillperc -= 100
            skilllevel += 1
            await ctx.send(f"You just promoted your {skillname} skill to {skilllevel} level!")
        skillslist[skillname] = [skilllevel, newskillperc]
        await self.config.member(ctx.author).skillslist.set(skillslist)
        cooldown_duration = timedelta(hours=1)  # Set cooldown to 1 hour
        cooldown_time = current_time + cooldown_duration
        if ctx.author.id not in skill_cooldowns:
            skill_cooldowns[ctx.author.id] = {}
        skill_cooldowns[ctx.author.id][skillname] = cooldown_time

        await ctx.send(f"You have improved {skillname} skill by {skilladdperc}% which puts it {newskillperc}% towards promoting to level {skilllevel + 1}!")

    @commands.group(aliases=["slsc"])
    async def slscareers(self, ctx: commands.Context):
        """Join a career and rise the ranks to the top of your field!"""
        return
        
    @slscareers.command(name="careerindex", aliases=["ci"])
    async def slscareers_careerindex(self, ctx: commands.Context):
        """See an index of all available careers!"""
        indexseparator = "\n- "
        await ctx.send(f"```Here is a list of all the available careers:\n- {indexseparator.join(ALLJOBS)}```")

    @slscareers.command(name="aboutcareer", aliases=["ac"])
    async def slscareers_aboutcareer(self, ctx: commands.Context, careername: str = None) -> None:
        """See more information about a particular career! Make sure the career is spelled and capitalized the same way it is in the index!"""

        if careername == None:
            await ctx.send("```You might've forgotten to type the career in! I can't get info for a career you didn't input!```")
            return
        
        if careername not in ALLJOBS:
            await ctx.send("```That career didn't seem to be found in our databases! Maybe try typing it again or checking the spelling!```")
            return
        
        
        jobinfo = ALLJOBS.get(careername)
        requiredskills = ALLJOBS.get(careername, [])[4:]
        careertitle = careername
        careerdescription = (
            f"{jobinfo[0]}\n"
            f"**Boss:** {jobinfo[2]}\n"
            f"**Required skill(s):** {', '.join(requiredskills)}"
        )
        careerpic = jobinfo[1]
        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(careerpic, ssl=False) as response:
                assert response.status == 200
        
        em = discord.Embed(
            title=careertitle, description=careerdescription, color=discord.Color.red()
        )
        em.set_image(url=careerpic)
        await ctx.send(embed=em)
    
    @slscareers.command(name="careerapply", aliases=["ca"])
    async def slscareers_careerapply(self, ctx: commands.Context, jobname: str = None) -> None:
        """Apply to a career of your choosing!"""

        if jobname == None:
            await ctx.send("```Not sure how you're planning to apply to a nameless job! Maybe try putting the name in next time!```")
            return
        
        userjob = await self.config.member(ctx.author).userjob()

        careerfield = self.config.member(ctx.author).careerfield()
        if careerfield == jobname:
            await ctx.send("```It looks like you're already in that career!```")
            return
        
        if userjob != "Unemployed":
            await ctx.send("```You should probably quit your existing job before you apply to new ones!```")
            return
        
        if jobname not in ALLJOBS:
            await ctx.send("```It doesn't seem like that's an available job right now... Maybe try retyping it!```")
            return
        
        jobdict = globals().get(jobname)
        if jobdict == None:
            await ctx.send("```You should not be able to see this error as a user! Please report this error to spideysimp if you see it!```")
            return
        maincareerlist = ALLJOBS.get(jobname)
        requiredskills = ALLJOBS.get(jobname, [])[4:]
        currency = await bank.get_currency_name(ctx.guild)
        startercareer = list(jobdict.keys())[0]
        careerdesc = jobdict.get(startercareer)
        description = careerdesc[0]
        salary = careerdesc[1]
        apptitle = f"{jobname} Application"
        appdesc = (
            f"You are currently trying to apply for the **{jobname} Career Path.**\n"
            f"The first career level is **{startercareer}** with the following job description:\n{description}\n"
            f"Your daily salary would start at **{salary} {currency}.**\n"
            f"Your supervisor would be **{maincareerlist[2]}**.\n"
            f"You'll need to build your **{', '.join(requiredskills)} skill(s)** if you want to get promoted."
        )
        careerpic = maincareerlist[1]
        
        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(careerpic, ssl=False) as response:
                assert response.status == 200

        em = discord.Embed(
            title=apptitle, description=appdesc, color=discord.Color.red()
        )
        em.set_image(url=careerpic)
        await ctx.send(embed=em)
        await ctx.send("Type `Confirm` to secure this job or `Cancel` to cancel the application.")

        def check(message):
            return message.author == ctx.author and message.content.lower() in ["confirm", "cancel"]

        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)

            if message.content.lower() == "confirm":
                await ctx.send(f"Congratulations {ctx.author.mention}, you've been hired for the {jobname} job!")
                await self.config.member(ctx.author).userjob.set(startercareer)
                await self.config.member(ctx.author).careerfield.set(jobname)
                await self.config.member(ctx.author).careerlevel.set(1)
                await self.config.member(ctx.author).salary.set(salary)
            else:
                await ctx.send(f"Application for {jobname} has been canceled.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond! Application has been canceled.")
        
    @slscareers.command(name="quitjob", aliases=["qj"])
    async def slscareers_quitjob(self, ctx: commands.Context):
        """Quit your job with this function!"""
        userjob = await self.config.member(ctx.author).userjob()
        await ctx.send(f"Are you sure you want to quit your job as a {userjob}? Type `Yes` or `No`.")
        def check(message):
            return message.author == ctx.author and message.content.lower() in ["yes", "no"]

        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)

            if message.content.lower() == "yes":
                await ctx.send("You have quit your job!")
                await self.config.member(ctx.author).userjob.set("Unemployed")
                await self.config.member(ctx.author).careerfield.set("Unemployed")
                await self.config.member(ctx.author).careerprog.set(0)
                await self.config.member(ctx.author).careerlevel.set(0)
                await self.config.member(ctx.author).salary.set(0)
            else:
                await ctx.send("Your resignation has been canceled.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond! If you want to quit, run the command again please!")

    @slscareers.command(name="gotowork", aliases=["gtw"])
    async def slscareers_gotowork(self, ctx: commands.Context):
        """Go to work at your job!"""
        user_id = ctx.author.id
        userjob = await self.config.member(ctx.author).userjob()
        careerfield = await self.config.member(ctx.author).careerfield()
        careerprog = await self.config.member(ctx.author).careerprog()
        careerlevel = await self.config.member(ctx.author).careerlevel()
        skillslist = await self.config.member(ctx.author).skillslist()
        salary = await self.config.member(ctx.author).salary()

        current_time = datetime.now()
        last_work_time = work_cooldowns.get(user_id)

        if last_work_time:
            time_since_last_work = current_time - last_work_time
            if time_since_last_work < timedelta(days=1):
                remaining_time = timedelta(days=1) - time_since_last_work
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(f"```You can only go to work once every day silly. Please try again in {hours} hours and {minutes} minutes.```")
                return

        if userjob == "Unemployed":
            await ctx.send("```You seem to be unemployed! You can't work if you have no job!```")
            return
        
       
        
        work_cooldowns[user_id] = current_time

        jobskillreq = ALLJOBS.get(careerfield)[4]
        skillvalue = skillslist.get(jobskillreq)[0]
        if ALLJOBS.get(careerfield)[5] != None:
            jobskillreq2 = ALLJOBS.get(careerfield)[5]
            skillvalue2 = skillslist.get(jobskillreq2)[0]
        
        jobaddperc = random.randint(10, 40)
        newjobperc = careerprog + jobaddperc
        jobdict = globals().get(careerfield)
        promotioncareer = list(jobdict.keys())[careerlevel]
        promotionbasesalary = jobdict.get(promotioncareer)[1]
        promotionbasebonus = jobdict.get(promotioncareer)[2]
        promotionsalary = promotionbasesalary * (random.randint(100, 115) / 100)
        promotionbonus = promotionbasebonus * (random.randint(100, 115) / 100)
        newsalary = round(promotionsalary)
        newbonus = round(promotionbonus)
        promotionlevel = careerlevel + 1
        currency = await bank.get_currency_name(ctx.guild)
        if newjobperc >= 100:
            if  promotionlevel <= skillvalue:
                if skillvalue2 == None:
                    newjobperc -= 100
                    await self.config.member(ctx.author).userjob.set(promotioncareer)
                    await self.config.member(ctx.author).careerlevel.set(promotionlevel)
                    await self.config.member(ctx.author).salary.set(newsalary)
                    await bank.deposit_credits(ctx.author, promotionbonus)
                    await ctx.send(
                        f"You have been promoted at your career from {userjob} to {promotioncareer}!\n"
                        f"You will now be making {newsalary} {currency} per day and have received a promotion bonus of {newbonus} {currency}!")
                elif promotionlevel <= skillvalue2:
                    newjobperc -= 100
                    await self.config.member(ctx.author).userjob.set(promotioncareer)
                    await self.config.member(ctx.author).careerlevel.set(promotionlevel)
                    await self.config.member(ctx.author).salary.set(newsalary)
                    await bank.deposit_credits(ctx.author, newbonus)
                    await ctx.send(
                        f"You have been promoted at your career from {userjob} to {promotioncareer}!\n"
                        f"You will now be making {newsalary} {currency} per day and have received a promotion bonus of {newbonus} {currency}!")
                elif skillvalue2 < promotionlevel:
                    newjobperc = 99
                    await ctx.send(f"Your {jobskillreq2} skill needs to reach level {promotionlevel} before you can be promoted!")
            elif skillvalue < promotionlevel:
                newjobperc = 99
                await ctx.send(f"Your {jobskillreq} skill needs to reach level {promotionlevel} before you can be promoted!")     
        
        await bank.deposit_credits(ctx.author, salary)
        await self.config.member(ctx.author).careerprog.set(newjobperc)
        await ctx.send(f"You finished your day of work at {careerfield} and have earned {salary} {currency}!")

    @slscareers.command(name="careerreview", aliases=["cr"])
    async def slscareers_careerreview(self, ctx: commands.Context):
        userjob = await self.config.member(ctx.author).userjob()
        careerfield = await self.config.member(ctx.author).careerfield()
        careerprog = await self.config.member(ctx.author).careerprog()
        careerlevel = await self.config.member(ctx.author).careerlevel()
        salary = await self.config.member(ctx.author).salary()
        username = await self.config.member(ctx.author).username()
        currency = await bank.get_currency_name(ctx.guild)
        jobdict = globals().get(careerfield)

        careertitle = f"{username}'s Career Info!"
        careerdesc = (
                f"**Position:** {userjob} at {careerfield} level {careerlevel}.\n"
                f"**Job description:** {jobdict.get(userjob)[0]}\n"
                f"**Daily salary:** {salary} {currency}.\n"
                f"**Required Skill(s):** {', '.join(ALLJOBS.get(careerfield)[4:])}\n"
                f"**Boss:** {ALLJOBS.get(careerfield)[2]}\n"
                f"**Promotion Progress:** {careerprog}% to {careerlevel + 1}! Make sure your required skills are at least the same as the level you would be promoted to!"
                )
        
        em = discord.Embed(
            title=careertitle, description=careerdesc, color=discord.Color.red()
        )
        em.set_image(url=ALLJOBS.get(careerfield)[1])
        await ctx.send(embed=em)
