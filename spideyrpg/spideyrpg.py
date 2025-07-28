import discord
from discord.ext import tasks
import random
import asyncio
import json
import os
from discord import app_commands
from redbot.core import Config, commands

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RPG_SAVE_FILE = os.path.join(BASE_DIR, 'rpg_save.json')
RPG_PRESET_FILE = os.path.join(BASE_DIR, 'preset_characters.json')

def load_file(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        return json.load(f)

def save_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

class CharacterCreationModal(discord.ui.Modal, title="Create Your Character"):
    def __init__(self, bot, presets, ctx):
        super().__init__()
        self.bot = bot
        self.presets = presets
        self.ctx = ctx  # store for access later

        self.name = discord.ui.TextInput(
            label="Character Name",
            placeholder="Enter your character's name",
            required=True,
            max_length=32
        )
        self.gender = discord.ui.TextInput(
            label="Gender",
            placeholder="Enter your character's gender (M, F, or O).",
            required=True,
            max_length=1
        )
        self.char_class = discord.ui.TextInput(
            label="Class",
            placeholder="Must match one of the preset classes (currently: rogue)",
            required=True,
            max_length=32
        )
        self.description = discord.ui.TextInput(
            label="Character Description",
            placeholder="Describe your character (optional)",
            required=False,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.image_url = discord.ui.TextInput(
            label="Image URL (optional)",
            placeholder="Paste an image link (optional). Must have a .png, .jpg, or .jpeg extension.",
            required=False,
            max_length=500
        )

        self.add_item(self.name)
        self.add_item(self.gender)
        self.add_item(self.char_class)
        self.add_item(self.description)
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in self.bot.get_cog("SpideyRPG").rpg_data:
            await interaction.response.send_message("You already have a character.", ephemeral=True)
            return

        class_name = self.char_class.value.strip().lower()
        if class_name not in self.presets.get("classes", {}):
            await interaction.response.send_message(f"Invalid class: {class_name}. Please use an existing class.", ephemeral=True)
            return

        # Save character data
        char_data = {
            "name": self.name.value.strip(),
            "gender": self.gender.value.strip(),
            "class": class_name,
            "description": self.description.value.strip() or None,
            "level": 1,
            "stats": self.presets["classes"][class_name].get("stats", {}),
            "abilities": self.presets["classes"][class_name].get("abilities", []),
            "weapons": self.presets["classes"][class_name].get("weapons", []),
            "inventory": self.presets["classes"][class_name].get("equipment", []),
            "passive_abilities": self.presets["classes"][class_name].get("passive_abilities", []),
            "image_url": self.image_url.value.strip() or self.presets["classes"][class_name].get("default_image", None),
        }

        self.bot.get_cog("SpideyRPG").rpg_data[user_id] = char_data
        save_file(RPG_SAVE_FILE, self.bot.get_cog("SpideyRPG").rpg_data)

        await interaction.response.send_message(f"Character **{char_data['name']}** the **{class_name.capitalize()}** created!", ephemeral=True)



class SpideyRPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rpg_data = load_file(RPG_SAVE_FILE)
        self.presets = load_file(RPG_PRESET_FILE)

    @tasks.loop(count=1)
    async def delayed_check(self):
        await self.bot.wait_until_ready()
        report = self.validate_presets()
        # Replace this with a known channel ID or log destination
        channel = self.bot.get_channel(1301307287071232051)
        if channel:
            await channel.send(report)

    def cog_unload(self):
        save_file(RPG_SAVE_FILE, self.rpg_data)

    
    @commands.command(name="checkpresets")
    @commands.is_owner()
    async def check_presets_command(self, ctx: commands.Context):
        """Check for undefined weapons, armor, or abilities in the preset character data."""
        report = self.validate_presets()
        await ctx.send(report)

    def validate_presets(self):
        classes = self.presets.get("classes", {})
        defined_weapons = set()
        defined_equipment = set()
        defined_abilities = set()

        # Gather defined assets
        for category in self.presets.get("weapons", {}).values():
            defined_weapons.update(category.keys())
        for slot in self.presets.get("equipment", {}).values():
            defined_equipment.update(slot.keys())
        if "abilities" in self.presets:
            defined_abilities.update(self.presets["abilities"].keys())

        missing = {
            "Weapons": set(),
            "Armor": set(),
            "Abilities": set(),
            "Passives": set()
        }

        for cname, cdata in classes.items():
            for weapon in cdata.get("weapons", []):
                if weapon not in defined_weapons:
                    missing["Weapons"].add(f"{weapon} (used by {cname})")
            for armor in cdata.get("armor", []):
                if armor not in defined_equipment:
                    missing["Armor"].add(f"{armor} (used by {cname})")
            for ability in cdata.get("abilities", []):
                if ability not in defined_abilities:
                    missing["Abilities"].add(f"{ability} (used by {cname})")
            for passive in cdata.get("passive_abilities", []):
                if passive not in defined_abilities:
                    missing["Passives"].add(f"{passive} (used by {cname})")

        # Build report
        report = "**Preset Validation Report:**\n"
        all_empty = True
        for category, items in missing.items():
            if items:
                all_empty = False
                report += f"\n**Missing {category}:**"
                for item in sorted(items):
                    report += f"\n- {item}"

        if all_empty:
            report = "✅ All RPG items are currently defined! Great job!"

        return report
    
    @commands.group(name="spidey_rpg", aliases=["srpg"])
    async def spidey_rpg(self, ctx: commands.Context):
        """RPG commands group."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand.")
    
    rpg = app_commands.Group(name="rpg", description="RPG commands")

    @rpg.command(name="create_character", description="Create a character using a modal form.")
    async def create_character(self, interaction: discord.Interaction):
        """Create a character using a modal form."""
        modal = CharacterCreationModal(self.bot, self.presets, interaction)
        await interaction.response.send_modal(modal)

    @rpg.command(name="view_character", description="View your or another user's RPG character.")
    async def view_character(self, interaction: discord.Interaction, user: discord.User = None):
        if user is None:
            user = interaction.user

        character = self.rpg_data.get(str(user.id))
        if not character:
            await interaction.response.send_message(f"{user.name} does not have a character.")
            return
        
        embed = discord.Embed(title=f"{user.name}'s Character", color=discord.Color.blue())
        embed.add_field(name="Name", value=f"{character.get('name', 'Unknown')} the {character.get('class', 'Unknown')}", inline=True)
        embed.add_field(name="Gender", value=character.get("gender", "Unknown"), inline=True)
        embed.add_field(name="Description", value=character.get("description", "No description provided"), inline=False)
        embed.add_field(name="Level", value=character.get("level", 1), inline=True)
        embed.add_field(name="Experience", value=character.get("experience", 0), inline=True)
        for stat, value in character.get("stats", {}).items():
            embed.add_field(name=stat.capitalize(), value=str(value), inline=True)
        image = character.get("image_url")
        if image:
            embed.set_image(url=image)
        await interaction.followup.send(embed=embed)
    
    @spidey_rpg.command(name="delete_character", aliases=["dc"])
    async def delete_character(self, ctx: commands.Context):
        """Delete your RPG character."""
        user_id = str(ctx.author.id)
        if user_id in self.rpg_data:
            await ctx.send(f"Are you sure you want to delete your character, {ctx.author.name}? This action cannot be undone. Type 'yes' to confirm.")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
            try:
                message = await self.bot.wait_for('message', check=check, timeout=30.0)
                if message.content.lower() == 'yes':
                    del self.rpg_data[user_id]
                    save_file(RPG_SAVE_FILE, self.rpg_data)
                    await ctx.send("Your character has been deleted.")
                else:
                    await ctx.send("Character deletion canceled.")
                    return
            except asyncio.TimeoutError:
                await ctx.send("Character deletion canceled.")
                return
        else:
            await ctx.send("You do not have a character to delete.")