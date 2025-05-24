import aiohttp
from redbot.core import commands, Config
import discord
from discord import app_commands
import random

ACCEPTED_LANGUAGES = ["pirate"]
INSULTABLE_LANGUAGES = ["pirate"]

class Languify(commands.Cog):
    """Translate to a variety of fun languages."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=829418329)
        self.config.register_user(language="")
    

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
    
    languify = app_commands.Group(name="languify", description="Fun language commands for all your fun language needs.")
    
    @languify.command(name="languageset", description="Choose the language to translate to.")
    @app_commands.describe(language="The language to translate to.")
    @app_commands.choices(language=[
        app_commands.Choice(name="Pirate", value="pirate")
    ])
    async def languageset(self, interaction:discord.Interaction, language: str):
        
        if language not in ACCEPTED_LANGUAGES:
            await interaction.response.send_message(f"Please choose from the currently available languages: {', '.join(ACCEPTED_LANGUAGES)}")
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
        
        language = language or random.choice(ACCEPTED_LANGUAGES)

        if language == "pirate":
            translated = await self.piratify(message=message)
        
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
