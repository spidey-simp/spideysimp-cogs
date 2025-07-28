import discord
import random
from redbot.core import Config
import json
import os
from discord.ext import app_commands, commands

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PROMPTS = {
    "greet": ["hey", "sup", "yo", "hi", "hello", "howdy"],
    "farewell": ["bye", "goodbye", "see you", "take care", "later"],
    "news": ["i'm bored", "i approve"],
}

RESPONSES = {
    "news": {
        "lead": ["BREAKING NEWS:", "EXCLUSIVE REPORT:", "SPIDEY SAYS:"],
    },
    "chaos": [
        "You really think you're something, huh kid?",
        "MJ and I are just friends, nothing more.",
        "MJ told me to tell you to stop bothering her.",
        "I don't have time for your nonsense, I'm a busy superhero.",
        "You think you're funny? I've seen better jokes in a kindergarten class.",
        "You're the reason I wish I could just stick to fighting villains.",
        "If I had a dollar for every time someone asked me to do their homework, I'd be rich.",
        "Have you ever tried sticking to the wall? It's not as easy as it looks.",
        "Delmar's Deli has the best sandwiches in town, but you wouldn't know that because you're too busy bothering me.",
        "F.R.I.D.A.Y., save a reminder for me to deal with this later.",
        "And I thought Gobby was bonkers.",
        "My friend Harry has a better sense of humor than you.",
        "E.D.I.T.H. says I need to spend my time in better ways than talking to you.",
        "I'd pick the Sinister Six over six more minutes of you.",
        "J. Jonah is nicer than you, and that's saying something.",
        "Picture for the Daily Bugle?",
        "Should I perch on the Empire State Building or Chrysler Building?"
    ],
    "quotes": {
        "power": "With great power comes great responsibility.",
        "pizza": "Pizza time!",
        "sense": "My spider-sense is tingling.",
        "dirt": "I'm gonna put some dirt in your eye.",
        "friendly": "I'm just your friendly neighborhood Spider-Man.",

    }
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)
    
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

class ResponseTypeSelect(discord.ui.Select):
    def __init__(self, current_types):
        options = [
            discord.SelectOption(label="Greet", value="greet", description="Simple greetings", default="greet" in current_types),
            discord.SelectOption(label="Farewell", value="farewell", description="Goodbye messages", default="farewell" in current_types),
            discord.SelectOption(label="News", value="news", description="Spidey snarky responses in news style", default="news" in current_types),
            discord.SelectOption(label="Chaos", value="chaos", description="Random chaos responses", default="chaos" in current_types),
            discord.SelectOption(label="Quotes", value="quotes", description="Quotes from Spider-Man movies", default="quotes" in current_types)
        ]
        super().__init__(placeholder="Select response types...", options=options, max_values=5, min_values=0)
    
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        settings = load_settings()
        settings[user_id]  = self.values
        save_settings(settings)
        await interaction.response.send_message(f"🕸️ SpideyBot will now only respond to: `{', '.join(self.values)}`", ephemeral=True)

class ResponseTypeView(discord.ui.View):
    def __init__(self, current_types):
        super().__init__()
        self.add_item(ResponseTypeSelect(current_types))

class SpideyResponds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config.register_guild(
            responses_enabled=["greet", "farewell", "news", "chaos", "quotes"]
        )

    @commands.slash_command(name="response_settings", description="Configure SpideyBot's response types to you.")
    async def response_settings(self, ctx: discord.ApplicationContext):
        user_id = str(ctx.author.id)
        settings = load_settings()
        current = settings.get(user_id, ["greet", "farewell", "news", "chaos", "quotes"])
        await ctx.response.send_message("Select the responses you want from SpideyBot:", view=ResponseTypeView(current), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        if not message.guild:
            return
        
        id = str(message.author.id)


        if message.content.lower() in PROMPTS["greet"]:
            response = await self.greet(message.content.lower(), id)

        

        


    
    async def greet(self, text, id):
        return f"{text.title()}, @<{id}>! Friendly neighborhood SpideyBot here! 🕷️"
