from __future__ import annotations
import discord
import logging
import asyncio
from datetime import datetime, timedelta
import random
from discord.ext import tasks, commands
from discord.ext.commands import BucketType
from discord.ui import View, Button
from random import choice
import aiohttp
from typing import Dict, List, Literal, Optional, Any, NoReturn
from abc import ABC
from discord import Member, Guild, File
from collections import Counter
import humanize
from functools import partial
import time
from discord import app_commands



from redbot.core import Config, checks, commands, bank
from redbot.core.config import Config
from redbot.core.commands import Cog


from .storestuff import FOODITEMS, SKILLITEMS, VEHICLES, ENTERTAINMENT, LUXURYITEMS, ALLITEMS
from .skills import SKILLSLIST, MAGICSTANCES, MAGICSKILLS, BROADSWORDSKILLS, LIGHTSABERSKILLS, CUTLASSSKILLS, FORCEPOWERS, FORCESTANCES, SKILLTREES
from .jobs import ALLJOBS, CAREEROPPOSITE, SUBJOBS, Culinary, Business, Programming, Medicine, LawEnforcement, Artist, Film, Military, Writing, SocialMedia, Athletic, Legal, Journalism, Engineering, Music, Science, Education, Politics, Criminal, Astronaut, Fashion, Sith, SecretAgent, Jedi, Sailor, DarkWarrior, ValiantKnight, Pirate, MurderDrone
from .traits import HINDRANCES, SOCIALTRAITS, VALUETRAITS, NATURETRAITS, INTERESTTRAITS, ALLTRAITS
from .alignment import AlignmentManager


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
current_traits = []
consechigheffort = 0
burnoutapplied = None
grantedtraits = []

LEARNEDSKILLS = {
    "Spells": [],
    "Lightsaber Techniques": [],
    "Broadsword Techniques": [],
    "Cutlass Techniques": [],
    "Force Powers": []
}

STANCES = {
    "Aggressive": False,
    "Defensive": False,
    "Balanced": False,
    "Chaotic": False,
    "Tactical": False,
    "Horseback": False,
    "Utility": False,
    "Neutral": True,
    "Good": False,
    "Evil": False,
    "Harry Potter Spells": False
}

EQUIVALENTSKILLS = {
    "force": {
        "skill": "Force-wielding",
        "dict": FORCEPOWERS,
    },
    "magic": {
        "skill": "Magic",
        "dict": MAGICSKILLS,
    },
    "lightsaber": {
        "skill": "Dueling",
        "dict": LIGHTSABERSKILLS,
    },
    "cutlass": {
        "skill": "Dueling",
        "dict": CUTLASSSKILLS,
    },
    "broadsword": {
        "skill": "Dueling",
        "dict": BROADSWORDSKILLS
    },
}

learnableabilities = []

next_refresh_time = None

async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.json()

