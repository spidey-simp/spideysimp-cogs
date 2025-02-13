
import discord
from discord.ext import commands
from redbot.core.bot import Red
from discord import app_commands
from redbot.core import commands, Config
import os
import json

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

        options = get_stories()

        super().__init__(placeholder="Choose a story. . .", options=options)
        


class StoryListView(discord.ui.View):
    def __init__(self, *, timeout = 180, bot, user_id):
        super().__init__(timeout=timeout)


class MadLibs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=21839172123)
    
    @commands.command(name="madlib", aliases=["ml"])
    async def madlib(self, ctx: commands.Context):
        """Generate a madlib."""
