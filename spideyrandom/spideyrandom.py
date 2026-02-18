from __future__ import annotations
import discord
from discord import app_commands
from redbot.core import commands
import json 
import os
import random
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LISTS_FILE = os.path.join(BASE_DIR, 'lists.json')

def load_json():
    if not os.path.exists(LISTS_FILE):
        return {}
    with open(LISTS_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def save_json(data):
    with open(LISTS_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

class GroupAdd(discord.ui.Modal, title="Add to a Random Group"):
    def __init__(self, bot, group:dict):
        super().__init__()
        self.bot = bot
        self.group = group

        self.group_items = discord.ui.TextInput(
            label="Add items (separate by ;)",
            style=discord.TextStyle.long,
            required=True
        )
        self.add_item(self.group_items)
    
    async def on_submit(self, interaction):
        group_raw = self.group_items.value
        stripped_group_items = [g.strip() for g in self.group_raw.strip(';') if g.strip()]
        for _ in stripped_group_items:
            self.group["random_list"].append(stripped_group_items[_])
            





class SpideyRandom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lists = load_json()

    random = app_commands.Group(name="random")

    @random.command(name="group_make", description="Make a random list group.")
    @app_commands.describe(
        item_type="The items in the group.",
        group_name="What you want the group to be named.",
        public="Whether you want others to use the list."
    )
    @app_commands.Choice(item_type=[
        app_commands.Choice(name="Normal (str)", value="str"),
        app_commands.Choice(name="Numbers (int)", value="int"),
        app_commands.Choice(name="People (member)", value="member")
    ])
    async def group_make(self, interaction:discord.Interaction, item_type:str, group_name:str, public:bool=False, group_desc:str="None"):
        user_id = str(interaction.user.id)
        
        user_dict = self.lists.setdefault(user_id, {})
        new_list = user_dict.setdefault(group_name, {})
        new_list.setdefault("random_list", [])
        new_list["item_type"] = item_type
        new_list["public"] = public
        new_list["desc"] = group_desc
    
    async def group_name_autocomplete(self, interaction:discord.Interaction, current:str):
        user_id = interaction.user.id

        user_dict = self.lists.setdefault(user_id, {})

        choices = []

        for list in user_dict.keys():
            if list in current.lower():
                choices.append(app_commands.Choice(name=list.title(), value=list))

        return choices[:25]


    @random.command(name="add_to_group", description="Add items to a group.")
    @app_commands.describe(
        group_name="The group to add to",
        member="Only if group is a member type"
    )
    @app_commands.autocomplete(group_name=group_name_autocomplete)
    async def add_to_group(self, interaction:discord.Interaction, group_name:str, member:discord.Member=None):
        user_id = str(interaction.user.id)
        user_dict = self.lists.setdefault(user_id, {})
        if not user_dict[group_name]:
            return interaction.response.send_message("Either that group doesn't yet exist or you're trying to add it to someone else's group.", ephemeral=True)
        
        group = user_dict[group_name]
        group_type = group_name["item_type"]
        if group_type is not "member" and member:
            return interaction.response.send_message(f"Your group is a {group_type}. Members should only be added to member groups.", ephemeral=True)
        elif group_type is "member" and not member:
            return interaction.response.send_message("Member groups should have members in them.", ephemeral=True)
        elif group_type is "member":
            group["random_list"].append(member)
        else:
            await interaction.response.send_modal(
                self=self, bot=self.bot, group=group
            )

    @random.command(name="pick", description="Get a random item from your random groups.")
    @app_commands.describe(
        group_name="The group to use"
    )
    @app_commands.autocomplete(group_name=group_name_autocomplete)
    async def pick(self, interaction:discord.Interaction, group_name:str)
        user_id = str(interaction.user.id)
        user_dict = self.lists.setdefault(user_id, {})
        if not user_dict[group_name]:
            return interaction.response.send_message("Either that group doesn't yet exist or it's someone else's group.", ephemeral=True)
        
        group = user_dict[group_name]
        