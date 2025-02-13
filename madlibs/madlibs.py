
import discord
from discord.ext import commands
from redbot.core.bot import Red
from discord import app_commands
from redbot.core import commands, Config
import os
import json

TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "templates.json")

class MadLibs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=21839172123)
        