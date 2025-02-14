
import discord
from discord.ext import commands
from redbot.core.bot import Red
from discord import app_commands
from redbot.core import commands, Config
import os
import json
import random
import asyncio

TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "templates.json")

def open_json(file_path):
    if not os.path.exists(file_path):
        print("Bad error. Please report it.")
        return {}
    
    with open(file_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            print("Error opening file.")
            return {}

def get_stories():
    titles = []
    story_dict = open_json(TEMPLATES_FILE)
    templates = story_dict.get("templates")
    for template in templates:
        title = template.get("title", "Unknown")
        print(f"DEBUG: `{title}` ({len(title)} chars)")
        titles.append(discord.SelectOption(label=template.get("title")))
    
    return titles

def get_template(title):
    story_dict = open_json(TEMPLATES_FILE)
    templates = story_dict.get("templates")
    for template in templates:
        if template.get("title") == title:
            return template.get("template")
        else:
            print("An error occurred finding that template.")
            return None

class StorySelect(discord.ui.Select):
    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id

        options = get_stories()

        options.append(discord.SelectOption(label="Random"))

        super().__init__(placeholder="Choose a story. . .", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This isn't your command! Please run your own!", ephemeral=True)
        
        story = self.values[0]
        while story == "Random":
            story = random.choice(self.options).label
            
        await self.bot.get_cog("MadLibs").config.member(interaction.user).story.set(story)
        await self.bot.get_cog("MadLibs").config.member(interaction.user).started.set(False)
        await interaction.response.send_message(f"You have selected a story! Run `[p]madlibs start` to do madlibs with it!", ephemeral=True)



class StoryListView(discord.ui.View):
    def __init__(self, bot, user_id, timeout=180.0):
        super().__init__(timeout=timeout)
        self.add_item(StorySelect(bot, user_id))


class MadLibs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=21839172123)
        self.config.register_member(
            story = "None",
            started = False
        )
    
    @commands.group(name="madlib", aliases=["ml"], invoke_without_command=True)
    async def madlib(self, ctx: commands.Context):
        """MadLib Parent Class"""
        await ctx.send("Please run `[p]madlib storyselect` first to select a story and then `[p]madlib start`.")
    
    @madlib.command(name="storyselect", aliases=["ss"])
    async def madlib_storyselect(self, ctx:commands.Context):
        """Pick from a list of stories for madlibs."""
        view = StoryListView(bot=self.bot, user_id=ctx.author.id)
        await ctx.send("Select a story:", view=view)
    
    @madlib.command(name="start", aliases=["s"])
    async def madlib_start(self, ctx:commands.Context):
        story_title = await self.config.member(ctx.author).story()
        started = await self.config.member(ctx.author).started()

        if story_title == "None":
            await ctx.send("Please use `[p]madlibs storyselect` to select a story first!")

        if started:
            await ctx.send("It looks like maybe you already did this story. Did you want to do it again? `Yes` or `No`")
            def check(message): return message.author == ctx.author and message.content.lower() in ['yes', 'no']
            try:
                message = await self.bot.wait_for("message", timeout=30, check=check)
                if message.content.lower() == "no":
                    return
            except asyncio.TimeoutError:
                await ctx.send("The command has timed out.")
                return
            
        await self.config.member(ctx.author).started.set(True)

        template = get_template(story_title)


        