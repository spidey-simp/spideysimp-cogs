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
from datetime import datetime, timedelta, timezone


CUSTOM_FILE = os.path.join(os.path.dirname(__file__), "custom.json")
BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), "blacklist.json")
MOD_CHANNEL_ID = 1287700985275355150

ACTOR_LIST_URL = "https://api.themoviedb.org/3/person/popular?language=en-Us&page={page_number}"


API_KEY_FILE = os.path.join(os.path.dirname(__file__), "api_keys.json")
VALID_APIS = ["superhero", "tmdb", "lastfm"]


CATEGORIES = ["Custom", "Actors", "Star Wars", "Superheroes", "Singers"]

REAL_CATEGORIES = ["Actors", "Singers"]

VOTES_FILE = os.path.join(os.path.dirname(__file__), "votes.json")

USER_BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), "user_blacklists.json")

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

def load_api_keys():
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_api_keys(data):
    with open(API_KEY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_user_blacklists():
    if not os.path.exists(USER_BLACKLIST_FILE):
        return {}
    with open(USER_BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_user_blacklists(data):
    with open(USER_BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def add_to_user_blacklist(user_id:int, category: str, name: str):
    data = load_user_blacklists()
    user_str = str(user_id)
    if user_str not in data:
        data[user_str] = {}
    if category not in data[user_str]:
        data[user_str][category] = []
    if name not in data[user_str][category]:
        data[user_str][category].append(name)
        save_user_blacklists(data)
        return True
    return False

def is_blacklisted_for_user(user_id: int, category: str, name: str):
    data = load_user_blacklists()
    return name in data.get(str(user_id), {}).get(category, [])

def get_wikipedia_image(artist_name):
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{artist_name.replace(' ', '_')}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("thumbnail", {}).get("source")
    return None

def get_random_singer(user_id=None):
    keys = load_api_keys()
    API_TOKEN = keys.get("lastfm")
    if not API_TOKEN:
        return "Key not found.", None

    for _ in range(5):
        page_number = random.randint(1, 6)
        SINGER_LIST_URL = f"http://ws.audioscrobbler.com/2.0/?method=chart.gettopartists&page={page_number}&api_key={API_TOKEN}&format=json"
        response = requests.get(SINGER_LIST_URL)

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

                if user_id and is_blacklisted_for_user(user_id, "Singers", name):
                    continue

                image_url = get_wikipedia_image(name)

                if image_url:
                    return name, image_url

            print(f"All artists on page {page_number} lacked a medium-sized image.")
        except (ValueError, KeyError) as e:
            print(f"Error processing JSON response: {e}")

    print("Application was unable to find a singer after multiple attempts.")
    return None, None




def get_random_actor(user_id = None):

    keys = load_api_keys()
    HEADERS = {
        "accept": "application/json",
        "Authorization": f"Bearer {keys.get('tmdb', '')}"
    }

    for attempt in range(5):
        page_number = random.randint(1, 50)
        try:
            response = requests.get(ACTOR_LIST_URL.format(page_number=page_number), headers=HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"TMDB fetch error: {e}")
            continue

        actors = response.json().get("results", [])
        if not actors:
            continue

        actor = random.choice(actors)
        name = actor.get("name", "Unknown Actor")
        if user_id and is_blacklisted_for_user(user_id, "Actors", name):
            continue

        image = f"https://image.tmdb.org/t/p/original{actor['profile_path']}" if actor.get("profile_path") else None

        return name, image

    return "Failed to fetch actor", None



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
    
def get_random_custom(user_id=None):
    """Gets a random character from custom.json"""
    if not os.path.exists(CUSTOM_FILE):
        return "No custom characters added yet!", None
    
    with open(CUSTOM_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not data:
        return "No custom characters found.", None
    for _ in range(5):
        character = random.choice(data)
        if user_id and is_blacklisted_for_user(user_id, "Custom", name=character["name"]):
            continue

        return character["name"], character["image"]
    
    return None, None

def is_blacklisted(user_id):
    if not os.path.exists(BLACKLIST_FILE):
        return False
    
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as file:
        blacklist = json.load(file)
    
    return str(user_id) in blacklist

def get_random_starwarscharacter(user_id=None):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(script_dir, "starwars.json")

        if not os.path.exists(filename):
            return "Missing Star Wars data", None

        with open(filename, "r", encoding="utf-8") as file:
            json_data = json.load(file)

        for _ in range(5):
            character = random.choice(json_data)
            name = character["name"]
            if user_id and is_blacklisted_for_user(user_id, "Star Wars", name):
                continue

            image_url = character["image"]
            return name, image_url
        return None, None
    except Exception as e:
        print(f"Star Wars load error: {e}")
        return "Failed to load Star Wars character", None



def get_random_superhero():
    keys = load_api_keys()
    token = keys.get("superhero")
    if not token:
        return "API key missing", None

    character_id = random.randint(1, 731)
    try:
        response = requests.get(f"https://superheroapi.com/api/{token}/{character_id}/image", timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Superhero API error: {e}")
        return "Failed to fetch superhero", None

    data = response.json()
    if data.get("response") != "success":
        return "Superhero not found", None

    name = data["name"]
    image_url = data["url"].replace("\\", "")
    return name, image_url


class UserUploadsView(discord.ui.View):
    def __init__(self, interaction, entries, target: discord.User):
        super().__init__(timeout=60.0)
        self.entries = entries
        self.index = 0
        self.interaction = interaction
        self.target = target
    
    async def update_message(self):
        entry = self.entries[self.index]
        embed = discord.Embed(title=f"Uploads by {self.target.display_name}")
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
        self.message = None
    
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
        image_url = entry[1].get("image")
        if image_url and image_url.startswith("http"):
            embed.set_image(url=image_url)

        if self.message:
            await self.message.edit(embed=embed, view=self)
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction:discord.Interaction, button:discord.ui.Button):
        self.index = (self.index - 1) % len(self.sorted_data)
        await self.update_message()
    
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.sorted_data)
        await self.update_message()
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                embed = self.message.embeds[0]
                embed.set_footer(text="⏱️ This leaderboard has timed out.")
                await self.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"LeaderboardView timeout error: {e}")

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
        super().__init__(
            placeholder="Choose your category. . .", 
            options=options,
            min_values=1,
            max_values=len(options)
            )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your menu!", ephemeral=True)
        
        category = self.values[0]
        await self.bot.get_cog("SmashOrPass").config.member(interaction.user).category.set(self.values)

        await interaction.response.send_message(f"Categories set to **{', '.join(self.values)}**!", ephemeral=True)

class CategoryView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=30)
        self.add_item(CategorySelect(bot, user_id))

class SmashPassView(discord.ui.View):
    def __init__(self, cog, character_name, category, image, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.character_name = character_name
        self.ctx = ctx
        self.image = image
        self.category = category
        self.message = None
        self.user_id = ctx.author.id
    
    @discord.ui.button(label="Super-Smash", style=discord.ButtonStyle.primary, emoji="💖")
    async def super_smash_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vote_bool = await self.cog.update_votes(self.category, self.character_name, "super-smashes", interaction.user.id, self.image)
        if vote_bool:
            await interaction.response.send_message(
                f"{interaction.user.mention} has used their daily **Super-Smash** on {self.character_name}! 💖\n"
                "Now that's special!"
            )
        else:
            super_time = self.cog.daily_super_smash.get(interaction.user.id)
            now = datetime.now(timezone.utc)
            difference = (super_time + timedelta(days=1)) - now
            hours, remainder = divmod(difference.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(
                "💔 You can only use your Super-Smash once per day!\n"
                f"The next time it will be available is in **{int(hours)}h {int(minutes)}m**."
            )

    @discord.ui.button(label="Smash", style=discord.ButtonStyle.green, emoji="🔥")
    async def smash_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.update_votes(self.category, self.character_name, "smashes", interaction.user.id, self.image)
        await interaction.response.send_message(
            f"{interaction.user.mention} chose **Smash** for {self.character_name}! 🔥",
            ephemeral=False,
        )

    @discord.ui.button(label="Pass", style=discord.ButtonStyle.red, emoji="❌")
    async def pass_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.update_votes(self.category, self.character_name, "passes", interaction.user.id, self.image)
        await interaction.response.send_message(
            f"{interaction.user.mention} chose **Pass** for {self.character_name}! ❌",
            ephemeral=False,
        )

    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.gray, emoji="🚫")
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can only blacklist characters on **your own post**.", ephemeral=True)
            return

        success = add_to_user_blacklist(interaction.user.id, self.category, self.character_name)
        if success:
            await interaction.response.send_message(f"🚫 {self.character_name} has been blacklisted. They won't appear again for you in {self.category}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{self.character_name} is **already** blacklisted for you.", ephemeral=True)


    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                embed = self.message.embeds[0]
                embed.set_footer(text="⏱️ This interaction has timed out.")
                await self.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"SmashPassView timeout error: {e}")


class SmashOrPass(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9237492836492)
        self.config.register_member(
            category=["All"]
        )
        self.daily_super_smash = {}
    
    sop = app_commands.Group(name="sop", description="Smash or Pass commands.")

    async def update_votes(self, category, character_name, vote_type, user_id, image):
        """Update smash/pass/super-smash count and prevent duplicate votes."""
        votes = load_votes()

        if category not in votes:
            votes[category] = {}

        if character_name not in votes[category]:
            votes[category][character_name] = {
                "smashes": 0,
                "passes": 0,
                "super-smashes": 0,
                "voters": [],
                "super-smashers": [],
                "image": ""
            }

        # Ensure all expected keys exist in case it's an old record
        char_data = votes[category][character_name]
        char_data.setdefault("smashes", 0)
        char_data.setdefault("passes", 0)
        char_data.setdefault("super-smashes", 0)
        char_data.setdefault("voters", [])
        char_data.setdefault("super-smashers", [])
        char_data.setdefault("image", "")

        if vote_type == "super-smashes":
            last_time = self.daily_super_smash.get(user_id)
            now = datetime.now(timezone.utc)
            if last_time and (now - last_time < timedelta(days=1)):
                return False  # Already used super smash today

            self.daily_super_smash[user_id] = now

            if user_id not in char_data["super-smashers"]:
                char_data["super-smashes"] += 1
                char_data["super-smashers"].append(user_id)

        else:
            if user_id in char_data["voters"]:
                return False  # Already smashed or passed

            char_data[vote_type] += 1
            char_data["voters"].append(user_id)

        char_data["image"] = image
        save_votes(votes)
        return True


    @sop.command(name="apikeyuplad", description="Upload or update an API key.")
    @app_commands.describe(api="Which API this is for", key="The Actual API key")
    @app_commands.choices(api=[
        app_commands.Choice(name="Superhero", value="superhero"),
        app_commands.Choice(name="tmdb", value="tmdb"),
        app_commands.Choice(name="LastFM", value="lastfm")
    ])
    async def apikeyupload(self, interaction: discord.Interaction, api: str, key:str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an **admin** to set API keys.", ephemeral=True)
            return

        if api.lower() not in VALID_APIS:
            await interaction.response.send_message(f"❌ Invalid API name. Must be one of: {', '.join(VALID_APIS)}", ephemeral=True)
            return

        keys = load_api_keys()
        keys[api.lower()] = key
        save_api_keys(keys)

        await interaction.response.send_message(f"✅ API key for **{api}** has been saved.", ephemeral=True)
    
    @sop.command(name="appeal", description="Appeal a Smash or Pass blacklist")
    @app_commands.describe(reason="Explain why you should be unblacklisted")
    async def appeal(self, interaction: discord.Interaction, reason: str):
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
    
    @sop.command(name="list", description="View images uploaded by a specific user")
    @app_commands.describe(user="Select a user (leave blank to see your own images)")
    async def list(self, interaction: discord.Interaction, user: discord.User = None):
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
    
    @sop.command(name="leaderboard", description="View the Smash or Pass leaderboard!")
    @app_commands.choices(category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES])
    async def leaderboard(self, interaction: discord.Interaction, category: str=None):
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
            await interaction.followup.send("❌ No characters have been voted on yet!", ephemeral=True)
            return
        
        sorted_data = sorted(category_data.items(), key = lambda x: x[1].get("smashes", 0) - x[1].get("passes", 0), reverse=True)

        if category:
            view = LeaderboardView("Leader", interaction, sorted_data, category)
        else:
            view = LeaderboardView("Leader", interaction, sorted_data)

        view.message = await interaction.followup.send("📊 Loading leaderboard...", view=view)

        await view.update_message()
    
    @sop.command(name="loserboard", description="View the Smash or Pass loserboard!")
    @app_commands.choices(category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES])
    async def loserboard(self, interaction: discord.Interaction, category: str=None):
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

    
    
    
    @sop.command(name="upload", description="Upload a custom character for Smash or Pass.")
    @app_commands.describe(
        name="Enter the character's name",
        url="Enter an image URL (optional if attaching an image)",
        image="Upload an image file (optional if providing a URL)"
    )
    async def upload(self, interaction: discord.Interaction, name: str, url: str = None, image: discord.Attachment = None):
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
    
    @sop.command(name="delete", description="Remove an uploaded character (self or mod)")
    @app_commands.describe(
        name="Delete by character name (if you're a mod, this is optional if you're deleting all images uploaded by a user)",
        user="Delete all uploads by a user (mods only)",
        fulldelete="Delete all images by this user (only applies if user is provided)"
    )
    async def delete(self, interaction: discord.Interaction, name: str = None, user: discord.User = None, fulldelete: bool = False):
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
    
    @sop.command(name="blacklist", description="Blacklist/unblacklist a user from uploading images")
    @app_commands.describe(user="Select the user to blacklist/unblacklist")
    async def blacklist(self, interaction:discord.Interaction, user:discord.User):
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

    @commands.hybrid_command(name="smashorpass", aliases=["sop"], description="Smash or pass a random character.")
    async def smashorpass(self, ctx:commands.Context):
        """Generates an image with which a person can react smash or pass."""
        categories = await self.config.member(ctx.author).category()

        if isinstance(categories, str):
            categories = [categories]

        if not categories or "All" in categories:
            categories = CATEGORIES
        elif "Real People" in categories:
            categories = REAL_CATEGORIES
        
        category = random.choice(categories)
        
        user_id = ctx.author.id

        if category == "Star Wars":
            name, image = get_random_starwarscharacter(user_id=user_id)
        elif category == "Custom":
            name, image = get_random_custom(user_id=user_id)
        elif category == "Actors":
            name, image = get_random_actor(user_id=user_id)
        elif category == "Singers":
            name, image = get_random_singer(user_id=user_id)
        else:
            name, image = get_random_superhero()

        if not image or "Failed" in name or name is None:
            await ctx.send(f"Error fetching character from **{category}**. Try again or continue switching categories!")
            return
        
        embed = discord.Embed(title=f"Smash or Pass: {name}")
        if image and image.startswith("http"):
            embed.set_image(url=image)
        embed.set_footer(text=f"Would you rather smash or pass {name}?")

        view = SmashPassView(self, name, category, image=image, ctx=ctx)
        view.message = await ctx.send(embed=embed, view=view)

    
    @commands.command(name="sopsettings", aliases=["sops"])
    async def sopsettings(self, ctx:commands.Context):
        """Choose your Smash or Pass category using a dropdown menu."""
        view = CategoryView(self.bot, ctx.author.id)
        await ctx.send("Select your preferred category:", view=view)
    
    
