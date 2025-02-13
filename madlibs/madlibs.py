
import discord
from discord.ext import commands
from redbot.core.bot import Red
from discord import app_commands
from redbot.core import commands, Config
import os
import json
import random

TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "templates.json")

def open_json():
    if not os.path.exists(TEMPLATES_FILE):
        print("Bad error. Please report it.")
        return {}
    
    with open(TEMPLATES_FILE, "r", "utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            print("Error opening file.")
            return {}

def get_stories():
    titles = []
    story_dict = open_json(TEMPLATES_FILE)
    templates = story_dict.get("templates")
    for i in len(templates):
        titles.append(discord.SelectOption(label=templates[i].get("title")))
    
    return titles

class StorySelect(discord.ui.Select):
    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id

        self.options = get_stories()

        self.options.append(discord.SelectOption(label="Random"))

        super().__init__(placeholder="Choose a story. . .", options=self.options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your command! Please run your own!", ephemeral=True)
        
        story = self.values[0]
        while story == "Random":
            story = random.choice(self.options)
            
        await self.bot.get_cog("MadLibs").config.member(interaction.user).story.set(story)
        await interaction.response.send_message(f"You have selected a story! Run `[p]madlibs start` to do madlibs with it!", ephemeral=True)



class StoryListView(discord.ui.View):
    def __init__(self, bot, user_id, timeout=180.0):
        super().__init__(timeout=timeout)
        self.add_item(StorySelect(bot, user_id))


class MadLibs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=21839172123)
        self.config.register_member(story = "None")
    
    @commands.group(name="madlib", aliases=["ml"], invoke_without_command=True)
    async def madlib(self, ctx: commands.Context):
        """MadLib Parent Class"""
        await ctx.send("Please run `[p]madlib storyselect` first to select a story and then `[p]madlib start`.")
    
    @madlib.command(name="storyselect", aliases=["ss"])
    async def madlib_storyselect(self, ctx:commands.Context):
        """Pick from a list of stories for madlibs."""
        view = StoryListView(bot=self.bot, user_id=ctx.author)
        await ctx.send("Select a story:", view=view)