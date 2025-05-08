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

ACTOR_LIST_URL = "https://api.themoviedb.org/3/person/popular?language=en-Us&page={page_number}"

HEADERS = {
    "accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI3ZWQxN2Y4NzE4Y2NjYmQ2MzgzYWM3ZTFmMjEwNzQ3ZSIsIm5iZiI6MTczOTIyOTM1Ni41NzIsInN1YiI6IjY3YWE4OGFjMDliODU1MWEwNGIwOTA5OSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.1N4OHN0YlUPqvT4w9YnjVP7yfMOl75rJWljb6eQ82BU"
}

SINGER_LIST_URL = "http://ws.audioscrobbler.com/2.0/?method=chart.gettopartists&page={page_number}&api_key=d5738e0d460367ef373d6167c5631fda&format=json"

CATEGORIES = ["Custom", "Actors", "Star Wars", "Superheroes", "Singers"]

REAL_CATEGORIES = ["Actors", "Singers"]

VOTES_FILE = os.path.join(os.path.dirname(__file__), "votes.json")

def load_votes():
    if not os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=4)

    with open(VOTES_FILE, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {}

def save_votes(votes):
    with open(VOTES_FILE, "w", encoding="utf-8") as file:
        json.dump(votes, file, indent=4)

def get_wikipedia_image(artist_name):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{artist_name.replace(' ', '_')}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("thumbnail", {}).get("source")
    return None

def get_random_singer():
    counter = 5
    for attempt in range(counter):
        page_number = random.randint(1, 6)
        response = requests.get(SINGER_LIST_URL.format(page_number=page_number))

        if response.status_code != 200:
            print(f"Error fetching singer list: {response.status_code}")
            continue
        
        try:
            artists = response.json().get("artists", {}).get("artist", [])
            if not artists:
                print("No artists found on this page.")
                continue
            for _ in range(len(artists)):
                singer = random.choice(artists)
                name = singer.get("name")
                image_url = get_wikipedia_image(name)

                if image_url:
                    return name, image_url
            
            print(f"All artists on page {page_number} lacked a medium-sized image.")
        except (ValueError, KeyError) as e:
            print(f"Error processing JSON response: {e}")
    
    print("Application was unable to find a singer after multiple attempts.")
    return None, None



def get_random_actor():

    while True:
        page_number = random.randint(1, 2)
        response = requests.get(ACTOR_LIST_URL.format(page_number=page_number), headers=HEADERS)

        if response.status_code != 200:
            print(f"Error fetching actor list: {response.status_code}")
            continue

        actors = response.json().get("results", [])

        if not actors:
            continue
    
    
        actor = random.choice(actors)
        name = actor.get("name", "Unknown Actor")
        image = f"https://image.tmdb.org/t/p/original{actor['profile_path']}" if actor.get("profile_path") else "No Image Available"

        return name, image


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

def update_votes(category, character_name, vote_type, user_id, image):
    """Update smash/pass count and prevent duplicate votes."""
    votes = load_votes()

    if category not in votes:
        votes[category] = {}
    
    if character_name not in votes[category]:
        votes[category][character_name] = {"smashes": 0, "passes": 0, "voters": [], "image": ""}
    
    if user_id in votes[category][character_name]["voters"]:
        return False
    
    votes[category][character_name][vote_type] += 1
    votes[category][character_name]["voters"].append(user_id)
    votes[category][character_name]["image"] = image

    save_votes(votes)

    return True

class UserUploadsView(discord.ui.View):
    def __init__(self, interaction, entries, target):
        super().__init__(timeout=60.0)
        self.entries = entries
        self.index = 0
        self.interaction = interaction
        self.target = target
    
    async def update_message(self):
        entry = self.entries[self.index]
        embed = discord.Embed(title=f"Uploads by {self.target.mention}")
        embed.add_field(name="Name", value=entry["name"], inline=True)
        embed.set_image(url=entry["image"])
        
        await self.interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.entries)
        await self.update_message()

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.entries)
        await self.update_message()

class LeaderboardView(discord.ui.View):
    def __init__(self, type, interaction, sorted_data, category: str = "All"):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.sorted_data = sorted_data
        self.index = 0
        self.category = category
        self.type = type
    
    async def update_message(self):
        entry = self.sorted_data[self.index]
        rank = self.index + 1

        votes = load_votes()
        char_category = "Unknown"
        for cat, characters in votes.items():
            if entry[0] in characters:
                char_category = cat
                break
        uploader = f"<@{entry[1]['user_id']}>" if entry[1].get("user_id") else "Default Category"

        embed = discord.Embed(title=f"🏆 Smash or Pass {self.type}board 🏆")
        embed.add_field(name="Name", value=entry[0])
        embed.add_field(name="Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="Votes", value=f"🔥 {entry[1]['smashes']} | ❌ {entry[1]['passes']}", inline=True)
        if uploader != "Default Category" and self.category != "All":
            embed.add_field(name="Uploader", value=uploader, inline=True)
        elif self.category == "All":
            embed.add_field(name="Category", value=f"{char_category}")
        if entry[1].get("image"):
            embed.set_image(url=entry[1].get("image", ""))

        await self.interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction:discord.Interaction, button:discord.ui.Button):
        self.index = (self.index - 1) % len(self.sorted_data)
        await self.update_message()
    
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.sorted_data)
        await self.update_message()

