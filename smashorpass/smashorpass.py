import requests
import random
import discord
from discord.ext import commands
from redbot.core.bot import Red
from redbot.core import commands, Config
import asyncio 
import os
import json
from discord import app_commands
API_TOKEN = "7da42651e96d7411de160cc921140e8b"
API_URL = f"https://superheroapi.com/api/{API_TOKEN}/"

CUSTOM_FILE = os.path.join(os.path.dirname(__file__), "custom.json")
BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), "blacklist.json")
MOD_CHANNEL_ID = 1287700985275355150


def load_json(file_path, default):
    if not os.path.exists(file_path):
        return default

    with open(file_path, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
            if not isinstance(data, list):
                return default
            return data   
        except json.JSONDecodeError:
            return default

def save_json(file_path, data):
    if not isinstance(data, list):
        return
    
    if len(data) == 0 and os.path.exists(file_path):
        return
    
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def save_custom_entry(name, image_url, user_id):
    """Saves the entry to custom.json"""
    data = load_json(CUSTOM_FILE, [])

    if not isinstance(data, list):
        data = []

    original_name = name
    counter = 1
    existing_names = {entry["name"].lower() for entry in data}
    while name.lower() in existing_names:
        name = f"{original_name} ({counter})"
        counter += 1
        
    data.append({"name": name, "image": image_url, "user_id": user_id})

    save_json(CUSTOM_FILE, data)

    return name
    
def get_random_custom():
    """Gets a random character from custom.json"""
    if not os.path.exists(CUSTOM_FILE):
        return "No custom characters added yet!", None
    
    with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not data:
        return "No custom characters found.", None
    character = random.choice(data)
    return character["name"], character["image"]

def is_blacklisted(user_id):
    if not os.path.exists(BLACKLIST_FILE):
        return False
    
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as file:
        blacklist = json.load(file)
    
    return str(user_id) in blacklist

def get_random_starwarscharacter():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "starwars.json")

    with open(filename, "r", encoding="utf-8") as file:
        json_data = json.load(file)
    
    character = random.choice(json_data)

    name = character["name"]
    image_url = character["image"]
    return name, image_url


def get_random_superhero():
    character_id = random.randint(1, 731)
    response = requests.get(f"{API_URL}/{character_id}/image")

    if response.status_code == 200:
        data = response.json()
        if data["response"] == "success":
            name = data["name"]
            image_url = data["url"].replace("\\", "")
            return name, image_url
        else:
            return "Error: Character not found.", None
    else:
        return f"Error: API request failed with status {response.status_code}", None

def update_votes(character_name, vote_type, user_id):
    """Update smash/pass count and prevent duplicate votes."""
    if not os.path.exists(CUSTOM_FILE):
        return False
    
    with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    for entry in data:
        if entry["name"].lower() == character_name.lower():
            if user_id in entry.get("voters", []):
                return False
            
            entry.setdefault("smashes", 0)
            entry.setdefault("passes", 0)
            
            entry[vote_type] += 1
            entry.setdefault("voters", []).append(user_id)

            with open(CUSTOM_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
            
            return True
    
    return False

class UserUploadsView(discord.ui.View):
    def __init__(self, interaction, entries):
        super().__init__()
        self.entries = entries
        self.index = 0
        self.interaction = interaction
    
    async def update_message(self, interaction):
        entry = self.entries[self.index]
        embed = discord.Embed(title=f"Uploads by {interaction.user.display_name}")
        embed.add_field(name="Name", value=entry["name"], inline=True)
        embed.set_image(url=entry["image"])
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.entries)
        await self.update_message(interaction)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.entries)
        await self.update_message(interaction)

class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, sorted_data):
        super().__init__()
        self.ctx = ctx
        self.sorted_data = sorted_data
        self.index = 0
    
    async def update_message(self, interaction):
        entry = self.sorted_data[self.index]
        rank = self.index + 1
        uploader = f"<@{entry['user_id']}>" if entry.get("user_id") else "Default Category"

        embed = discord.Embed(title="🏆 Smash or Pass Leaderboard 🏆")
        embed.add_field(name="Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="Votes", value=f"🔥 {entry['smashes']} | ❌ {entry['passes']}", inline=True)
        embed.add_field(name="Uploader", value=uploader, inline=True)
        embed.set_image(url=entry["image"])
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction:discord.Interaction, button:discord.ui.Button):
        self.index = (self.index - 1) % len(self.sorted_data)
        await self.update_message(interaction)
    
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.sorted_data)
        await self.update_message(interaction)

