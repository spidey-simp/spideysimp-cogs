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
import humanize

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
from .jobs import ALLJOBS, Culinary, Business, Programming, Medicine, LawEnforcement, Artist, Film, Military, Writing, SocialMedia, Athletic, Legal, Journalism, Engineering, Music, Science, Education, Politics, Criminal, Astronaut, Fashion, Sith, SecretAgent, Sailing, Knighthood
from .actions import LightsaberList, CutlassList, BroadswordList, MartialArtsList

log = logging.getLogger("red.spideysimp-cogs.SpideyLifeSim")

skill_cooldowns: Dict[str, Dict[str, datetime]] = {}

store_slots = []

userinventory = []
username = ""
userjob = ""
userpic = ""
usergender = ""
careerfield = ""
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

        self.storerefresh_task = None

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


    def cog_load(self):
        # Create the task when the cog is loaded
        self.storerefresh_task = asyncio.create_task(self.storerefresh())
    
    def cog_unload(self):
        if self.storerefresh_task and not self.storerefresh_task.cancelled():
            self.storerefresh_task.cancel()

    

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
            try:
                await asyncio.sleep(wait_seconds)
        
            except asyncio.CancelledError:
                print("storerefresh task was cancelled. Performing cleanup... Probably best to reload the cog if you see this!")
                # Optional: Reset store_slots or clear any temporary data
                store_slots.clear()




    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return
    
    async def practice_skill(self, ctx, skillname, progress: bool = True, user: discord.Member = None):
        """Handle the skill practice process with a progress bar."""
        if user == None:
            user = ctx.author
        skillslist = await self.config.member(user).skillslist()
        username = await self.config.member(user).username()
        if username == "None":
            username = user.display_name
        skillvalues = skillslist.get(skillname, [0, 0])
        skilladdperc = random.randint(5, 33)
        newskillperc = skillvalues[1] + skilladdperc
        skilllevel = skillvalues[0]
        if skilllevel >= 10:
            skilllevel = 10
            skillslist[skillname] = [skilllevel, 100]
            await ctx.send(f"You have maxed {skillname}! You cannot get it any higher!")
            return


        if newskillperc >= 100:
            newskillperc -= 100
            skilllevel += 1
            await ctx.send(f"Congratulations, {username}! Your {skillname} skill is now Level {skilllevel}!")

        skillslist[skillname] = [skilllevel, newskillperc]
        await self.config.member(ctx.author).skillslist.set(skillslist)
        if progress == True:
            def generate_progress_bar(percentage):
                """Generate a progress bar with blocks for a percentage."""
                filled_blocks = int(percentage // 10) 
                empty_blocks = 10 - filled_blocks
                return f"[{'█' * filled_blocks}{'░' * empty_blocks}]"

            await ctx.send(
                f"```You improved {skillname} skill by {skilladdperc}%, reaching {generate_progress_bar(newskillperc)} towards Level {skilllevel + 1}.```"
            )
        else:
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
        items = [FOODITEMS, SKILLITEMS, VEHICLES, ENTERTAINMENT, LUXURYITEMS]
        store_items = [item.get(store_slots[i]) for i, item in enumerate(items)]
        store_title = "Here's what's available in the shop right now:"

        remaining_time = (next_refresh_time - datetime.now()).total_seconds() if next_refresh_time else None
        cooldown_timer = (
            f"**Next refresh in:** {int(remaining_time // 3600)}h {int(remaining_time % 3600 // 60)}m {int(remaining_time % 60)}s"
            if remaining_time
            else "Next refresh time is being calculated."
        )

        store_items_text = "\n".join(
            [f"**Slot {i + 1}:** {humanize.intcomma(item)} {currency} for {store_slots[i]}" for i, item in enumerate(store_items)]
        ) + f"\n{cooldown_timer}"

        store_image = "https://mydigitalwirral.co.uk/wp-content/uploads/2020/02/bigstock-Empty-Store-Front-With-Window-324188686.jpg"

        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(store_image, ssl=False) as response:
                if response.status != 200:
                    await ctx.send("Failed to fetch store image.")
                    return

        embed = discord.Embed(title=store_title, description=store_items_text, color=discord.Color.red())
        embed.set_image(url=store_image)
        await ctx.send(embed=embed)

    @slsstore.command(name="purchase", aliases=["p"])
    async def slsstore_purchase(self, ctx: commands.Context, storeslot: int = 0, itemcount: int = 1):
        """Input the store slot of the item you want to purchase in the command!"""
        if not (1 <= storeslot <= 5):
            await ctx.send("The store slot provided doesn't exist. Please input one of the store slots from 1-5.")
            return

        item_for_purchase = store_slots[storeslot - 1]
        item_cost = ALLITEMS.get(item_for_purchase)
        if itemcount <= 0:
            await ctx.send(f"I don't think it's possible to buy {itemcount} items.")
            return
        if itemcount > 10:
            await ctx.send("That seems like a lot... Maybe buy a little less!")
            return

        currency = await bank.get_currency_name(ctx.guild)
        total_cost = item_cost * itemcount
        if not await bank.can_spend(ctx.author, total_cost):
            await ctx.send(f"You have an insufficient balance! You need {total_cost} {currency}.")
            return

        await bank.withdraw_credits(ctx.author, total_cost)
        async with self.config.member(ctx.author).userinventory() as inventory:
            inventory.extend([item_for_purchase] * itemcount)

        user_balance = await bank.get_balance(ctx.author)
        item_plural = "s" if itemcount > 1 else ""
        await ctx.send(f"You have successfully purchased {itemcount} {item_for_purchase}{item_plural}.\n"
                   f"Remaining balance: {humanize.intcomma(user_balance)} {currency}.")

    @slsstore.command(name="sellitem", aliases=["si"])
    async def slsstore_sellitem(self, ctx: commands.Context, count: int = 1, *, itemtosell: str = None):
        """Sell items which returns 80% of their original value. Case-sensitive."""
        if not itemtosell:
            await ctx.send("Please specify the item you want to sell.")
            return
        if count <= 0:
            await ctx.send("How can you sell items you don't have? :thinking:")
            return

        user_inventory = await self.config.member(ctx.author).userinventory()
        if itemtosell not in user_inventory:
            await ctx.send(f"You don't have {itemtosell}. Check your inventory for spelling and case.")
            return
        currency = await bank.get_currency_name(ctx.guild)
        original_price = ALLITEMS.get(itemtosell)
        sell_price = round(original_price * 0.8)
        async with self.config.member(ctx.author).userinventory() as inventory:
            for _ in range(min(count, inventory.count(itemtosell))):
                inventory.remove(itemtosell)
                await bank.deposit_credits(ctx.author, sell_price)

        user_balance = await bank.get_balance(ctx.author)
        item_plural = "s" if count > 1 else ""
        await ctx.send(f"You sold {count} {itemtosell}{item_plural}. New balance: {humanize.intcomma(user_balance)} {currency}.")

    @commands.group(aliases=["slsp"])
    async def slsprofile(self, ctx: commands.Context):
        """See everything about your profile in these settings!"""
    
    @slsprofile.command(name="userprofile", aliases=["up"])
    async def slsprofile_userprofile(self, ctx: commands.Context):
        """See your user profile."""
        user_data = await self.config.member(ctx.author).all()
        profilename = user_data["username"] if user_data["username"] != "None" else ctx.author.display_name
        currency = await bank.get_currency_name(ctx.guild)
        userbalance = await bank.get_balance(ctx.author)
    
        profileheader = "Here is your profile!"
        profiledescription = (
            f"**Name:** {profilename}\n"
            f"**Gender:** {user_data['usergender']}\n"
            f"**Profession:** {user_data['userjob']} in the {user_data['careerfield']} field\n"
            f"**Traits:** {user_data['usertraits']}\n"
            f"**Account Balance:** {humanize.intcomma(userbalance)} {currency}\n"
        )
        await self.display_profile(ctx, profileheader, profiledescription, user_data["userpic"])

    @slsprofile.command(name="setname", aliases=["sn"])
    async def slsprofile_setname(self, ctx: commands.Context, *, name: str):
        """Change your profile name!"""
        await self.update_and_confirm(ctx, "username", name)

    @slsprofile.command(name="setgender", aliases=["sg"])
    async def slsprofile_setgender(self, ctx: commands.Context, *, gender: str):
        """Set your gender."""
        await self.update_and_confirm(ctx, "usergender", gender)

    @slsprofile.command(name="setpic", aliases=["sp"])
    async def slsprofile_setpic(self, ctx: commands.Context, *, link: str):
        """Set your profile image."""
        await self.update_and_confirm(ctx, "userpic", link)

    @slsprofile.command(name="inventory", aliases=["i"])
    async def slsprofile_inventory(self, ctx: commands.Context):
        """View your inventory."""
        userinventory = await self.config.member(ctx.author).userinventory()
        item_counts = Counter(userinventory)
        formatted_items = [f"{count}x - {item}" if count > 1 else item for item, count in item_counts.items()]
        message = "```Here are all the items you have:\n- " + "\n- ".join(formatted_items) + "```"
        await ctx.send(message)

    @slsprofile.command(name="otherprofile", aliases=["op"])
    async def slsprofile_otherprofile(self, ctx: commands.Context, user: discord.Member = None):
        """See another user's profile."""
        if not user:
            await ctx.send("```Please specify a user to view their profile.```")
            return
        user_data = await self.config.member(user).all()
        profilename = user_data["username"] if user_data["username"] != "None" else user.display_name
        currency = await bank.get_currency_name(ctx.guild)
        userbalance = await bank.get_balance(user)
    
        profileheader = "Here is the user's profile!"
        profiledescription = (
            f"**Name:** {profilename}\n"
            f"**Gender:** {user_data['usergender']}\n"
            f"**Profession:** {user_data['userjob']} in the {user_data['careerfield']} field\n"
            f"**Traits:** {user_data['usertraits']}\n"
            f"**Account Balance:** {humanize.intcomma(userbalance)} {currency}\n"
        )
        await self.display_profile(ctx, profileheader, profiledescription, user_data["userpic"])

    @slsprofile.command(name="resetprofile", aliases=["rp"])
    async def slsprofile_resetprofile(self, ctx: commands.Context):
        """Reset profile data."""
        await self.confirm_action(
            ctx, 
            "This will completely reset your profile data! `Confirm` or `Cancel`", 
            self.reset_user_profile, 
            ctx.author
        )

    @slsprofile.command(name="emptyaccount", aliases=["ea"])
    async def slsprofile_emptyaccount(self, ctx: commands.Context):
        """Reset your bank balance to 0."""
        balance = await bank.get_balance(ctx.author)
        await self.confirm_action(
            ctx, 
            "This will empty your bank account! `Confirm` or `Cancel`", 
            lambda user: bank.withdraw_credits(user, balance), 
            ctx.author
        )

    async def update_and_confirm(self, ctx, attribute, value):
        """Helper function to update an attribute and confirm it."""
        await self.config.member(ctx.author).set_raw(attribute, value=value)
        await ctx.send(f"Your {attribute} has been updated to {value}.")

    async def display_profile(self, ctx, title, description, image_url):
        """Helper function to display a profile."""
        em = discord.Embed(title=title, description=description, color=discord.Color.red())
        em.set_image(url=image_url)
        await ctx.send(embed=em)

    async def confirm_action(self, ctx, message, action, *args):
        """Helper function for confirm/cancel actions."""
        await ctx.send(message)
        def check(m):
            return m.author == ctx.author and m.content.lower() in ["confirm", "cancel"]
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            if response.content.lower() == "confirm":
                await action(*args)
                await ctx.send("Action confirmed and executed.")
            else:
                await ctx.send("Action cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Command cancelled.")
    
    async def reset_user_profile(self, member):
        """Reset all profile data to their default values for a given member."""
        await self.config.member(member).userinventory.set([])
        await self.config.member(member).userjob.set("Unemployed")
        await self.config.member(member).careerfield.set("Unemployed")
        await self.config.member(member).careerlevel.set(0)
        await self.config.member(member).salary.set(0)
        await self.config.member(member).username.set("None")
        await self.config.member(member).careerprog.set(0)
        await self.config.member(member).userpic.set("https://i.pinimg.com/originals/40/a4/59/40a4592d0e7f4dc067ec0cdc24e038b9.png")
        await self.config.member(member).usergender.set("Not set")
        await self.config.member(member).usertraits.set([])
        await self.config.member(member).skillslist.set(SKILLSLIST)

    @commands.group(aliases=["slssk"])
    async def slsskills(self, ctx: commands.Context):
        """Work on or check your skill levels!"""
        return

    @slsskills.command(name="skillindex", aliases=["si"])
    async def slsskills_skillindex(self, ctx: commands.Context):
        """See all available skills!"""
        skills_text = "```Here are all the available skills:\n- " + "\n- ".join(SKILLSLIST) + "```"
        await ctx.send(skills_text)

    @slsskills.command(name="skillprogress", aliases=["sp"])
    async def slsskills_skillprogress(self, ctx: commands.Context):
        """Show your skill progress with progress bars!"""
        skillslist = await self.config.member(ctx.author).skillslist()

        def generate_progress_bar(percentage):
            """Generate a progress bar with blocks for a percentage."""
            filled_blocks = int(percentage // 10)  # Each block represents 10%
            empty_blocks = 10 - filled_blocks
            return f"[{'█' * filled_blocks}{'░' * empty_blocks}]"
        
        filtered_skills = {key: value for key, value in skillslist.items() if value[0] > 0 or value[1] > 0}

        if not filtered_skills:
            skillresult = "```You haven't made any progress in any skills yet!```"
        else:
            skillresult = "```Here are the skills you have developed so far:\n" + "\n".join(
                f"- {key}\nLevel {value[0]} {generate_progress_bar(value[1])}"
                for key, value in filtered_skills.items()
            ) + "```"
        await ctx.send(skillresult)

    @slsskills.command(name="practice", aliases=["p"])
    async def slsskills_practice(self, ctx: commands.Context, skillname: str = None):
        """Work on a skill of your choice (case-sensitive; starts with capitals)."""
        if skillname not in SKILLSLIST:
            await ctx.send("```This skill is not one of the accepted skills! Please consult the skill index and try again!```")
            return

        if await self.is_on_cooldown(ctx, skillname):
            return

        if not await self.has_required_items(ctx, skillname):
            return

        await self.practice_skill(ctx, skillname)
        cooldown_duration = timedelta(minutes=60)  # Adjust duration as needed
        current_time = datetime.now()
        user_cooldowns = skill_cooldowns.get(ctx.author.id, {})
        user_cooldowns[skillname] = current_time + cooldown_duration
        skill_cooldowns[ctx.author.id] = user_cooldowns

    async def is_on_cooldown(self, ctx, skillname):
        """Check if the user is on cooldown for a skill."""
        current_time = datetime.now()
        user_cooldowns = skill_cooldowns.get(ctx.author.id, {})
        if skillname in user_cooldowns:
            cooldown_time = user_cooldowns[skillname]
            if current_time < cooldown_time:
                remaining_seconds = (cooldown_time - current_time).total_seconds()
                minutes, seconds = divmod(int(remaining_seconds), 60)
                await ctx.send(f"```You're so tired from practicing {skillname}. Try waiting {minutes} minutes and {seconds} seconds to practice again.```" if minutes else f"```You're so tired from practicing {skillname}. Try waiting {seconds} seconds to practice again.```")
                return True
        return False

    async def has_required_items(self, ctx, skillname):
        """Check if the user has the required items to practice a skill."""
        required_items = SKILLSLIST.get(skillname, [])[2:]
        userinventory = await self.config.member(ctx.author).userinventory()
        if required_items and not any(item in userinventory for item in required_items):
            await ctx.send(f"```You need one of these items to practice {skillname}: {', '.join(required_items)}. Buy them from the store!```")
            return False
        return True

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
    async def slscareers_aboutcareer(self, ctx: commands.Context, careername: str = None):
        """See more information about a particular career! Ensure correct spelling/capitalization."""
        if not careername:
            await ctx.send("```Please specify the career you want to learn about!```")
            return
    
        if careername not in ALLJOBS:
            await ctx.send("```The specified career wasn't found. Double-check spelling and try again!```")
            return
    
        jobinfo = ALLJOBS[careername]
        requiredskills = jobinfo[4]
        em = discord.Embed(
            title=careername, 
            description=f"{jobinfo[0]}\n**Boss:** {jobinfo[2]}\n**Required skill(s):** {', '.join(requiredskills)}", 
            color=discord.Color.red()
        )
        em.set_image(url=jobinfo[1])
        await ctx.send(embed=em)

    @slscareers.command(name="careerapply", aliases=["ca"])
    async def slscareers_careerapply(self, ctx: commands.Context, jobname: str = None):
        """Apply to a career of your choosing!"""
        if not jobname:
            await ctx.send("```Specify a job name to apply!```")
            return

        userjob = await self.config.member(ctx.author).userjob()
        careerfield = await self.config.member(ctx.author).careerfield()
    
        if careerfield == jobname:
            await ctx.send("```You're already in that career!```")
            return
        if userjob != "Unemployed":
            await ctx.send("```Quit your existing job before applying to a new one!```")
            return
        if jobname not in ALLJOBS:
            await ctx.send("```Job not found. Try retyping it!```")
            return
    
        jobdict = globals().get(jobname)
        if not jobdict:
            await ctx.send("```Internal error! Contact support if this persists.```")
            return

        maincareerlist = ALLJOBS[jobname]
        requiredskills = maincareerlist[4]
        currency = await bank.get_currency_name(ctx.guild)
        startercareer = list(jobdict.keys())[0]
        description, salary = jobdict[startercareer][:2]
    
        em = discord.Embed(
            title=f"{jobname} Application",
            description=(
            f"Apply for the **{jobname} Career Path.**\n"
            f"Starting as **{startercareer}**: {description}\n"
            f"Salary: **{salary} {currency}**\n"
            f"Supervisor: **{maincareerlist[2]}**\n"
            f"Required skill(s): **{', '.join(requiredskills)}**"
            ),
            color=discord.Color.red()
        )
        em.set_image(url=maincareerlist[1])
        await ctx.send(embed=em)
        await ctx.send("Type `Confirm` to secure this job or `Cancel` to cancel.")

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
                async with self.config.member(ctx.author).userinventory() as inventory:
                    inventory.extend(maincareerlist[3])
                recruitmessage = discord.Embed(title=f"Message from {maincareerlist[2]}", description=f"{maincareerlist[6]}")
                recruitmessage.set_thumbnail(url=maincareerlist[5])
                await ctx.send(embed=recruitmessage)
            else:
                await ctx.send(f"Application for {jobname} has been canceled.")
        except asyncio.TimeoutError:
            await ctx.send("Response timeout! Application canceled.")

    @slscareers.command(name="quitjob", aliases=["qj"])
    async def slscareers_quitjob(self, ctx: commands.Context):
        """Quit your job with this function!"""
        userjob = await self.config.member(ctx.author).userjob()
        careerfield = await self.config.member(ctx.author).careerfield()

        if userjob == "Unemployed":
            await ctx.send("You can't quit a job if you don't have a job.")
            return
        
        await ctx.send(f"Are you sure you want to quit your job as a {userjob}? Type `Yes` or `No`.")
    
        def check(message):
            return message.author == ctx.author and message.content.lower() in ["yes", "no"]

        maincareerlist = ALLJOBS[careerfield]

        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            if message.content.lower() == "yes":
                await ctx.send("You have quit your job!")
                await self.config.member(ctx.author).userjob.set("Unemployed")
                await self.config.member(ctx.author).careerfield.set("Unemployed")
                await self.config.member(ctx.author).careerprog.set(0)
                await self.config.member(ctx.author).careerlevel.set(0)
                await self.config.member(ctx.author).salary.set(0)
                for i in maincareerlist[3]:
                    async with self.config.member(ctx.author).userinventory() as inventory:
                        if i in inventory:
                            inventory.remove(i)
                leavemessage = discord.Embed(title=f"Message from {maincareerlist[2]}", description=f"{maincareerlist[7]}")
                leavemessage.set_thumbnail(url=maincareerlist[5])
                await ctx.send(embed=leavemessage)
            else:
                await ctx.send("Resignation canceled.")
        except asyncio.TimeoutError:
            await ctx.send("Response timeout! Please run the command again if you want to quit.")

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

        if last_work_time and current_time - last_work_time < timedelta(days=1):
            remaining_time = timedelta(days=1) - (current_time - last_work_time)
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await ctx.send(f"```You can only go to work once every day. Try again in {hours} hours and {minutes} minutes.```")
            return

        if userjob == "Unemployed":
            await ctx.send("```You need a job to go to work!```")
            return
    
        work_cooldowns[user_id] = current_time

        skill_values = []
        jobskillreq = ALLJOBS.get(careerfield)[4]
        for skill in jobskillreq:
            skill_value = skillslist.get(skill, [0])
            skill_values.append(skill_value[0])

        jobaddperc = random.randint(10, 40)
        newjobperc = careerprog + jobaddperc
        jobdict = globals().get(careerfield)
        promotioncareer = list(jobdict.keys())[careerlevel]
        promotionsalary, promotionbonus = jobdict[promotioncareer][1:3]
        promotionsalary = round(promotionsalary * (random.randint(100, 115) / 100))
        promotionbonus = round(promotionbonus * (random.randint(100, 115) / 100))
        promotionlevel = careerlevel + 1
        currency = await bank.get_currency_name(ctx.guild)

        if newjobperc >= 100:
            if all(promotionlevel <= skill_value for skill_value in skill_values):
                newjobperc -= 100
                await self.config.member(ctx.author).userjob.set(promotioncareer)
                await self.config.member(ctx.author).careerlevel.set(promotionlevel)
                await self.config.member(ctx.author).salary.set(promotionsalary)
                await bank.deposit_credits(ctx.author, promotionbonus)
                await ctx.send(
                    f"Promoted from {userjob} to {promotioncareer}!\n"
                    f"New salary: {humanize.intcomma(promotionsalary)} {currency}, with a bonus of {humanize.intcomma(promotionbonus)} {currency}."
                )
            else:
                newjobperc = 99
                missing_skills = [skill for skill, value in zip(jobskillreq, skill_values) if promotionlevel > value]
                await ctx.send(f"Increase your {','.join(missing_skills)} skill(s) to level {promotionlevel} for promotion!")

        await bank.deposit_credits(ctx.author, salary)
        await self.config.member(ctx.author).careerprog.set(newjobperc)
        await ctx.send(f"Worked in the {careerfield} Field, earning {humanize.intcomma(salary)} {currency}.")

    @slscareers.command(name="careerreview", aliases=["cr"])
    async def slscareers_careerreview(self, ctx: commands.Context):
        """Review current career information."""
        userjob = await self.config.member(ctx.author).userjob()
        careerfield = await self.config.member(ctx.author).careerfield()
        careerprog = await self.config.member(ctx.author).careerprog()
        careerlevel = await self.config.member(ctx.author).careerlevel()
        salary = await self.config.member(ctx.author).salary()
        username = await self.config.member(ctx.author).username()
        currency = await bank.get_currency_name(ctx.guild)
        maxjoblevel = len(globals().get(careerfield))

        jobinfo = ALLJOBS.get(careerfield)
        if not jobinfo:
            await ctx.send("```Career information not found.```")
            return
        if userjob == "Unemployed":
            await ctx.send("```You are currently unemployed.```")
            return

        progressionbar = f"[{'█' * (careerprog // 10)}{'░' * (10 - careerprog // 10)}]"

        em = discord.Embed(
            title=f"{username}'s Career Review",
            description=f"**Field:** {careerfield}\n**Position:** {userjob}\n**Level:** {careerlevel}/{maxjoblevel}\n"
                    f"**Salary:** {humanize.intcomma(salary)} {currency}\n**Progress:** {progressionbar}",
            color=discord.Color.red()
        )
        em.set_image(url=jobinfo[1])
        await ctx.send(embed=em)

    @commands.group(aliases=["slsa"])
    async def slsactions(self, ctx: commands.Context):
        """Use items in your inventory for various purposes."""
        return
    
    @slsactions.command(name="duel", aliases=["d"])
    async def slsactions_duel(self, ctx: commands.Context, user: discord.Member = None) -> None:
        """Challenge someone to a duel. Higher dueling or martial arts skill increases chance of success."""

        if user == None:
            await ctx.send("You have to pick someone to duel!")
            return
        
        userinventory = await self.config.member(ctx.author).userinventory()
        otherinventory = await self.config.member(user).userinventory()
        othername = await self.config.member(user).username()
        if othername == "None":
            othername = user.display_name

        await ctx.send("Pick a duel weapon (type it with caps at the start pls): `Lightsaber`, `Cutlass`, `Broadsword`, or `Martial Arts`")

        weaponlist = ["lightsaber", "cutlass", "broadsword", "martial arts"]

        def check(message):
            return message.author == ctx.author and message.content.lower() in ["lightsaber", "cutlass", "broadsword", "martial arts"]
        
        
        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            if message.content.lower() in weaponlist:
                weapon = message.content
                if weapon in userinventory:
                    if weapon in otherinventory:
                        await ctx.send(f"You have selected {weapon} as your choice of weapon.")
                    else:
                        await ctx.send(f"It appears {othername} doesn't have that weapon. Ask them what weapons they have!")
                        return
                elif weapon == "Martial Arts":
                    await ctx.send("You have chosen to use martial arts in your duel.")
                else:
                    await ctx.send("It looks like maybe you don't have that weapon. Choose one you do have.")
                    return
            else:
                await ctx.send("That doesn't appear to be a real weapon in the weapon list.")
                return
        except asyncio.TimeoutError:
            await ctx.send("Response timeout! Please run the command again if you want to duel.")
            return
        
        await ctx.send(f"{othername} do you accept the duel? (yes/no)")

        def check2(message2):
            return message2.author == user and message2.content.lower() in ["yes", "no"]
        
        try:
            message2 = await self.bot.wait_for('message', timeout=30.0, check=check2)
            if message2.content.lower() == "yes":
                await ctx.send(f"{othername} accepted the duel!")
            else:
                await ctx.send(f"{othername} rejected the duel!")
                return
        except asyncio.TimeoutError:
            await ctx.send("Response timeout! Please run the command again if you want to duel.")
            return
        
        skillslist = await self.config.member(ctx.author).skillslist()
        otherskillslist = await self.config.member(user).skillslist()

        randmessage = []
        user_skill = 0
        other_skill = 0
        if weapon == "Lightsaber":
            randmessage = LightsaberList
            user_skill = skillslist.get("Dueling", [0])[0] + skillslist.get("Force-wielding", [0])[0]
            other_skill = otherskillslist.get("Dueling", [0])[0] + otherskillslist.get("Force-wielding", [0])[0]
            skillsupdate = ["Dueling", "Force-wielding"]
        elif weapon == "Cutlass":
            randmessage = CutlassList
            user_skill = skillslist.get("Dueling", [0])[0]
            other_skill = otherskillslist.get("Dueling", [0])[0]
            skillsupdate = ["Dueling"]
        elif weapon == "Broadsword":
            randmessage = BroadswordList
            user_skill = skillslist.get("Dueling", [0])[0]
            other_skill = otherskillslist.get("Dueling", [0])[0]
            skillsupdate = ["Dueling"]
        elif weapon == "Martial Arts":
            randmessage = MartialArtsList
            user_skill = skillslist.get("Martial Arts", [0])[0]
            other_skill = otherskillslist.get("Martial Arts", [0])[0]
            skillsupdate = ["Martial Arts"]

        # Calculate probabilities
        skill_difference = user_skill - other_skill
        base_chance = 0.5
        skill_multiplier = 0.05
        if skill_difference > 0:
            user_win_chance = base_chance + abs(skill_difference) * skill_multiplier
        else:
            user_win_chance = base_chance - abs(skill_difference) * skill_multiplier

        username = await self.config.member(ctx.author).username()
        if username == "None":
            username = ctx.author.display_name
        
        user1 = username
        user2 = othername
        randmessleng = len(randmessage) - 1
        await ctx.send("The duel is beginning... May the best party win.")
        randint = random.randint(3, 5)
        for _ in range(randint):
            await asyncio.sleep(2)
            randuser = random.randint(1, 2)
            randpick = random.randint(0, randmessleng)
            if randuser == 1:
                user1 = username
                user2 = othername
            else:
                user1 = othername
                user2 = username
            await ctx.send(randmessage[randpick].format(user1=user1, user2=user2))
        outcome = random.random()
        reward = random.randint(100, 400)
        currency = await bank.get_currency_name(ctx.guild)
        if outcome < user_win_chance:
            userbalance = await bank.get_balance(user)
            for i in range(len(skillsupdate)):
                await self.practice_skill(ctx, skillsupdate[i], False)
            if reward >= userbalance:
                await bank.withdraw_credits(user, userbalance)
                await bank.deposit_credits(ctx.author, userbalance)
                await ctx.send(f"Congratulations {username}, you won the duel! For winning the duel, you have stolen {userbalance} {currency} from {othername}!")
            else:
                await bank.withdraw_credits(user, reward)
                await bank.deposit_credits(ctx.author, reward)
                await ctx.send(f"Congratulations {username}, you won the duel! For winning the duel, you have stolen {userbalance} {currency} from {othername}!")
        else:
            userbalance = await bank.get_balance(ctx.author)
            for i in range(len(skillsupdate)):
                await self.practice_skill(ctx, skillsupdate[i], False, user)
            if reward >= userbalance:
                await bank.withdraw_credits(ctx.author, userbalance)
                await bank.deposit_credits(user, userbalance)
                await ctx.send(f"{othername} has defeated you in the duel! They have stolen {userbalance} {currency} from you!")
            else:
                await bank.withdraw_credits(ctx.author, reward)
                await bank.deposit_credits(user, reward)
                await ctx.send(f"{othername} has defeated you in the duel! They have stolen {userbalance} {currency} from you!")
            
