import discord
from discord.ext import commands, app_commands, tasks
import random
import asyncio
import json
import os

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