class CategorySelect(discord.ui.Select):
    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id

        options = [
            discord.SelectOption(label="Superheroes", description="Smash or Pass on Superheroes!"),
            discord.SelectOption(label ="Star Wars", description="Smash or Pass on Star Wars characters!"),
            discord.SelectOption(label="Custom", description="Use community uploaded characters!")
        ]
        super().__init__(placeholder="Choose your category. . .", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your menu!", ephemeral=True)
        
        category = self.values[0]
        await self.bot.get_cog("SmashOrPass").config.member(interaction.user).category.set(category)

        await interaction.response.send_message(f"Category set to **{category}**!", ephemeral=True)

class CategoryView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=30)
        self.add_item(CategorySelect(bot, user_id))

class SmashPassView(discord.ui.View):
    def __init__(self, character_name, ctx):
        super().__init__(timeout=30)
        self.character_name = character_name
        self.ctx = ctx
    
    @discord.ui.button(label="Smash", style=discord.ButtonStyle.green, emoji="🔥")
    async def smash_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        first_vote = update_votes(self.character_name, "smashes", interaction.user.id)
        await interaction.response.send_message(f"{interaction.user.mention} chose **Smash** for {self.character_name}! 🔥", ephemeral=False)
    
    @discord.ui.button(label="Pass", style=discord.ButtonStyle.red, emoji="❌")
    async def pass_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        first_vote = update_votes(self.character_name, "passes", interaction.user.id)
        await interaction.response.send_message(f"{interaction.user.mention} chose **Pass** for {self.character_name}! ❌", ephemeral=False)