def paginate(data, page_size=5):
    pages = []
    page = []
    total_pages = (len(data) // page_size) + (1 if len(data) % page_size != 0 else 0)  # Calculate total pages

    for idx, (trait, body) in enumerate(data.items()):
        description = body.get("description")
        page.append(f"**{trait}**: {description}")
        if len(page) == page_size or idx == len(data) - 1:
            pages.append("\n".join(page))
            page = []

    for i in range(len(pages)):
        pages[i] += f"\n\nPage {i+1}/{total_pages}"

    return pages


class SpideyLifeSim(Cog):
    """Various life simulation functions to play around with!"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.alignmentmanager = AlignmentManager()
        self.config = Config.get_conf(self, identifier=684457913250480143, force_registration=True)
        fooddefault = random.choice(list(FOODITEMS.keys()))
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
            skillslist = SKILLSLIST,
            consechigheffort = 0,
            burnoutapplied = None,
            alignment = 0,
            allymilestone = "Neutral",
            grantedtraits = [],
            learnedskills = LEARNEDSKILLS,
            learnedstances = STANCES,
            learnableabilities = []
        )


    
    def cog_unload(self):
        self.storerefresh.cancel()

    @tasks.loop(hours=6)
    async def storerefresh(self):

            store_slots.clear()
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
    




    async def practice_skill(self, interaction:discord.Interaction, skillname:str, progress: bool = True, user: discord.Member = None):
        """Handle the skill practice process with a progress bar."""
        user = user or interaction.user
        skillslist = await self.config.member(user).skillslist()
        username = await self.config.member(user).username()
        if username == "None":
            username = user.display_name
        
        usertraits = await self.config.member(user).usertraits()
        skillvalues = skillslist.get(skillname, [0, 0, [], []])
        print(f"Debug: skillvalues for {skillname} are {skillvalues}")
        if len(skillvalues) < 2:
            await interaction.followup.send(f"Error: Invalid data for {skillname}. If you see this error, please report it.")
            return
        
        skilllevel, skillprogress = skillvalues[:2]
        forbidden_traits = {
            "Hydrophobic": ["Swimming", "Sailing"],
            "Pacifist": ["Dueling", "Martial Arts"],
            "Humorless": ["Comedy"],
            "No-nonsense": ["Comedy"],
            "Pirate": ["Programming", "Social Media"],
            "Medieval": ["Programming", "Social Media"],
        }
        for trait, forbidden_skills in forbidden_traits.items():
            if trait in usertraits and skillname in forbidden_skills:
                await interaction.followup.send(
                    f"```Your {trait} trait prevents you from practicing {skillname}.```"
                )
                return
    
        skilladdperc = random.randint(5, 33)
        boost_traits = SKILLSLIST.get(skillname)[2]
        for trait in boost_traits:
            if trait in usertraits:
                skilladdperc = int(skilladdperc * 1.2)
        
        hindrance_traits = ["Absent-Minded", "Lazy"]
        for trait in hindrance_traits:
            if trait in usertraits:
                skilladdperc = int(skilladdperc * 0.8)
        
        skilladdperc = max(skilladdperc, 1)
        newskillperc = skillprogress + skilladdperc

        if skilllevel >= 10:
            skilllevel = 10
            skillslist[skillname] = [skilllevel, 100]
            await interaction.followup.send(f"You have maxed {skillname}! You cannot get it any higher!")
            return

        if newskillperc >= 100:
            newskillperc -= 100
            skilllevel += 1
            await interaction.followup.send(f"Congratulations, {username}! Your {skillname} skill is now Level {skilllevel}!")

        skillslist[skillname] = [skilllevel, newskillperc]
        await self.config.member(user).skillslist.set(skillslist)
        if progress == True:
            def generate_progress_bar(percentage):
                """Generate a progress bar with blocks for a percentage."""
                filled_blocks = int(percentage // 10) 
                empty_blocks = 10 - filled_blocks
                return f"[{'█' * filled_blocks}{'░' * empty_blocks}]"

            await interaction.followup.send(
                f"```You improved {skillname} skill by {skilladdperc}%, reaching {generate_progress_bar(newskillperc)} towards Level {skilllevel + 1}.```"
            )
        else:
            return
        
    sls = app_commands.Group(name="spideylifesim", description="Don't forget to set up your profile first!")
    skills = app_commands.Group(name="skills", description="Commands related to skills.", parent=sls)
    careers = app_commands.Group(name="careers", description="Commands related to careers.", parent=sls)
    store = app_commands.Group(name="store", description="Commands related to the store.", parent=sls)
    profile = app_commands.Group(name="profile", description="Commands related to user profiles.", parent=sls)

    @store.command(name="storeview", description="View the currently in-store items!")
    async def slsstore_storeview(self, interaction: discord.Interaction):
        """View the currently in-store items!"""
        currency = await bank.get_currency_name(interaction.guild)
        items = [FOODITEMS, SKILLITEMS, VEHICLES, ENTERTAINMENT, LUXURYITEMS]
        store_items = [item.get(store_slots[i]) for i, item in enumerate(items)]
        store_title = "Here's what's available in the shop right now:"

        next_iter = getattr(self.storerefresh, "next_iteration", None) or getattr(
            self.storerefresh, "_next_iteration", None
        )
        if next_iter is not None:
            now = datetime.now(next_iter.tzinfo) if next_iter.tzinfo else datetime.now()
            remaining = (next_iter - now).total_seconds()

            if remaining < 0:
                remaining = 0
            
            remaining = int(remaining)
            hours, remainder = divmod(remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            cooldown_timer = f"**Next refresh in:** {hours}h {minutes}m {seconds}s"
        else:
            cooldown_timer = "Next refresh time is being calculated."


        store_items_text = "\n".join(
            [f"**Slot {i + 1}:** {humanize.intcomma(item)} {currency} for {store_slots[i]}" for i, item in enumerate(store_items)]
        ) + f"\n{cooldown_timer}"

        store_image = "https://mydigitalwirral.co.uk/wp-content/uploads/2020/02/bigstock-Empty-Store-Front-With-Window-324188686.jpg"

        async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
            async with session.get(store_image, ssl=False) as response:
                if response.status != 200:
                    await interaction.response.send_message("Failed to fetch store image.")
                    return

        embed = discord.Embed(title=store_title, description=store_items_text, color=discord.Color.red())
        embed.set_image(url=store_image)
        await interaction.response.send_message(embed=embed)

    @store.command(name="purchase", description="Purchase an item from the store by specifying its slot number.")
    @app_commands.describe(storeslot="The store slot number (1-5) of the item you want to purchase.", itemcount="The number of items you want to purchase (default is 1).")
    async def slsstore_purchase(self, interaction: discord.Interaction, storeslot: int, itemcount: int = 1):
        """Input the store slot of the item you want to purchase in the command!"""
        if not (1 <= storeslot <= 5):
            await interaction.response.send_message("The store slot provided doesn't exist. Please input one of the store slots from 1-5.")
            return

        item_for_purchase = store_slots[storeslot - 1]
        item_cost = ALLITEMS.get(item_for_purchase)
        if itemcount <= 0:
            await interaction.response.send_message(f"I don't think it's possible to buy {itemcount} items.")
            return
        if itemcount > 10:
            await interaction.response.send_message("That seems like a lot... Maybe buy a little less!")
            return

        currency = await bank.get_currency_name(interaction.guild)
        total_cost = item_cost * itemcount
        if not await bank.can_spend(interaction.user, total_cost):
            await interaction.response.send_message(f"You have an insufficient balance! You need {total_cost} {currency}.")
            return

        await bank.withdraw_credits(interaction.user, total_cost)
        async with self.config.member(interaction.user).userinventory() as inventory:
            inventory.extend([item_for_purchase] * itemcount)

        user_balance = await bank.get_balance(interaction.user)
        item_plural = "s" if itemcount > 1 else ""
        await interaction.response.send_message(f"You have successfully purchased {itemcount} {item_for_purchase}{item_plural}.\n"
                   f"Remaining balance: {humanize.intcomma(user_balance)} {currency}.")

    async def inventory_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete function for inventory items."""
        current = current.lower()
        user_inventory = await self.config.member(interaction.user).userinventory()
        unique_items = set(user_inventory)
        choices = []
        for item in unique_items:
            if current in item.lower():
                choices.append(app_commands.Choice(name=item, value=item))
        return choices[:25]

    @store.command(name="sellitem", description="Sell items which returns 80% of their original value.")
    @app_commands.describe(itemtosell="The item you want to sell (case-sensitive).", count="The number of items you want to sell (default is 1).")
    async def slsstore_sellitem(self, interaction: discord.Interaction, count: int = 1, *, itemtosell: str):
        """Sell items which returns 80% of their original value. Case-sensitive."""
        if not itemtosell:
            await interaction.response.send_message("Please specify the item you want to sell.")
            return
        if count <= 0:
            await interaction.response.send_message("How can you sell items you don't have? :thinking:")
            return

        user_inventory = await self.config.member(interaction.user).userinventory()
        if itemtosell not in user_inventory:
            await interaction.response.send_message(f"You don't have {itemtosell}. Check your inventory for spelling and case.")
            return
        currency = await bank.get_currency_name(interaction.guild)
        original_price = ALLITEMS.get(itemtosell)
        sell_price = round(original_price * 0.8)
        async with self.config.member(interaction.user).userinventory() as inventory:
            for _ in range(min(count, inventory.count(itemtosell))):
                inventory.remove(itemtosell)
                await bank.deposit_credits(interaction.user, sell_price)

        user_balance = await bank.get_balance(interaction.user)
        item_plural = "s" if count > 1 else ""
        await interaction.response.send_message(f"You sold {count} {itemtosell}{item_plural}. New balance: {humanize.intcomma(user_balance)} {currency}.")

    
    @profile.command(name="userprofile", description="See your user profile or another's.")
    @app_commands.describe(user="The user whose profile you want to view.")
    async def slsprofile_userprofile(self, interaction: discord.Interaction, user: discord.Member = None):
        """See your user profile."""
        if user is None:
            user = interaction.user
        user_data = await self.config.member(user).all()
        profilename = user_data["username"] if user_data["username"] != "None" else user.display_name
        currency = await bank.get_currency_name(interaction.guild)
        userbalance = await bank.get_balance(user)
        alignment = user_data["alignment"]
        alignmentprogress = self.alignmentmanager.generate_alignment_bar(alignment)
        profileheader = "Here is your profile!"
        profiledescription = (
            f"**Name:** {profilename}\n"
            f"**Gender:** {user_data['usergender']}\n"
            f"**Profession:** {user_data['userjob']} in the {user_data['careerfield']} field\n"
            f"**Traits:** {', '.join(user_data['usertraits'])}\n"
            f"**Granted Traits:**{', '.join(user_data['grantedtraits'])}\n"
            f"**Account Balance:** {humanize.intcomma(userbalance)} {currency}\n"
            f"**Alignment:**\n{alignmentprogress}\n"
        )
        await self.display_profile(interaction, profileheader, profiledescription, user_data["userpic"])

    @profile.command(name="setname", description="Change your profile name!")
    @app_commands.describe(name="The new name you want to set for your profile.")
    async def profile_setname(self, interaction: discord.Interaction, *, name: str):
        """Change your profile name!"""
        await self.update_and_confirm(interaction, "username", name)

    @profile.command(name="setgender", description="Set your gender.")
    @app_commands.describe(gender="Your gender.")
    async def profile_setgender(self, interaction: discord.Interaction, *, gender: str):
        """Set your gender."""
        await self.update_and_confirm(interaction, "usergender", gender)

    @profile.command(name="setpic", description="Set your profile image.")
    @app_commands.describe(link="The link to the image you want to set as your profile picture.")
    async def profile_setpic(self, interaction: discord.Interaction, *, link: str):
        """Set your profile image."""
        if not (link.startswith("http://") or link.startswith("https://")):
            await interaction.response.send_message("Please provide a valid URL starting with http:// or https://")
            return
        await self.update_and_confirm(interaction, "userpic", link)

    @profile.command(name="inventory", description="View your inventory.")
    async def profile_inventory(self, interaction: discord.Interaction):
        """View your inventory."""
        userinventory = await self.config.member(interaction.user).userinventory()
        item_counts = Counter(userinventory)
        formatted_items = [f"{count}x - {item}" if count > 1 else item for item, count in item_counts.items()]
        message = "```Here are all the items you have:\n- " + "\n- ".join(formatted_items) + "```"
        await interaction.response.send_message(message)


    @profile.command(name="resetprofile", description="Reset profile data - Not Undoable.")
    async def profile_resetprofile(self, interaction: discord.Interaction):
        """Reset profile data."""
        await self.confirm_action(
            interaction, 
            "This will completely reset your profile data! `Confirm` or `Cancel`", 
            self.reset_user_profile, 
            interaction.user
        )

    @profile.command(name="emptyaccount", description="Empty your Red Discord bank account - Not Undoable.")
    async def profile_emptyaccount(self, interaction: discord.Interaction):
        """Reset your bank balance to 0."""
        balance = await bank.get_balance(interaction.user)
        await self.confirm_action(
            interaction,
            "This will empty your bank account! `Confirm` or `Cancel`", 
            lambda user: bank.withdraw_credits(user, balance), 
            interaction.user
        )

    @profile.command(name="setalignment", description="Set your alignment to good or evil if you're neutral.")
    @app_commands.describe(alignment = "Choose your alignment: good or evil.")
    async def profile_setalignment(self, interaction: discord.Interaction, alignment: str):
        """Only works if you're neutral. Otherwise you'll have to influence alignment with actions."""
        allymilestone = await self.config.member(interaction.user).allymilestone()
        learnedstances = await self.config.member(interaction.user).learnedstances()

        if allymilestone != "Neutral":
            await interaction.response.send_message("You can't set your alignment if you're already aligned.")
            return

        await interaction.response.send_message("Are you going to fight for `good` or `evil`?")
        def check(message): return message.author == interaction.user and message.content.lower() in ["good", "evil"]
        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            if message.content.lower() == "good":
                await self.config.member(interaction.user).allymilestone.set("Radiant Wanderer")
                await self.config.member(interaction.user).alignment.set(25)
                learnedstances["Good"] = True
                await self.config.member(interaction.user).learnedstances.set(learnedstances)
                await interaction.response.send_message("You have successfully joined the path to good.")
            elif message.content.lower() == "evil":
                await self.config.member(interaction.user).allymilestone.set("Veiled Wanderer")
                await self.config.member(interaction.user).alignment.set(-25)
                learnedstances["Evil"] = True
                await self.config.member(interaction.user).learnedstances.set(learnedstances)
                await interaction.response.send_message("You have successfully joined the path to evil.")
            else:
                await interaction.response.send_message("That doesn't appear to be one of the accepted alignments. Try again.")
                return
        except asyncio.TimeoutError:
            await interaction.response.send_message("The prompt timed out. Please try again.")
            return
    
  
    
    @profile.command(name="traitsview", description="View traits and their descriptions via categories.")
    @app_commands.describe(category = "Choose a category: hindrances, social, values, nature, or interests.")
    @app_commands.choices(category=[
        app_commands.Choice(name="Hindrances", value="hindrances"),
        app_commands.Choice(name="Social", value="social"),
        app_commands.Choice(name="Values", value="values"),
        app_commands.Choice(name="Nature", value="nature"),
        app_commands.Choice(name="Interests", value="interests")
    ])
    async def profile_traitsview(self, interaction: discord.Interaction, category: str):
        """View traits and their descriptions via categories."""
        response = category.lower()
        if response == "hindrances":
            data = HINDRANCES
        elif response == "social":
            data = SOCIALTRAITS
        elif response == "values":
            data = VALUETRAITS
        elif response == "nature":
            data = NATURETRAITS
        elif response == "interests":
            data = INTERESTTRAITS
        else:
            await interaction.response.send_message("Looks like maybe you typed the category wrong! Try again please!")
            return
        pages = paginate(data)
        current_page = 0

        message = await interaction.response.send_message(pages[current_page])

        await message.add_reaction("⬅️") 
        await message.add_reaction("➡️") 

        def reaction_check(reaction, user):
            return user == interaction.user and reaction.message.id == message.id

        while True:
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=reaction_check)
                if str(reaction.emoji) == "➡️":
                    if current_page == len(pages) - 1:
                        current_page = 0
                    else:
                        current_page += 1
                    await message.edit(content=pages[current_page])
                    try:
                        await message.remove_reaction("➡️", interaction.user)
                    except discord.Forbidden:
                        pass
                elif str(reaction.emoji) == "⬅️":
                    if current_page == 0:
                            current_page = len(pages) - 1
                    else:
                            current_page -= 1
                    await message.edit(content=pages[current_page])
                    try:
                        await message.remove_reaction("⬅️", interaction.user)
                    except discord.Forbidden:
                        pass
            except asyncio.TimeoutError:
                await message.remove_reaction("➡️", self.bot.user)
                await message.remove_reaction("⬅️", self.bot.user)
                pass

    
            
    @profile.command(name="addtraits", description="Add up to 5 traits, ensuring one is a hindrance.")
    async def slsprofile_addtraits(self, interaction: discord.Interaction):
        """Allows users to add up to 5 traits, ensuring one is a hindrance. Cannot change traits once they're set unless you reset your profile."""
        user_traits = await self.config.member(interaction.user).usertraits()

        if len(user_traits) >= 5:
            await interaction.response.send_message("You already have the maximum number of traits (5). If you want to change your traits, you'll have to reset your profile or ask an admin to remove the traits.")
            return

        hindrance_traits = list(HINDRANCES.keys())
        selected_hindrance = await self.select_trait(interaction, hindrance_traits, "hindrance", 1)
        if not selected_hindrance:
            await interaction.response.send_message("No hindrance was selected. Please try the command again.")
            return

        user_traits.extend(selected_hindrance)

        all_traits = list({
            **SOCIALTRAITS,
            **VALUETRAITS,
            **NATURETRAITS,
            **INTERESTTRAITS,
            **HINDRANCES
        }.keys())

        
        selected_additional_traits = await self.select_trait(interaction, all_traits, "all traits", 4, user_traits)
        if len(selected_additional_traits) != 4:
            await interaction.response.send_message("You didn't select enough traits. Please try the command again.")
            return

        user_traits.extend(selected_additional_traits)
        await self.config.member(interaction.user).usertraits.set(user_traits)
        await interaction.response.send_message(f"Profile updated! Your traits are now:\n{', '.join(user_traits)}")

    async def select_trait(self, interaction, traits, category, max_traits, current_traits=[]):
        """Displays a trait selection page."""
        traits_per_page = 10
        total_pages = (len(traits) + traits_per_page - 1) // traits_per_page
        current_page = 0
        selected_traits = []

        def build_embed(page):
            start_idx = page * traits_per_page
            end_idx = start_idx + traits_per_page
            page_traits = traits[start_idx:end_idx]

            embed = discord.Embed(
                title=f"{category.capitalize()} Traits",
                description="\n".join([f"• **{trait}**" for trait in page_traits]),
                color=discord.Color.blurple()
            )
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
            return embed, page_traits

        def create_view(page_traits):
            view = View(timeout=600.0)
            for trait in page_traits:
                is_disabled = trait in current_traits or any(conflict in current_traits for conflict in ALLTRAITS.get(trait, {}).get("conflicts", []))
                button = Button(label=trait, style=discord.ButtonStyle.primary, disabled=is_disabled)

                async def button_callback(interaction, selected_trait=trait):
                    if max_traits is None or len(selected_traits) < max_traits:
                        selected_traits.append(selected_trait)
                        await interaction.response.send_message(f"Trait **{selected_trait}** added!", ephemeral=True)
                        if len(selected_traits) == max_traits:
                            view.stop()
                    else:
                        await interaction.response.send_message("You've already selected the maximum number of traits!", ephemeral=True)

                button.callback = button_callback
                view.add_item(button)

            if current_page > 0:
                prev_button = Button(label="Previous", style=discord.ButtonStyle.green)
                prev_button.callback = partial(update_message, view=view, page=current_page - 1)
                view.add_item(prev_button)

            if current_page < total_pages - 1:
                next_button = Button(label="Next", style=discord.ButtonStyle.green)
                next_button.callback = partial(update_message, view=view, page=current_page + 1)
                view.add_item(next_button)
            
            cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)
            cancel_button.callback = lambda interaction: cancel_selection(interaction, view)
            view.add_item(cancel_button)

            return view
        
        async def update_message(interaction, page, view):
            nonlocal current_page
            current_page = page
            embed, page_traits = build_embed(current_page)
            view = create_view(page_traits)
            await interaction.response.edit_message(embed=embed, view=view)
        
        async def cancel_selection(interaction, view):
            await interaction.response.send_message("Trait selection cancelled.", ephemeral=True)
            view.stop()

        embed, page_traits = build_embed(current_page)
        message = await interaction.response.send_message(embed=embed, view=create_view(page_traits))

        try:
            while len(selected_traits) < max_traits:
                await asyncio.sleep(0.1)
            await message.delete()
            return selected_traits
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")
            return []
    

    @profile.command(name="removetraits", description="Remove all traits from a user's profile. Admins only.")
    @app_commands.checks.has_permissions(administrator=True)
    async def slsprofile_removetraits(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Only usable by bot owners. This command is here for legitimate accidental trait additions. The idea is traits should not be changed during the lifetime of a character."""
        await self.config.member(user).usertraits.set([])
        await interaction.response.send_message(f"{user}'s traits have been deleted successfully.")


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
        await self.config.member(member).alignment.set(0)
        await self.config.member(member).allymilestone.set("Neutral")
        await self.config.member(member).grantedtraits.set([])
        await self.config.member(member).learnedskills.set(LEARNEDSKILLS)
        await self.config.member(member).learnedstances.set(STANCES)



    @skills.command(name="skillindex", description="See all available skills!")
    async def slsskills_skillindex(self, interaction: discord.Interaction):
        """See all available skills!"""
        skills_text = "```Here are all the available skills:\n- " + "\n- ".join(SKILLSLIST) + "```"
        await interaction.response.send_message(skills_text)

    @skills.command(name="skillprogress", description="Show your skill progress with progress bars!")
    async def slsskills_skillprogress(self, interaction: discord.Interaction):
        """Show your skill progress with progress bars!"""
        skillslist = await self.config.member(interaction.user).skillslist()

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
        await interaction.response.send_message(skillresult)
    
    async def skills_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete function for skills."""
        current = current.lower()
        choices = []
        for skill in SKILLSLIST.keys():
            if current in skill.lower():
                choices.append(app_commands.Choice(name=skill, value=skill))
        return choices[:25]

    @skills.command(name="practice", description="Work on a skill of your choice.")
    @app_commands.describe(skillname="The skill you want to practice.")
    @app_commands.autocomplete(skillname=skills_autocomplete)
    async def slsskills_practice(self, interaction: discord.Interaction, skillname: str):
        """Work on a skill of your choice (case-sensitive; starts with capitals)."""
        if skillname not in SKILLSLIST:
            await interaction.response.send_message("```This skill is not one of the accepted skills! Please consult the skill index and try again!```")
            return

        if await self.is_on_cooldown(interaction, skillname):
            return

        if not await self.has_required_items(interaction, skillname):
            return

        await self.practice_skill(interaction, skillname)
        cooldown_duration = timedelta(minutes=60)  # Adjust duration as needed
        current_time = datetime.now()
        user_cooldowns = skill_cooldowns.get(interaction.user.id, {})
        user_cooldowns[skillname] = current_time + cooldown_duration
        skill_cooldowns[interaction.user.id] = user_cooldowns

    async def is_on_cooldown(self, interaction, skillname):
        """Check if the user is on cooldown for a skill."""
        current_time = datetime.now()
        user_cooldowns = skill_cooldowns.get(interaction.user.id, {})
        if skillname in user_cooldowns:
            cooldown_time = user_cooldowns[skillname]
            if current_time < cooldown_time:
                remaining_seconds = (cooldown_time - current_time).total_seconds()
                minutes, seconds = divmod(int(remaining_seconds), 60)
                await interaction.response.send_message(f"```You're so tired from practicing {skillname}. Try waiting {minutes} minutes and {seconds} seconds to practice again.```" if minutes else f"```You're so tired from practicing {skillname}. Try waiting {seconds} seconds to practice again.```")
                return True
        return False

    async def has_required_items(self, interaction, skillname):
        """Check if the user has the required items to practice a skill."""
        skillsinfo = SKILLSLIST.get(skillname, [])
        if len(skillsinfo) < 4:
            return True
        required_items = skillsinfo[3]
        userinventory = await self.config.member(interaction.user).userinventory()
        if required_items and not any(item in userinventory for item in required_items):
            await interaction.response.send_message(f"```You need one of these items to practice {skillname}: {', '.join(required_items)}. Buy them from the store!```")
            return False
        return True
    
    # decide whether to do this or not
    '''
    @slsskills.command(name="study", aliases=["s"])
    @commands.cooldown(rate=1, per=1800, type=BucketType.user)
    async def slsskills_study(self, ctx: commands.Context):
        """Study further into a specific style."""
        learnedskills = await self.config.member(ctx.author).learnedskills()
        learnedstances = await self.config.member(ctx.author).learnedstances()
        skillslist = await self.config.member(ctx.author).skillslist()
        userinventory = await self.config.member(ctx.author).userinventory()
        learnableabilities = await self.config.member(ctx.author).learnableabilities()
        study = None
        await ctx.send("Would you prefer to study a specific skill or learn general stances? `Skills` or `Stances`")
        def check(message):
            return message.author == ctx.author and message.content.lower() in ['skills', 'stances']
        
        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            study = message.content.lower()
        except asyncio.TimeoutError:
            await ctx.send("Response timed out. Please try again.")
            self.slsskills_study.reset_cooldown(ctx)
            return
        
        randvalue = random.randint(0, 3)
        if randvalue == 0:
            await ctx.send("You tried to study, but you were unable to find anything pertinent.")
            return
        
        studyfield = None
        stanceavailable = []
        if study == "skills":
            await ctx.send("Pick a skill area to study in: `magic`, `force`, `lightsaber`, `cutlass`, or `broadsword`")
            def check(message):
                return message.author == ctx.author and message.content.lower() in ['magic', 'force', 'lightsaber', 'cutlass', 'broadsword']
            
            try:
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                studyfield = message.content.lower()
                skillreq = skillslist.get(EQUIVALENTSKILLS.get(studyfield).get("skill"))
                if not skillreq:
                    await ctx.send(f"Error: The required skill for {studyfield} could not be found.")
                    return
                skillreq = skillreq[0]
                if skillreq < 1:
                    await ctx.send("Unfortunately that skill requires at least level 1 in that field.")
                    self.slsskills_study.reset_cooldown(ctx)
                    return
                skilldict = EQUIVALENTSKILLS.get(studyfield).get("dict")
                for i in skilldict.keys():
                    if learnedstances.get(i):
                        stanceavailable.append(i)
                if not stanceavailable:
                    await ctx.send("You need to have a learned stance to learn skills in that field.")
                    self.slsskills_study.reset_cooldown(ctx)
                    return
                validability = None
                attemptlimit = 50
                attempts = 0
                while not validability and attempts < attemptlimit:
                    attempts += 1
                    stance = random.choice(stanceavailable)
                    for ability, values in skilldict[stance].items():
                        requiredskill = values[0]
                        abilitydesc = values[1]
                        if skillreq >= requiredskill and ability not in learnedskills:
                            validability = (stance, ability, abilitydesc)
                            break
                if not validability:
                    await ctx.send("No valid abilities were found that match your skill level! Try learning more stances or practicing your skill more.")
                    self.slsskills_study.reset_cooldown(ctx)
                    return
                stance, ability, abilitydesc = validability
                await ctx.send(f"You have discovered a new ability in the {stance} stance: **{ability}**!")
                learnableabilities.append(ability)
                await self.config.member(ctx.author).learnableabilities.set(learnableabilities)
                
                
            except asyncio.TimeoutError:
                await ctx.send("Response Timeout!")
                self.slsskills_study.reset_cooldown(ctx)
                return
        elif study == "stances":
            validstances = [stance for stance in learnedstances if learnedstances[stance] == False]
            validstances.remove("Good", "Evil")
            if "Horseback" in validstances and "Horse" not in userinventory:
                validstances.remove("Horseback")

            if not validstances:
                await ctx.send("No stances are available for you to learn at this time.")
                self.slsskills_study.reset_cooldown(ctx)
                return
            
            validstance = random.choice(validstances)
            await ctx.send(f"You have discovered the stance **{validstance}**! Feel free to use it in duels!")
            learnedstances[validstance] = True
            await self.config.member(ctx.author).learnedstances.set(learnedstances)
    
    
    @slsskills.command(name="learn", aliases=["l"])
    @commands.cooldown(rate=1, per=1800, type=BucketType.user)
    async def slsskills_learn(self, ctx: commands.Context):
        learnableabilities = await self.config.member(ctx.author).learnableabilities()
        learnedskills = await self.config.member(ctx.author).learnedskills()
        await ctx.send(f"Which skill would you like to learn: {', '.join(learnableabilities)}")
        def check(message): return message.author == ctx.author and message.content.lower() in map(str.lower, learnableabilities)
        skill = None
        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            skillinput = message.content.strip()
            skill = next(skill for skill in learnableabilities if skill.lower() == skillinput.lower())
            randvalue = random.randint(0, 3)
            if randvalue == 0:
                await ctx.send("You aren't quite certain you've grasped all the functions of this ability. Maybe try practicing some more?")
                return
            learnedskills.append(skill)
            learnableabilities.remove(skill)
            await ctx.send(f"You have successfully added {skill} to your ability list!")
            await self.config.member(ctx.author).learnedskills.set(learnedskills)
            await self.config.member(ctx.author).learnableabilities.set(learnableabilities)
        except asyncio.TimeoutError:
            await ctx.send("Response timed out! Please try again!")
            self.slsskills_learn.reset_cooldown(ctx)
            return
        except StopIteration:
            await ctx.send("An error occurred matching the skill. Please try again.")
            self.slsskills_learn.reset_cooldown(ctx)

    
    @slsskills_study.error
    async def slsskills_study_error(self, ctx, error):
        """Handle errors for the study command"""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
    
    @slsskills_learn.error
    async def slsskills_learn_error(self, ctx, error):
        """Handle errors for the study command"""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
    
    @slsskills.command(name="subskillview", aliases=["ssv"])
    async def slsskills_subskillview(self, ctx: commands.Context):
        """View your progress on sub-skills."""
        learnedskills = await self.config.member(ctx.author).learnedskills()
        learnedstances = await self.config.member(ctx.author).learnedstances()
        learnedstances.remove("Good", "Evil", "Neutral")
        groupedskills = {category: [] for category in SKILLTREES}
        for category, skillsorstances in SKILLTREES.items():
            if isinstance(skillsorstances, dict):
                for subcategory, abilities in skillsorstances.items():
                    for ability, values in abilities.items():
                        if ability in learnedskills:
                            groupedskills[category].append(f"{subcategory} - {ability}")
        
        description = f"**Duel Stances**: {', '.join(learnedstances)}\n"
        for category, skills in groupedskills.items():
            if skills:
                description += f"\n**{category}**: {', '.join(skills)}"

        em = discord.Embed(title="Here is your subskill progress", 
                           description=description)
        await ctx.send(embed=em)

    '''


        
    @careers.command(name="careerindex", description="See an index of all available careers!")
    async def slscareers_careerindex(self, interaction: discord.Interaction):
        """See an index of all available careers!"""
        indexseparator = "\n- "
        await interaction.response.send_message(f"```Here is a list of all the available career paths:\n- {indexseparator.join(ALLJOBS)}```")

    async def career_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete function for careers."""
        current = current.lower()
        choices = []
        for career in ALLJOBS.keys():
            if current in career.lower():
                choices.append(app_commands.Choice(name=career, value=career))
        return choices[:25]

    async def subcareer_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete function for subcareers."""
        current = current.lower()
        top_level_career = interaction.namespace.careername
        if top_level_career not in ALLJOBS:
            return []
        choices = []
        for subcareer in SUBJOBS.keys():
            if current in subcareer.lower() and subcareer in CAREEROPPOSITE[top_level_career]:
                choices.append(app_commands.Choice(name=subcareer, value=subcareer))
        return choices[:25]

    @careers.command(name="aboutcareer", description="See more information about a particular career!")
    @app_commands.describe(careername="The career you want to learn about.")
    @app_commands.autocomplete(careername=career_autocomplete)
    async def slscareers_aboutcareer(self, interaction: discord.Interaction, careername: str):
        """See more information about a particular career! Ensure correct spelling/capitalization."""
        await interaction.response.defer(thinking=True)
        
        if not careername:
            await interaction.followup.send("```Please specify the career you want to learn about!```")
            return
    
        if careername not in ALLJOBS:
            await interaction.followup.send("```The specified career wasn't found. Double-check spelling and try again!```")
            return
        
        jobdict = ALLJOBS
        if ALLJOBS[careername] == None:
            jobdict = SUBJOBS
            jobopts = CAREEROPPOSITE[careername]
            await interaction.followup.send(f"Would you like to see the career information for `{jobopts[0]}` or `{jobopts[1]}`?")
            def check(message): return message.author == interaction.user and message.content in jobopts

            try: 
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                if message.content == jobopts[0]:
                    careername = jobopts[0]
                elif message.content == jobopts[1]:
                    careername = jobopts[1]
                else:
                    await interaction.followup.send("Please check your spelling and try again.")
                    return
            except asyncio.TimeoutError:
                await interaction.followup.send("Prompt timed out. Please try again.")
                return

        jobinfo = jobdict[careername]
        requiredskills = jobinfo[4]
        em = discord.Embed(
            title=careername, 
            description=f"{jobinfo[0]}\n**Boss:** {jobinfo[2]}\n**Required skill(s):** {', '.join(requiredskills)}", 
            color=discord.Color.red()
        )
        em.set_image(url=jobinfo[1])
        await interaction.followup.send(embed=em)

    @careers.command(name="careerapply", description="Apply to a career of your choosing!")
    @app_commands.describe(jobname="The career you want to apply for.")
    @app_commands.autocomplete(jobname=career_autocomplete)
    async def slscareers_careerapply(self, interaction: discord.Interaction, jobname: str):
        """Apply to a career of your choosing!"""
        if not jobname:
            await interaction.response.send_message("```Specify a job name to apply!```")
            return

        userjob = await self.config.member(interaction.user).userjob()
        careerfield = await self.config.member(interaction.user).careerfield()

        if careerfield == jobname:
            await interaction.response.send_message("```You're already in that career!```")
            return
        if userjob != "Unemployed":
            await interaction.response.send_message("```Quit your existing job before applying to a new one!```")
            return
        if jobname not in ALLJOBS:
            await interaction.response.send_message("```Job not found. Try retyping it!```")
            return
        
        maindict = ALLJOBS
        if ALLJOBS.get(jobname) == None:
            maindict = SUBJOBS
            jobopts = CAREEROPPOSITE.get(jobname)
            alignment = await self.config.member(interaction.user).alignment()
            if alignment > 0:
                await interaction.response.send_message("Because you are good, the following career seems ideal for you:")
                jobname = jobopts[0]
            elif alignment < 0:
                await interaction.response.send_message("Because you are evil, the following career seems ideal for you:")
                jobname = jobopts[1]
            else:
                await interaction.response.send_message("You need to have an alignment for that career path!")
                return
            
    
        jobdict = globals().get(jobname)
        if not jobdict:
            await interaction.response.send_message("```Internal error! Contact support if this persists.```")
            return

        maincareerlist = maindict[jobname]
        requiredskills = maincareerlist[4]
        currency = await bank.get_currency_name(interaction.guild)
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
        await interaction.response.send_message(embed=em)
        await interaction.response.send_message("Type `Confirm` to secure this job or `Cancel` to cancel.")

        def check(message):
            return message.author == interaction.user and message.content.lower() in ["confirm", "cancel"]
        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            if message.content.lower() == "confirm":
                await interaction.response.send_message(f"Congratulations {interaction.user.mention}, you've been hired for the {jobname} job!")
                await self.config.member(interaction.user).userjob.set(startercareer)
                await self.config.member(interaction.user).careerfield.set(jobname)
                await self.config.member(interaction.user).careerlevel.set(1)
                await self.config.member(interaction.user).salary.set(salary)
                async with self.config.member(interaction.user).userinventory() as inventory:
                    inventory.extend(maincareerlist[3])
                recruitmessage = discord.Embed(title=f"Message from {maincareerlist[2]}", description=f"{maincareerlist[6]}")
                recruitmessage.set_thumbnail(url=maincareerlist[5])
                await interaction.response.send_message(embed=recruitmessage)
            else:
                await interaction.response.send_message(f"Application for {jobname} has been canceled.")
        except asyncio.TimeoutError:
            await interaction.response.send_message("Response timeout! Application canceled.")

    @careers.command(name="quitjob", description="Quit your job with this function!")
    async def slscareers_quitjob(self, interaction: discord.Interaction):
        """Quit your job with this function!"""
        userjob = await self.config.member(interaction.user).userjob()
        careerfield = await self.config.member(interaction.user).careerfield()
        if userjob == "Unemployed":
            await interaction.response.send_message("You can't quit a job if you don't have a job.")
            return

        await interaction.response.send_message(f"Are you sure you want to quit your job as a {userjob}? Type `Yes` or `No`.")
    
        def check(message):
            return message.author == interaction.user and message.content.lower() in ["yes", "no"]

        if careerfield in SUBJOBS.keys():
            maincareerlist = SUBJOBS[careerfield]
        else:
            maincareerlist = ALLJOBS[careerfield]

        try:
            message = await self.bot.wait_for('message', timeout=30.0, check=check)
            if message.content.lower() == "yes":
                await interaction.response.send_message("You have quit your job!")
                await self.config.member(interaction.user).userjob.set("Unemployed")
                await self.config.member(interaction.user).careerfield.set("Unemployed")
                await self.config.member(interaction.user).careerprog.set(0)
                await self.config.member(interaction.user).careerlevel.set(0)
                await self.config.member(interaction.user).salary.set(0)
                for i in maincareerlist[3]:
                    async with self.config.member(interaction.user).userinventory() as inventory:
                        if i in inventory:
                            inventory.remove(i)
                leavemessage = discord.Embed(title=f"Message from {maincareerlist[2]}", description=f"{maincareerlist[7]}")
                leavemessage.set_thumbnail(url=maincareerlist[5])
                await interaction.response.send_message(embed=leavemessage)
            else:
                await interaction.response.send_message("Resignation canceled.")
        except asyncio.TimeoutError:
            await interaction.response.send_message("Response timeout! Please run the command again if you want to quit.")

    @careers.command(name="gotowork", description="Go to work at your job!")
    @app_commands.describe(effort="How much effort to put into work today?")
    @app_commands.choices(effort=[
        app_commands.Choice(name="Low", value="low"),
        app_commands.Choice(name="Normal", value="normal"),
        app_commands.Choice(name="High", value="high")
    ])
    async def slscareers_gotowork(self, interaction: discord.Interaction, effort: str):
        """Go to work at your job!"""
        await interaction.response.defer(thinking=True)
        user_id = interaction.user.id
        userjob = await self.config.member(interaction.user).userjob()
        careerfield = await self.config.member(interaction.user).careerfield()
        careerprog = await self.config.member(interaction.user).careerprog()
        careerlevel = await self.config.member(interaction.user).careerlevel()
        skillslist = await self.config.member(interaction.user).skillslist()
        salary = await self.config.member(interaction.user).salary()
        usertraits = await self.config.member(interaction.user).usertraits()
        username = await self.config.member(interaction.user).username()
        consechigheffort = await self.config.member(interaction.user).consechigheffort()
        burnoutapplied = await self.config.member(interaction.user).burnoutapplied()
        grantedtraits = await self.config.member(interaction.user).grantedtraits()
        alignment = await self.config.member(interaction.user).alignment()
        burnoutbool = None
        if username == "None":
            username = interaction.user.display_name

        current_time = datetime.now()
        last_work_time = work_cooldowns.get(user_id)

        if last_work_time and current_time - last_work_time < timedelta(days=1):
            remaining_time = timedelta(days=1) - (current_time - last_work_time)
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.followup.send(f"```You can only go to work once every day. Try again in {hours} hours and {minutes} minutes.```")
            return

        if userjob == "Unemployed":
            await interaction.followup.send("```You need a job to go to work!```")
            return
        firebool = False
        oppositecareer = None
        oppvalue = None
        for key, value in CAREEROPPOSITE.items():
            if careerfield in value:
                oppositecareer = key
                if careerfield == value[0] and alignment <= -25:
                    firebool = True
                    oppvalue = 1
                elif careerfield == value[1] and alignment >= 25:
                    firebool = True
                    oppvalue = 0
                break
            
        if firebool == True:
            await interaction.followup.send(f"You are becoming too {'evil' if oppvalue == 1 else 'good'} for the {careerfield} field. Your supervisor has words to say:")
            em = discord.Embed(
                title=f"Message from {SUBJOBS.get(careerfield)[2]}",
                description=f"{SUBJOBS.get(careerfield)[8]}"
            )
            em.set_thumbnail(url=SUBJOBS.get(careerfield)[5])
            await interaction.response.send_message(embed=em)
            afterlevel = careerlevel - 2 if careerlevel - 2 > 0 else 1
            await self.config.member(interaction.user).userjob.set("Unemployed")
            await self.config.member(interaction.user).careerfield.set("Unemployed")
            await self.config.member(interaction.user).careerprog.set(0)
            await self.config.member(interaction.user).careerlevel.set(0)
            await self.config.member(interaction.user).salary.set(0)
            for i in SUBJOBS.get(careerfield)[3]:
                async with self.config.member(interaction.user).userinventory() as inventory:
                    if i in inventory:
                        inventory.remove(i)
                
            await asyncio.sleep(3)
            oppcareername = CAREEROPPOSITE.get(oppositecareer)[oppvalue]
            oppdict = globals().get(oppcareername)
            opposingcareer = SUBJOBS.get(oppcareername)
            em2 = discord.Embed(
                title=f"Message from {opposingcareer[2]}",
                description = f"{opposingcareer[9]}"
            )
            em2.set_thumbnail(url=opposingcareer[5])
            await interaction.followup.send(embed=em2)
            currency = await bank.get_currency_name(interaction.guild)
            nextposition = list(oppdict.keys())[afterlevel - 1]
            nextsalary = oppdict[nextposition][1]
            await interaction.followup.send(
                f"You are being offered the position: {nextposition}, starting at level {afterlevel} "
                f"with a daily salary of {humanize.intcomma(nextsalary)} {currency}. Do you accept? `yes` or `no`"
            )
            def check(message):
                    return message.author == interaction.user and message.content.lower() in ['yes', 'no']

            try:
                message = await self.bot.wait_for('message', timeout=30.0, check=check)
                if message.content.lower() == "yes":
                    await self.config.member(interaction.user).userjob.set(nextposition)
                    await self.config.member(interaction.user).careerfield.set(oppcareername)
                    await self.config.member(interaction.user).salary.set(nextsalary)
                    await self.config.member(interaction.user).careerlevel.set(afterlevel)
                    for i in opposingcareer[3]:
                        async with self.config.member(interaction.user).userinventory() as inventory:
                            inventory.append(i)
                    await interaction.followup.send("You have accepted the offer and started your new career!")
                    return
                else:
                    await interaction.followup.send("You declined the offer. You are currently unemployed.")
                    return
            except asyncio.TimeoutError:
                await interaction.followup.send("Your response timed out. Unfortunately, the offer is no longer on the table.")
                return


        if "Burned Out" in grantedtraits:
            current_time = datetime.now()
            if burnoutapplied:
                burnoutdate = datetime.fromisoformat(burnoutapplied)
                if current_time - burnoutdate > timedelta(days=7):
                    grantedtraits.remove("Burned Out")
                    await self.config.member(interaction.user).grantedtraits.set(grantedtraits)
                    await self.config.member(interaction.user).burnoutapplied.set(None)
                    await interaction.followup.send("You've recovered from your burnout and feel refreshed!")
                else:
                    await interaction.followup.send(
                        "You're burned out! Your performance will be signifcantly reduced.\n"
                        "Try taking it easy for a day to recover."
                    )
            else:
                grantedtraits.remove("Burned Out")
                await self.config.member(interaction.user).grantedtraits.set(grantedtraits)
                await interaction.followup.send("There has been an error with your traits. You appear to have burnout but no set burnout date. Burned Out was removed from your traits, but if you ever see this error again, please report it.")

        goodtraits = ["Driven Achiever", "Disciplined", "Workaholic", "Lucky"]
        badtraits = ["Lazy", "Reckless", "Pessimist", "Absent-Minded", "Insane", "Defiant Rebel", "Easily Frightened"]
        notraits = ["Lazy", "Absent-Minded", "Defiant Rebel"]
        yestraits = ["Driven Achiever", "Disciplined", "Workaholic"]
        preclusiontraits = []

        if effort == "high":
                for trait in notraits:
                    if trait in usertraits:
                        preclusiontraits.append(trait)
                if preclusiontraits:
                    await interaction.followup.send(f"{username} has the traits {', '.join(preclusiontraits)} and can't work hard because of them.")
                    return
                if "Burned Out" in grantedtraits: 
                    await interaction.followup.send("You're burned out and can't push yourself any harder.")
                    return
                consechigheffort += 1
                burnoutthreshold = 4 if any(trait in usertraits for trait in yestraits) else 3
                if consechigheffort > burnoutthreshold:
                    burnoutbool = True
                effort_modifier = random.randint(30, 60)

        if effort == "normal":
                effort_modifier = random.randint(15, 45)
                if "Burned Out" in grantedtraits and any(trait in usertraits for trait in yestraits):
                    burnoutbool = False

        if effort == "low":
                for trait in yestraits:
                    if trait in usertraits:
                        preclusiontraits.append(trait)
                if preclusiontraits:
                    await interaction.followup.send(f"Because {username} has the traits {usertraits}, they aren't content with putting in low effort at work.")
                    return
                if "Burned Out" in grantedtraits:
                    burnoutbool = False
                effort_modifier = random.randint(-10, 10)
        
        if effort != "high":
            consechigheffort = 0
        
        await self.config.member(interaction.user).consechigheffort.set(consechigheffort)
        
        work_cooldowns[user_id] = current_time

        skill_values = []
        careerdict = ALLJOBS
        if careerfield not in ALLJOBS:
            careerdict = SUBJOBS
        jobskillreq = careerdict.get(careerfield)[4]
        for skill in jobskillreq:
            skill_value = skillslist.get(skill, [0])
            skill_values.append(skill_value[0])

        jobtraitbenefit = sum(5 for trait in usertraits if trait in goodtraits)
        jobtraitbenefit -= sum(5 for trait in usertraits if trait in badtraits)

        jobaddperc = effort_modifier + jobtraitbenefit

        if "Burned Out" in grantedtraits:
            burnoutpenalty = abs(jobaddperc) * 0.5
            jobaddperc -= burnoutpenalty
            await interaction.followup.send("Your performance was reduced by 50% due to burnout.")
        
        newjobperc = careerprog + jobaddperc
        jobdict = globals().get(careerfield)
        promotioncareer = list(jobdict.keys())[careerlevel]
        promotionsalary, promotionbonus = jobdict[promotioncareer][1:3]
        promotionsalary = round(promotionsalary * (random.randint(100, 115) / 100))
        promotionbonus = round(promotionbonus * (random.randint(100, 115) / 100))
        promotionlevel = careerlevel + 1
        currency = await bank.get_currency_name(interaction.guild)

        if newjobperc >= 100 and promotionlevel < 10:
            if all(promotionlevel <= skill_value for skill_value in skill_values):
                newjobperc -= 100
                await self.config.member(interaction.user).userjob.set(promotioncareer)
                await self.config.member(interaction.user).careerlevel.set(promotionlevel)
                await self.config.member(interaction.user).salary.set(promotionsalary)
                await bank.deposit_credits(interaction.user, promotionbonus)
                await interaction.followup.send(
                    f"Promoted from {userjob} to {promotioncareer}!\n"
                    f"New salary: {humanize.intcomma(promotionsalary)} {currency}, with a bonus of {humanize.intcomma(promotionbonus)} {currency}."
                )
            else:
                newjobperc = 99
                missing_skills = [skill for skill, value in zip(jobskillreq, skill_values) if promotionlevel > value]
                await interaction.followup.send(f"Increase your {', '.join(missing_skills)} skill(s) to level {promotionlevel} for promotion!")
        if newjobperc >= 100 and promotionlevel >= 10:
            newjobperc = 50
            raiseamount = random.randint(5, 25)
            salary *= (1 + raiseamount / 100)
            await self.config.member(interaction.user).salary.set(salary)
            await interaction.followup.send(f"Because you're already at the maximum level in your career, you have instead received a raise of {raiseamount}% which increases your salary to {humanize.intcomma(round(salary))} {currency}!")

        if burnoutbool is not None:
            if burnoutbool == True:
                grantedtraits.append("Burned Out")
                await self.config.member(interaction.user).grantedtraits.set(grantedtraits)
                await self.config.member(interaction.user).burnoutapplied.set(datetime.now().isoformat())
                await interaction.followup.send("You pushed yourself too hard at work over the past couple days. You're burnt out now. Consider taking it easy.")
            elif burnoutbool == False:
                grantedtraits.remove("Burned Out")
                await self.config.member(interaction.user).grantedtraits.set(grantedtraits)
                await self.config.member(interaction.user).burnoutapplied.set(None)
                await interaction.followup.send("You've recovered from your burnout by putting in a more manageable effort today!")

        await bank.deposit_credits(interaction.user, salary)
        await self.config.member(interaction.user).careerprog.set(newjobperc)
        await interaction.followup.send(f"Worked in the {careerfield} Field, earning {humanize.intcomma(salary)} {currency}.")

    @careers.command(name="careerreview", description="Review current career information.")
    async def slscareers_careerreview(self, interaction: discord.Interaction):
        """Review current career information."""
        userjob = await self.config.member(interaction.user).userjob()
        careerfield = await self.config.member(interaction.user).careerfield()
        careerprog = await self.config.member(interaction.user).careerprog()
        careerlevel = await self.config.member(interaction.user).careerlevel()
        salary = await self.config.member(interaction.user).salary()
        username = await self.config.member(interaction.user).username()
        currency = await bank.get_currency_name(interaction.guild)
        burnoutapplied = await self.config.member(interaction.user).burnoutapplied()
        burnoutdesc = ""
        if "Burned Out" in grantedtraits:
            burnoutdate = datetime.fromisoformat(burnoutapplied)
            burnoutdesc = f"Currently burned out as of {humanize.naturaltime(burnoutdate)}."
        
        jobdict = ALLJOBS
        if careerfield not in ALLJOBS:
            jobdict = SUBJOBS
        jobinfo = jobdict.get(careerfield)
        if not jobinfo:
            await interaction.response.send_message("```Career information not found.```")
            return
        if userjob == "Unemployed":
            await interaction.response.send_message("```You are currently unemployed.```")
            return

        progressionbar = f"[{'█' * (careerprog // 10)}{'░' * (10 - careerprog // 10)}]"

        em = discord.Embed(
            title=f"{username}'s Career Review",
            description=f"**Field:** {careerfield}\n**Position:** {userjob}\n**Level:** {careerlevel}/10\n"
                    f"**Salary:** {humanize.intcomma(salary)} {currency}\n**Progress:** {progressionbar}\n{burnoutdesc}",
            color=discord.Color.red()
        )
        em.set_image(url=jobinfo[1])
        await interaction.response.send_message(embed=em)