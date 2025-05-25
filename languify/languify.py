import aiohttp
from redbot.core import commands, Config
import discord
from discord import app_commands
import random
import re
import os
import json

ACCEPTED_LANGUAGES = ["pirate", "old_english", "valley_girl"]
INSULTABLE_LANGUAGES = ["pirate"]
APIABLE_LANGUAGES = ["rapidapi_key"]


BASE_DIR = os.path.dirname(__file__)
SECRETS_FILE = os.path.join(BASE_DIR, "secrets.json")




class Languify(commands.Cog):
    """Translate to a variety of fun languages."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=829418329)
        self.config.register_user(language="")
        self.api_keys = self.load_secrets_file()
        self.save_secrets_file()
    
    def save_secrets_file(self):
        # Always save at least a valid empty JSON object
        if not os.path.exists(SECRETS_FILE):
            with open(SECRETS_FILE, "w") as f:
                json.dump({}, f, indent=4)
        else:
            with open(SECRETS_FILE, "w") as f:
                json.dump(self.api_keys or {}, f, indent=4)

        
        

    def load_secrets_file(self):
        if os.path.exists(SECRETS_FILE) and os.path.getsize(SECRETS_FILE) > 0:
            with open(SECRETS_FILE, "r") as f:
                return json.load(f)
        else:
            return {}


    async def piratify(self, message: str = None):
        if message == None:
            return "Ahoy matey! It seems ye fergot yer message! Ye can't be translating nothing."
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pirate.monkeyness.com/api/translate?english={message}") as resp:
                if resp.status != 200:
                    return "⚓ Cap'n the seas be stormy, and I couldn’t reach the galley."
                return await resp.text()
    
    async def pirate_insult(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pirate.monkeyness.com/api/insult") as resp:
                if resp.status != 200:
                    return "The bravest captains of the high seas could not even insult {person}."
                return await resp.text()
    
    def format_paragraph(self, text: str) -> str:
        pattern = r'([.!?])([a-z])'

        restored = re.sub(pattern, r'\1\n\n\2', text)

        return restored
    

    
    async def old_englishify(self, text: str) -> str:
        key = self.api_keys.get("rapidapi_key")

        if not key:
            return "Ye Olde English API key is missing. Hast thou forgotteth to upload it?"

        headers = {
            "x-rapidapi-key": key,
            "x-rapidapi-host": "shakespeare.p.rapidapi.com"
        }

        params = {"text": text}

        async with aiohttp.ClientSession() as session:
            async with session.get("https://shakespeare.p.rapidapi.com/shakespeare.json", headers=headers, params=params) as resp:
                if resp.status != 200:
                    return "Alack! Yon translation hath failed. Perhaps tryeth again later."
                
                try:
                    data = await resp.json()
                    return data.get("contents", {}).get("translated", "Nay, the response bore no fruit.")
                except Exception:
                    return "Forsooth! The scroll of knowledge returned no legible markings."


    async def valley_girlify(self, text:str) -> str:
        key = self.api_keys.get("rapidapi_key")

        if not key:
            return "You like forgot to upload your key. Like you gotta do that pronto."


        payload = {}
        headers = {
            "x-rapidapi-key": key,
            "x-rapidapi-host": "valspeak.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        params = {"text": text}

        async with aiohttp.ClientSession() as session:
            async with session.post("https://valspeak.p.rapidapi.com/valspeak.json", json=payload, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return "Like I know you like want the translation, but I like totally can't do it right now."
                
                try:
                    data = await resp.json()
                    return data.get("contents", {}).get("translated", "I'm like totally sooooo sorry, but I like couldn't get you your translation. My bad girlie.")
                except Exception:
                    return "Whoops. I like totally spilled my morning latte all over the translation panel."

    
    languify = app_commands.Group(name="languify", description="Fun language commands for all your fun language needs.")

    @languify.command(name="apis", description="Upload an api key for languify.")
    @app_commands.describe(language="The API you want the key for.")
    @app_commands.choices(language=[
        app_commands.Choice(name="RapidAPI", value="rapidapi_key")
    ])
    async def apis(self, interaction:discord.Interaction, language:str, api_key:str):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You have to be an administrator to use this command.", ephemeral=True)
        
        if language not in APIABLE_LANGUAGES:
            return await interaction.response.send_message("That language is not one of the API-able languages.", ephemeral=True)
        
        self.api_keys.setdefault(language, "")
        self.api_keys[language] = api_key
        self.save_secrets_file()
        await interaction.response.send_message(f"API key for {language} is properly set.", ephemeral=True)

    
    @languify.command(name="languageset", description="Choose the language to translate to.")
    @app_commands.describe(language="The language to translate to.")
    @app_commands.choices(language=[
        app_commands.Choice(name="Pirate", value="pirate"),
        app_commands.Choice(name="Old English", value="old_english"),
        app_commands.Choice(name="Valley Girl", value="valley_girl"),
        app_commands.Choice(name="Random", value="random")
    ])
    async def languageset(self, interaction:discord.Interaction, language: str):
        
        if language not in ACCEPTED_LANGUAGES and language != "random":
            await interaction.response.send_message(f"Please choose from the currently available languages: {', '.join(ACCEPTED_LANGUAGES)}", ephemeral=True)
            return
    

        try:
            await self.config.user(interaction.user).language.set(language)

            await interaction.response.send_message(f"`{language.title()}` has officially been set as your new language! Use command `[p]funtranslate` or `[p]ft` to get started using it!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occured: {e}. Please report it.", ephemeral=True)
    
    
        
    
    @commands.command(aliases=["ft"])
    async def funtranslate(self, ctx:commands.Context, *, message:str=None):
        """Translate into a funny language."""

        if message is None and ctx.message.reference:
            try:
                ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                message = ref.content
            except Exception:
                message = None

        language = await self.config.user(ctx.author).language()
        
        if language == None or language == "random":
            language = random.choice(ACCEPTED_LANGUAGES)

        if language == "pirate":
            translated = await self.piratify(message=message)
            translated = self.format_paragraph(translated)
        elif language == "old_english":
            translated = await self.old_englishify(message)
        elif language == "valley_girl":
            translated = await self.valley_girlify(message)
        
        await ctx.send(translated)
    
    @commands.command(aliases=["fi"])
    async def funinsult(self, ctx:commands.Context, *, taggee:discord.Member=None):
        """Do an insult from a funny language."""

        if not taggee and ctx.message.reference:
            try:
                message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                taggee = message.author
            except Exception:
                return await ctx.send("You can't just be insulting no one.")
        
        if not taggee:
            taggee = ctx.author

        language = await self.config.user(ctx.author).language()

        if not language or language not in INSULTABLE_LANGUAGES:
            language = random.choice(INSULTABLE_LANGUAGES)
        
        if language == "pirate":
            insult = await self.pirate_insult()
        
        try:
            await ctx.send(insult.format(person=taggee.mention))
        except KeyError:
            await ctx.send(f"{taggee.mention}, {insult}")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