class SmashOrPass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9237492836492)
        self.config.register_member(
            category="Superheroes"
        )
    
    @app_commands.command(name="sopappeal", description="Appeal a Smash or Pass blacklist")
    @app_commands.describe(reason="Explain why you should be unblacklisted")
    async def sopappeal(self, interaction: discord.Interaction, reason: str):
        """Submits a blacklist appeal for mod review."""
        if not is_blacklisted(interaction.user.id):
            await interaction.response.send_message("❌ You are not blacklisted!", ephemeral=True)
            return
        
        mod_channel = self.bot.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            await interaction.response.send_message("❌ Appeal system is unavailable. Contact a moderator!", ephemeral=True)
            return
        
        embed = discord.Embed(title="⚠️ Blacklist Appeal Submitted")
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Moderators: Use /sopblacklist to remove a blacklist.")
        
        await mod_channel.send(embed=embed)
        await interaction.response.send_message("✅ Your appeal has been submitted. Moderators will review it soon!", ephemeral=True)
    
    @app_commands.command(name="soplist", description="View images uploaded by a specific user")
    @app_commands.describe(user="Select a user (leave blank to see your own images)")
    async def soplist(self, interaction: discord.Interaction, user: discord.User = None):
        """Shows all uploaded images by a user."""
        target_user = user or interaction.user

        if not os.path.exists(CUSTOM_FILE):
            await interaction.response.send_message("No custom characters exist!", ephemeral=True)
            return
        
        with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        user_entries = [entry for entry in data if entry["user_id"] == target_user.id]

        if not user_entries:
            await interaction.response.send_message(f"❌ No uploads found for **{target_user.mention}**!", ephemeral=True)
            return
        
        view=UserUploadsView(interaction, user_entries)
        await view.update_message(interaction)
    
    @app_commands.command(name="sopleaderboard", description="View the Smash or Pass leaderboard!")
    async def soplevels(self, interaction: discord.Interaction):
        """Displays the leaderboard with a slideshow format."""
        if not os.path.exists(CUSTOM_FILE):
            await interaction.response.send_message("❌ No votes recorded yet!", ephemeral=True)
            return
        
        with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        sorted_data = sorted(data, key=lambda x: x.get("smashes", 0), reverse=True)
        if not sorted_data:
            await interaction.response.send_message("❌ No characters have been voted on yet!", ephemeral=True)
            return
        
        view = LeaderboardView(interaction, sorted_data)
        message = await interaction.response.send_message("📊 Loading leaderboard...", ephemeral=False, view=view)
        await view.update_message(message)
    
    
    
    @app_commands.command(name="sopupload", description="Upload a custom character for Smash or Pass.")
    @app_commands.describe(
        name="Enter the character's name",
        url="Enter an image URL (optional if attaching an image)",
        image="Upload an image file (optional if providing a URL)"
    )
    async def sopupload(self, interaction: discord.Interaction, name: str, url: str = None, image: discord.Attachment = None):
        """Allow users to upload an image via a URL or file attachment."""
        if is_blacklisted(interaction.user.id):
            await interaction.response.send_message("❌ You are **blacklisted** from uploading images!", ephemeral=True)

        if image:
            if not image.content_type or not image.content_type.startswith("image/"):
                await interaction.response.send_message("❌ Please upload a valid image file!", ephemeral=True)
                return
            image_url = image.url
        elif url:
            image_url = url
        else:
            await interaction.response.send_message("❌ You must provide either an image attachment or a URL!", ephemeral=True)
            return
        
        new_name = save_custom_entry(name, image_url, interaction.user.id)
        await interaction.response.send_message(f"✅ **{new_name}** has been added to the custom category!", ephemeral=False)
    
    @app_commands.command(name="sopdelete", description="Remove an uploaded character (self or mod)")
    @app_commands.describe(
        name="Delete by character name (if you're a mod, this is optional if you're deleting all images uploaded by a user)",
        user="Delete all uploads by a user (mods only)",
        fulldelete="Delete all images by this user (only applies if user is provided)"
    )
    async def sopdelete(self, interaction: discord.Interaction, name: str = None, user: discord.User = None, fulldelete: bool = False):
        """Allows users to delete their own images and mods to remove any."""
        if not os.path.exists(CUSTOM_FILE):
            await interaction.response.send_message("No custom characters exist!", ephemeral=True)
            return
        
        with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if user and interaction.user.guild_permissions.manage_messages:
            if fulldelete:
                data = [entry for entry in data if entry["user_id"] != user.id]
                message = f"✅ **All** uploads from {user.mention} have been removed! Use `/sopblacklist` to prevent them from uploading if you think that's warranted."
            elif name:
                new_data  = []
                found = False
                for entry in data:
                    if entry["name"].lower() == name.lower() and entry["user_id"] == user.id:
                        found = True
                        continue
                    new_data.append(entry)
                
                if found:
                    data = new_data
                    message = f"✅ **{name}** by {user.mention} has been removed!"
                else:
                    message = f"❌ No entry **{name}** found for {user.mention}."
            else:
                await interaction.response.send_message("❌ You must provide either **name** or **all:true**!", ephemeral=True)
                return
        else:
            found = False
            new_data = []
            for entry in data:
                if entry["name"].lower() == name.lower():
                    if entry["user_id"] == interaction.user.id:
                        found = True
                        continue
                new_data.append(entry)
            if found:
                data = new_data
                message = f"✅ Character **{name}** has been removed!"
            else:
                message = "❌ You do not have permission to delete this character."
        
        with open(CUSTOM_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        
        await interaction.response.send_message(message, ephemeral=False)
    
    @app_commands.command(name="sopblacklist", description="Blacklist/unblacklist a user from uploading images")
    @app_commands.describe(user="Select the user to blacklist/unblacklist")
    @commands.has_permissions(manage_messages=True)
    async def sopblacklist(self, interaction:discord.Interaction, user:discord.User):
        """Toggles a user's blacklist status for uploading images."""
        if os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as file:
                blacklist = json.load(file)
        else:
            blacklist = {}
        
        user_id_str = str(user.id)

        if user_id_str in blacklist:
            del blacklist[user_id_str]
            action = "✅ **Unblacklisted**"
        else:
            blacklist[user_id_str] = user.name
            action = "❌ **Blacklisted**"
        
        with open(BLACKLIST_FILE, "w", encoding="utf-8") as file:
            json.dump(blacklist, file, indent=4)
        
        await interaction.response.send_message(f"{action} {user.mention} from uploading images!", ephemeral=False)

    @commands.command(name="smashorpass", aliases=["sop"])
    async def smashorpass(self, ctx:commands.Context):
        """Generates an image with which a person can react smash or pass."""
        category = await self.config.member(ctx.author).category()

        if category == "Star Wars":
            name, image = get_random_starwarscharacter()
        elif category == "Custom":
            name, image = get_random_custom()
        else:
            name, image = get_random_superhero()

        if not image:
            await ctx.send("Error fetching character. Try again!")
            return
        
        embed = discord.Embed(title=f"Smash or Pass: {name}")
        embed.set_image(url=image)
        embed.set_footer(text=f"Would you rather smash or pass {name}?")

        view = SmashPassView(name, ctx)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="sopsettings", aliases=["sops"])
    async def sopsettings(self, ctx:commands.Context):
        """Choose your Smash or Pass category using a dropdown menu."""
        view = CategoryView(self.bot, ctx.author.id)
        await ctx.send("Select your preferred category:", view=view)
    
    
