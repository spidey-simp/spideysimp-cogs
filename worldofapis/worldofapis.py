from redbot.core import commands
import discord
import aiohttp
import json
import os
from discord import app_commands

BASE_DIR = os.path.dirname(__file__)

API_KEYS = os.path.join(BASE_DIR, "api_keys.json")

CURRENT_API_LIST = ["cat_api"]

cat_breed_list = ["abys", "aege", "abob", "acur", "asho", "awir", "amau", "amis", "bali",
                  "bamb", "beng", "birm", "bomb", "bslo", "bsho", "bure", "buri", "cspa",
                  "ctif", "char", "chau", "chee", "csho", "crex", "cymr", "cypr", "drex",
                  "dons", "lihu", "emau", "ebur", "esho", "hbro", "hima", "jbob", "java",
                  "khao", "kora", "kuri", "lape", "mcoo", "mala", "manx", "munc", "nebe",
                  "norw", "ocic", "orie", "pers", "pixi", "raga", "ragd", "rblu", "sava",
                  "sfol", "srex", "siam", "sibe", "sing", "snow", "soma", "sphy", "tonk",
                  "toyg", "tang", "tvan", "ycho"
                  ]

class CatLinkButton(discord.ui.Button):
    def __init__(self, wiki_url: str):
        super().__init__(label="Wikipedia", style=discord.ButtonStyle.link, url=wiki_url)

class CatView(discord.ui.View):
    def __init__(self, wiki_url: str):
        super().__init__()
        self.add_item(CatLinkButton(wiki_url))

