import random
import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands, Config

class WhoAmI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=120983423)
        self.config.register_user(stats={})

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.user:
            return
        try:
            await self.bot.tree.sync()
            print("Slash commands synced successfully!")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    @app_commands.command(name="stats", description="Get your random RPG stats!")
    async def stats(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_stats = await self.config.user(interaction.user).stats()

        if not user_stats:
            user_stats = {stat: random.randint(1, 10) for stat in ["Strength", "Dexterity", "Speed", "Charisma", "Intelligence", "Luck", "Endurance", "Wisdom"]}
            await self.config.user(interaction.user).stats.set(user_stats)

        embed = discord.Embed(title=f"{interaction.user.display_name}'s Stats", color=discord.Color.blue())

        def format_stat(value):
            if value >= 8:
                return f"🟢 **{value}**"
            elif 4 <= value <= 7:
                return f"🟡 **{value}**"
            else:
                return f"🔴 **{value}**"
        
        for stat, value in user_stats.items():
            embed.add_field(name=stat, value=format_stat(value), inline=True)
        
        await interaction.response.send_message(embed=embed)