class CategorySelect(discord.ui.Select):
    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id

        options = [
            discord.SelectOption(label="All", description="Get a character from any category."),
            discord.SelectOption(label="Superheroes", description="Smash or Pass on Superheroes!"),
            discord.SelectOption(label ="Star Wars", description="Smash or Pass on Star Wars characters!"),
            discord.SelectOption(label="Custom", description="Use community uploaded characters!"),
            discord.SelectOption(label="Actors", description="Use actors for the Smash or Pass game!"),
            discord.SelectOption(label="Singers", description="Get people from the music field as your category."),
            discord.SelectOption(label="Real People", description="Only see categories including real people.")
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
    def __init__(self, character_name, category, image, ctx):
        super().__init__(timeout=30)
        self.character_name = character_name
        self.ctx = ctx
        self.image = image
        self.category = category
    
    @discord.ui.button(label="Smash", style=discord.ButtonStyle.green, emoji="🔥")
    async def smash_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        update_votes(self.category, self.character_name, "smashes", interaction.user.id, self.image)
        await interaction.response.send_message(f"{interaction.user.mention} chose **Smash** for {self.character_name}! 🔥", ephemeral=False)
    
    @discord.ui.button(label="Pass", style=discord.ButtonStyle.red, emoji="❌")
    async def pass_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        update_votes(self.category, self.character_name, "passes", interaction.user.id, self.image)
        await interaction.response.send_message(f"{interaction.user.mention} chose **Pass** for {self.character_name}! ❌", ephemeral=False)
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.ctx.message.edit(view=self)

class SmashOrPass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9237492836492)
        self.config.register_member(
            category="All"
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
        await interaction.response.defer()

        target_user = user or interaction.user

        if not os.path.exists(CUSTOM_FILE):
            await interaction.followup.send("No custom characters exist!", ephemeral=True)
            return
        
        with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        user_entries = [entry for entry in data if entry["user_id"] == target_user.id]

        if not user_entries:
            await interaction.followup.send_message(f"❌ No uploads found for **{target_user.mention}**!", ephemeral=True)
            return
        
        view=UserUploadsView(interaction, user_entries, target_user)
        await interaction.followup.send(f"Loading {target_user.mention}'s list . . . ", ephemeral=False, view=view)
        await view.update_message()
    
    @app_commands.command(name="sopleaderboard", description="View the Smash or Pass leaderboard!")
    @app_commands.choices(category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES])
    async def sopleaderboard(self, interaction: discord.Interaction, category: str=None):
        """Displays the leaderboard with a slideshow format."""
        votes = load_votes()
        
        await interaction.response.defer()
        
        if category:
            if category not in votes:
                await interaction.followup.send(f"❌ No votes recorded for **{category}**!", ephemeral=True)
                return
            category_data = votes[category]
        else:
            category_data = {name: data for cat in votes.values() for name, data in cat.items()}
        
        if not category_data:
            await interaction.follup.send("❌ No characters have been voted on yet!", ephemeral=True)
            return
        
        sorted_data = sorted(category_data.items(), key = lambda x: x[1].get("smashes", 0) - x[1].get("passes", 0), reverse=True)

        if category:
            view = LeaderboardView("Leader", interaction, sorted_data, category)
        else:
            view = LeaderboardView("Leader", interaction, sorted_data)

        await interaction.followup.send("📊 Loading leaderboard...", view=view)

        await view.update_message()
    
    @app_commands.command(name="soploserboard", description="View the Smash or Pass loserboard!")
    @app_commands.choices(category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES])
    async def soploserboard(self, interaction: discord.Interaction, category: str=None):
        """Displays the leaderboard with a slideshow format."""
        votes = load_votes()
        
        await interaction.response.defer()
        
        if category:
            if category not in votes:
                await interaction.response.send_message(f"❌ No votes recorded for **{category}**!", ephemeral=True)
                return
            category_data = votes[category]
        else:
            category_data = {name: data for cat in votes.values() for name, data in cat.items()}
        
        if not category_data:
            await interaction.response.send_message("❌ No characters have been voted on yet!", ephemeral=True)
            return
        
        sorted_data = sorted(category_data.items(), key = lambda x: x[1].get("passes", 0) - x[1].get("smashes", 0), reverse=True)

        if category:
            view = LeaderboardView("Loser", interaction, sorted_data, category)
        else:
            view = LeaderboardView("Loser", interaction, sorted_data)

        await interaction.followup.send("📊 Loading loserboard...", view=view)

        await view.update_message()

    
    
    
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
    async def sopblacklist(self, interaction:discord.Interaction, user:discord.User):
        """Toggles a user's blacklist status for uploading images."""

        if not interaction.user.guild_permissions.manage_permissions:
            await interaction.response.send_message("You don't have permission to blacklist people!", ephemeral=True)
            return

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

        if category == "All":
            category = random.choice(CATEGORIES)
        
        if category == "Real People":
            category = random.choice(REAL_CATEGORIES)

        if category == "Star Wars":
            name, image = get_random_starwarscharacter()
        elif category == "Custom":
            name, image = get_random_custom()
        elif category == "Actors":
            name, image = get_random_actor()
        elif category == "Singers":
            name, image = get_random_singer()
        else:
            name, image = get_random_superhero()

        if not image:
            await ctx.send("Error fetching character. Try again!")
            return
        
        embed = discord.Embed(title=f"Smash or Pass: {name}")
        embed.set_image(url=image)
        embed.set_footer(text=f"Would you rather smash or pass {name}?")

        view = SmashPassView(name, category, image=image, ctx=ctx)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="sopsettings", aliases=["sops"])
    async def sopsettings(self, ctx:commands.Context):
        """Choose your Smash or Pass category using a dropdown menu."""
        view = CategoryView(self.bot, ctx.author.id)
        await ctx.send("Select your preferred category:", view=view)
    
    