class WorldOfApis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.api_keys = self.load_json()
        self.breed_dict = {}

    
    def load_json(self) -> dict:
        if not os.path.exists(API_KEYS):
            return {}
        else:
            with open(API_KEYS, "r") as f:
                return json.load(f)
    
    def save_json(self) -> None:
        with open(API_KEYS, "w") as f:
            json.dump(self.api_keys, f, indent=4)
    
    async def load_dog_breeds(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thedogapi.com/v1/breeds") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Create dict: name -> id
                    self.breed_dict = {str(breed["id"]): breed["name"] for breed in data}  # ID → Name

                    # For autocomplete
                    self.autocomplete_list = [
                        app_commands.Choice(name=breed["name"], value=str(breed["id"])) for breed in data
                    ]
                else:
                    self.breed_dict = {}
                    self.autocomplete_list = []
    

    woa = app_commands.Group(name="woa", description="World of Apis commands")

    @woa.command(name="add_api_key", description="Add an api key for WOA.")
    @app_commands.describe(api="The program for the api key.", key="The api key itself.")
    @app_commands.choices(api=[
        app_commands.Choice(name="TheCatAPI", value="cat_api")
    ])
    async def add_api_key(self, interaction:discord.Interaction, api:str, key:str):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to edit api keys.", ephemeral=True)
        
        if api not in CURRENT_API_LIST:
            return await interaction.response.send_message("That API is not currently supported.")
        
        self.api_keys.setdefault(api, "")
        self.api_keys[api] = key
        self.save_json()
        await interaction.response.send_message(f"The api key for {api} has successfully been uploaded.", ephemeral=True)
    
    async def cat_breed_autocomplete(self, interaction:discord.Interaction, current: str):
        return [
            app_commands.Choice(name=breed, value=breed)
            for breed in cat_breed_list if current.lower() in breed.lower()
        ][:25]

    @woa.command(name="cat", description="See a cat with its facts.")
    @app_commands.describe(breed="The breed of cat you want to see.")
    @app_commands.autocomplete(breed=cat_breed_autocomplete)
    async def cat(self, interaction:discord.Interaction, breed: str=None):
        await interaction.response.defer(thinking=True)

        api = self.api_keys.get("cat_api")
        if not api:
            return await interaction.followup.send("Please ask the admin to upload an API key.", ephemeral=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.thecatapi.com/v1/images/search?{'breed_ids=' + breed + '&' if breed else ''}api_key={api}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Unable to find a cat :(")
                cat_json = await resp.json()

                cat_dict = cat_json[0]
                embed = discord.Embed(title="Cat Profile", color=discord.Color.blurple())
                embed.set_image(url=cat_dict.get("url"))
                embed.set_footer(text="Courtesy of TheCatAPI")

                breeds_list = cat_dict.get("breeds")
                if breeds_list:
                    breed_info = breeds_list[0]
                    name = breed_info.get("name")
                    desc = breed_info.get("description")
                    wiki_url = breed_info.get("wikipedia_url")

                    if name:
                        embed.title = f"{name} – Cat Profile"
                    if desc:
                        embed.add_field(name="📝 Description", value=desc, inline=False)
                    
                    temperament = breed_info.get("temperament")
                    if temperament:
                        embed.add_field(name="😺 Temperament", value=temperament, inline=False)

                    traits = {
                        "Affection": breed_info.get("affection_level"),
                        "Energy": breed_info.get("energy_level"),
                        "Intelligence": breed_info.get("intelligence"),
                        "Dog Friendly": breed_info.get("dog_friendly"),
                        "Child Friendly": breed_info.get("child_friendly"),
                        "Shedding": breed_info.get("shedding_level"),
                        "Grooming Needs": breed_info.get("grooming"),
                        "Health Issues": breed_info.get("health_issues"),
                        "Vocalization": breed_info.get("vocalisation"),
                    }
                    trait_lines = [
                        f"• **{k}**: {'⭐' * v}" for k, v in traits.items() if isinstance(v, int)
                    ]
                    if trait_lines:
                        embed.add_field(name="📊 Traits", value="\n".join(trait_lines), inline=False)

                    origin = breed_info.get("origin")
                    life_span = breed_info.get("life_span")
                    hypoallergenic = "Yes" if breed_info.get("hypoallergenic") else "No"
                    weight = breed_info.get("weight", {}).get("imperial")

                    details = []
                    if origin: details.append(f"• **Origin**: {origin}")
                    if life_span: details.append(f"• **Life Span**: {life_span} years")
                    if weight: details.append(f"• **Weight**: {weight} lbs")
                    details.append(f"• **Hypoallergenic**: {hypoallergenic}")

                    if details:
                        embed.add_field(name="📦 Additional Info", value="\n".join(details), inline=False)


                if wiki_url:
                    view = CatView(wiki_url)
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send(embed=embed)
    
    
    async def dog_breed_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            choice for choice in self.autocomplete_list if current.lower() in choice.name.lower()
        ][:25]

    @woa.command(name="dog", description="See a dog with its facts.")
    @app_commands.describe(breed="The breed of dog you want to see.")
    @app_commands.autocomplete(breed=dog_breed_autocomplete)
    async def dog(self, interaction: discord.Interaction, breed: str = None):
        await interaction.response.defer(thinking=True, ephemeral=False)

        api = self.api_keys.get("cat_api")
        if not api:
            return await interaction.followup.send("Please ask the admin to upload an API key.", ephemeral=True)

        base_url = "https://api.thedogapi.com/v1/images/search"
        breed_id_param = ""
        if breed:
            if not hasattr(self, "breed_dict") or not self.breed_dict:
                return await interaction.followup.send(
                    "🐕 Woah there! I want to look at dogs just as much as you! "
                    "Ask an admin to run `/woa initialize_dog`, or run this command without a breed for now.",
                    ephemeral=True
                )
            if breed not in self.breed_dict:
                return await interaction.followup.send("Breed not recognized. Please try again.", ephemeral=True)
            breed_id_param = f"&breed_ids={breed}"

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}?api_key={api}{breed_id_param}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Failed to fetch a dog image.")
                data = await resp.json()
                dog_dict = data[0]
                image_id = dog_dict.get("id")

            if not breed:
                # No breed = no metadata. Just send image.
                embed = discord.Embed(title="Here's a random dog!", color=discord.Color.orange())
                embed.set_image(url=dog_dict.get("url"))
                return await interaction.followup.send(embed=embed)

            # Otherwise: Get full breed info via image ID
            async with session.get(f"https://api.thedogapi.com/v1/images/{image_id}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Failed to fetch dog metadata.")
                dog_meta = await resp.json()

        embed = discord.Embed(title="Dog Profile 🐾", color=discord.Color.orange())
        embed.set_image(url=dog_meta.get("url"))

        breeds_list = dog_meta.get("breeds")
        if breeds_list:
            breed_info = breeds_list[0]
            embed.add_field(name="Breed", value=breed_info.get("name", "Unknown"))

            if bred := breed_info.get("bred_for"):
                embed.add_field(name="Bred For", value=bred, inline=False)
            if group := breed_info.get("breed_group"):
                embed.add_field(name="Group", value=group, inline=True)
            if life := breed_info.get("life_span"):
                embed.add_field(name="Life Span", value=life, inline=True)
            if temper := breed_info.get("temperament"):
                embed.add_field(name="Temperament", value=temper, inline=False)
            if origin := breed_info.get("origin"):
                embed.set_footer(text=f"Origin: {origin}")

        await interaction.followup.send(embed=embed)

    @woa.command(name="initialize_dog", description="Initializes or refreshes the dog breed list.")
    async def initialize_dog(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to initialize dog data.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.load_dog_breeds()
        await interaction.followup.send("Dog breeds have been initialized and are ready to go! 🐶", ephemeral=True)
