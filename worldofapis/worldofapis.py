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
