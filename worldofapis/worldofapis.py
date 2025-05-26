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

    
    def load_json(self) -> dict:
        if not os.path.exists(API_KEYS):
            return {}
        else:
            with open(API_KEYS, "r") as f:
                return json.load(f)
    
    def save_json(self) -> None:
        with open(API_KEYS, "w") as f:
            json.dump(self.api_keys, f, indent=4)
    

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
        await interaction.response.defer(thinking=True, ephemeral=True)

        api = self.api_keys.get("cat_api")
        if not api:
            return await interaction.followup.send("Please ask the admin to upload an API key.", ephemeral=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.thecatapi.com/v1/images/search?{'breed_ids=' + breed + '&' if breed else ''}api_key={api}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Unable to find a cat :(")
                cat_json = await resp.json()

                cat_dict = cat_json[0]  # Since theCatAPI returns a list

                embed = discord.Embed(title="Cat Profile", color=discord.Color.blurple())
                breeds_list = cat_dict.get("breeds")

                wiki_url = None

                if breeds_list:
                    for breed_info in breeds_list:
                        name = breed_info.get("name")
                        desc = breed_info.get("description")
                        wiki_url = breed_info.get("wikipedia_url")

                        if name:
                            embed.add_field(name="Breed", value=name)
                        if desc:
                            embed.add_field(name="Description", value=desc)

                embed.set_image(url=cat_dict.get("url"))
                embed.set_footer(text="Courtesy of TheCatAPI")

                view = CatView(wiki_url) if wiki_url else None
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)