import asyncio
import random
import discord
import aiohttp
from typing import List
from discord import Member
from discord.ext import commands
from redbot.core import Config, bank, commands
from redbot.core.commands import Cog

from .skills import SKILLTREES
from .locations import STARWARSLOCATIONMODIFIERS
from .buffs import BUFFS

SKILLTREEREQ = {
    "Dueling": ["Broadsword", "Longsword", "Shortsword", "Lightsaber", "Mace", "Rapier", "Small Sword", "Axe", "Scimitar"],
    "Horse Riding": ["Horseback"],
    "Marksmanship": ["Blaster", "Rifles", "Archery", "Flintlock", "Cannon"],
    "Force-Wielding": ["Force Abilities"],
    "Charisma": ["Commander"],
    "Magic": ["Spells", "Magic Stances"]
}

BASESTATS = {
    "HP": 25000,
    "Damage": 1000,
    "Defense": 20,
    "Evasion": 5,
    "Crit Chance": 20,
    "Speed": 100,
    "Crit Damage": 150,
    "Energy": 100,
    "Accuracy": 100,
    "Tenacity": 25,
    "Potency": 25
}

DUELINGADDITION = {
    "HP": 5,
    "Damage": 1,
    "Crit Chance": 1,
    "Crit Damage": 3,
    "Speed": 0.5,
    "Evasion": 1,
    "Defense": 2,
    "Accuracy": 1,
    "Tenacity": 1
}
FORCEADDITION = {
    "HP": 4,
    "Damage": 2,
    "Crit Chance": 0.5,
    "Crit Damage": 2,
    "Energy": 10,
    "Defense": 1,
    "Accuracy": 1.5,
    "Tenacity": 2,
    "Potency": 1.5
}
MAGICADDITION = {
    "HP": 4,
    "Damage": 2,
    "Crit Chance": 0.5,
    "Crit Damage": 2,
    "Energy": 10,
    "Defense": 1,
    "Accuracy": 1,
    "Tenacity": 3,
    "Potency": 2
}
MARKSMANADDITION = {
    "HP": 2,
    "Damage": 3,
    "Crit Chance": 1.5,
    "Crit Damage": 3,
    "Potency": 1,
    "Defense": 0.5,
    "Accuracy": 2,
    "Tenacity": 0.5
}
CHARISMAADDITION = {
    "HP": 3,
    "Damage": 0.5,
    "Crit Chance": 1,
    "Crit Damage": 1,
    "Speed": 0.5,
    "Defense": 1,
    "Accuracy": 0.5,
    "Tenacity": 1,
    "Energy": 5
}

class DuelManager(Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def red_delete_data_for_user(self,**kwargs):
        return
        
    @commands.command(name="duelsandbox", aliases=["lds"])
    async def duelsandbox(self, ctx: commands.Context):
        """Set up a duel sandbox with customizable settings."""

        def create_dropdown(options, placeholder, custom_id):
            """Helper function to create a dropdown view."""
            options = [
                discord.SelectOption(label=opt, value=opt) for opt in options
            ]
            dropdown = discord.ui.Select(placeholder=placeholder, options=options, custom_id=custom_id)
            view = discord.ui.View()
            view.add_item(dropdown)
            return view
        
        era_view = create_dropdown(["Star Wars"], "Select an era", "era")
        era_message = await ctx.send("Select the era for the duel to take place in:", view=era_view)

        def era_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "era"
        
        era_interaction = await self.bot.wait_for("interaction", check=era_check)
        era = era_interaction.data["values"][0]
        await era_message.delete()

        locations = STARWARSLOCATIONMODIFIERS.keys()
        location_view = create_dropdown(locations, "Select a location", "location")
        location_message = await ctx.send("Select the location for the duel:", view=location_view)

        def location_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "location"

        location_interaction = await self.bot.wait_for("interaction", check=location_check)
        location = location_interaction.data["values"][0]
        await location_message.delete()

        location_images = STARWARSLOCATIONMODIFIERS.get(location).get("images")

        weapon_view = create_dropdown(["Lightsaber"], "Select your primary weapon", "weapon")
        weapon_message = await ctx.send("Select your primary weapon:", view=weapon_view)

        def weapon_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "weapon"

        weapon_interaction = await self.bot.wait_for("interaction", check=weapon_check)
        weapon = weapon_interaction.data["values"][0]
        await weapon_message.delete()

        opponent_type_view = create_dropdown(["NPC"], "Select opponent type", "opponent_type")
        opponent_type_message = await ctx.send("Select if your opponent is another user or an NPC:", view=opponent_type_view)

        def opponent_type_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "opponent_type"

        opponent_type_interaction = await self.bot.wait_for("interaction", check=opponent_type_check)
        opponent_type = opponent_type_interaction.data["values"][0]
        await opponent_type_message.delete()

        opponent_view = create_dropdown(["TestNPC"], "Select opponents (up to 5)", "opponent")
        opponent_message = await ctx.send("Select your opponents (you must select at least one):", view=opponent_view)

        def opponent_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "opponent"
        
        opponent_interaction = await self.bot.wait_for("interaction", check=opponent_check)
        opponents = opponent_interaction.data["values"]
        await opponent_message.delete()

        ally_view = create_dropdown(["None"], "Select allies (up to 4)", "ally")
        ally_message = await ctx.send("Select your allies (option, up to 4):", view=ally_view)

        def ally_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "ally"

        ally_interaction = await self.bot.wait_for("interaction", check=ally_check)
        allies = ally_interaction.data["values"]
        await ally_message.delete()

        stance_view = create_dropdown(["Basic Stance"], "Select your starting stance", "stance")
        stance_message = await ctx.send("Select your starting stance:", view=stance_view)

        def stance_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "stance"

        stance_interaction = await self.bot.wait_for("interaction", check=stance_check)
        stance = stance_interaction.data["values"][0]
        await stance_message.delete()

        settings = (
            f"**Era**: {era}\n"
            f"**Location**: {location}\n"
            f"**Primary Weapon**: {weapon}\n"
            f"**Starting Stance**: {stance}\n"
            f"**Opponents**: {', '.join(opponents)}\n"
            f"**Allies**: {', '.join(allies)}\n"
        )

        confirm_view = create_dropdown(["Yeah, let's start", "Cancel"], "Confirm settings", "confirm")
        confirm_message = await ctx.send(f"Do these settings look correct?\n{settings}", view=confirm_view)

        def confirm_check(interaction): return interaction.user == ctx.author and interaction.data["custom_id"] == "confirm"

        confirm_interaction = await self.bot.wait_for("interaction", check=confirm_check)
        confirmation = confirm_interaction.data["values"][0]
        await confirm_message.delete()

        if confirmation == "Cancel":
            await ctx.send("Duel setup canceled.")
            return
        
        await ctx.send("Settings confirmed! Starting the duel...")

        loading_message = await ctx.send("Loading...")
        loading_bar_length = 20
        loading_progress = 0

        for i, image_url in enumerate(location_images):
            embed = discord.Embed(title=f"Loading {location}")
            embed.set_image(url=image_url)
            loading_increment = random.randint(3, 7)
            loading_progress = min(loading_progress + loading_increment, loading_bar_length)
            loading_bar = f"[{'█' * loading_progress}{'▒' * (loading_bar_length - loading_progress)}]"
            embed.add_field(name="Loading", value=loading_bar, inline=False)
            await loading_message.edit(embed=embed)
            await asyncio.sleep(3)
        
        await ctx.send("Duel is ready! Let the battle begin!")

        await self.startduel(ctx, location, weapon, stance, opponents, allies)

    async def startduel(self, ctx, location, primary_weapon, starting_stance, opponents, allies):
        """Starts the duel logic"""
        ABILITIES = {
            "Basic Slash": [0, "Deals Base Damage.", {"Effect": {"Damage": 1}, "Cooldown": 0}],
            "Deflect": [0, "Temporarily increases Evasion.", {"Effect": {"Buff": {"Target": "player", "Name": "Fortified"}}, "Cooldown": 2}],
            "Charge Slash": [0, "Deals high damage but applies vulnerable to the user.", {"Effect": {"Damage": 1.4, "Crit Chance": 200000, "Buff": {"Target": "player", "Name": "Vulnerable"}}}, "Cooldown": 3,
        }]

        actions_log = []

        def update_actions_embed(embed, actions_log, new_action):
            """Update the actions embed to display the last three actions."""
            actions_log.append(new_action)
            if len(actions_log) > 3:
                actions_log.pop(0)
            
            embed.clear_fields()
            for i, action in enumerate(actions_log, start=1):
                embed.add_field(name=f"Action {i}", value=action, inline=False)

        def generate_action_desc(attacker, defender, ability_name, damage, crit, buffs_applied, hit, resisted):
            """Generates a description of abilities used."""
            ability_effect = ABILITIES[ability_name][2]["Effect"]

            if not hit:
                action_desc = f"{attacker['name']} used {ability_name} on {defender['name']}, but it missed!"
            elif resisted:
                action_desc = f"{attacker['name']} used {ability_name} to apply a debuff on {defender['name']}, but they resisted it!"
            elif damage > 0:
                action_desc = (
                    f"{attacker['name']} used {ability_name} on {defender['name']} dealing {damage} damage."
                    + (" ***(Critical Hit!)***" if crit else "")
                )
            else:
                action_desc = f"{attacker['name']} used {ability_name}."
            
            if buffs_applied:
                buff_details = []
                for target, buff_name in buffs_applied:
                    buff_target = attacker["name"] if target == attacker else defender["name"]
                    buff_details.append(f"{buff_target} gained {buff_name}")
                
                action_desc += " " + "And also ".join(buff_details) + "."
            
            return action_desc

        def calculate_damage(attacker, defender, ability_effect):
            """Calculate damage based on stats."""
            damage_multiplier = ability_effect.get("Damage", 1)
            base_damage = float(attacker["Damage"]) * damage_multiplier
            base_damage *= random.uniform(.9, 1.1)

            if "Vulnerable" in defender["buffs"]:
                base_damage *= 1.2

            if random.randint(1, 100) <= attacker["Crit Chance"]:
                base_damage *= (attacker["Crit Damage"]/100)
                is_crit = True
                crit_chance_multiplier = ability_effect.get("Crit Chance", 0)
                crit_chance = attacker["Crit Chance"] + crit_chance_multiplier
            else:
                is_crit = False
            
            defense_reduction = calculate_defense(defender) / 100
            damage_taken = base_damage * (1 - defense_reduction)

            return max(0, round(damage_taken)), is_crit
        
        def calculate_defense(defender, k=50):
            base_defense = defender["Defense"]
            total_defense = base_defense

            for buff_name, buff_data in defender["buffs"].items():
                if "Defense Change" in buff_data["Effect"]:
                    total_defense += base_defense * buff_data["Effect"]["Defense Change"]

            effective_defense = total_defense / (total_defense + k)
            return min(effective_defense * 100, 90)
            

        def calculate_hit(attacker, defender):
            """Determine if the attack hits based on accuract and evasion."""
            effective_accuracy = attacker["Accuracy"] - defender["Evasion"]
            return random.randint(1, 100) <= max(0, effective_accuracy)
        
        def process_counterattack(attacker, defender):
            """Check and process counterattacks."""
            for buff_name, buff_data in defender["buffs"].items():
                if "Counterattack" in buff_data["Effect"] and buff_data["Effect"]["Counterattack"]:
                    counter_damage = round(defender["Damage"] * random.uniform(.9, 1.1))
                    counter_damage = round(counter_damage)
                    attacker["HP"] = max(0, attacker["HP"] - counter_damage)

                    defender["buffs"][buff_name]["Effect"]["Counterattacker"] = False
                    return f"{defender['name']} counterattacked, hitting {attacker['name']} for {counter_damage} damage."
                return None
        
        def get_ability_options(attacker):
            """Generate ability options for the attacker."""
            return [ability for ability, details in ABILITIES.items() if attacker["cooldowns"].get(ability, 0) == 0]
        
        def reduce_cooldowns(attacker):
            """Reduce cooldowns for all abilities by 1, but not below 0."""
            for ability in attacker["cooldowns"]:
                attacker["cooldowns"][ability] = max(0, attacker["cooldowns"][ability] - 1)
        
        def apply_buff(target, buff_name):
            if buff_name in BUFFS:
                buff = BUFFS[buff_name]
                if buff_name in target["buffs"]:
                    target["buffs"][buff_name]["Duration"] = buff.get("Duration", None)
                    if "Counterattack" in buff["Effect"]:
                        target["buffs"][buff_name]["Effect"]["Counterattack"] = True
                    return
                target["buffs"][buff_name] = {
                    "Effect": buff["Effect"],
                    "Duration": buff.get("Duration", None),
                    "Original Stats": {
                        stat: target[stat] for stat in buff["Effect"] if stat in target
                    }
                }
                for stat, effect in buff["Effect"].items():
                    if stat not in target:
                        continue
                    if isinstance(effect, float):
                        target[stat] += round(target[stat] * effect)
                    elif isinstance(effect, int):
                        target[stat] += effect

        def apply_ability_effect(attacker, defender, ability_name):
            """Applies the effects of the selected ability."""
            ability_data = ABILITIES.get(ability_name, None)
            if not ability_data:
                return "Invalid ability selected."
            
            ability_effect = ability_data[2]["Effect"]
            buffs_applied = []
            resisted = False

            if "Buff" in ability_effect:
                buff_data = ability_effect["Buff"]
                target = attacker if buff_data["Target"] == "player" else defender
                if target == defender and "Potency" in attacker and "Tenacity" in defender:
                    potency = attacker["Potency"]
                    tenacity = defender["Tenacity"]
                    if random.randint(1, 100) <= max(0, tenacity - potency):
                        resisted = True
                    else:
                        apply_buff(target, buff_data["Name"])
                        buffs_applied.append((target, buff_data["Name"]))
                else:
                    apply_buff(target, buff_data["Name"])
                    buffs_applied.append((target, buff_data["Name"]))
            
            damage_multiplier = ability_effect.get("Damage", None)
            damage = damage_multiplier if damage_multiplier is not None else 0

            return {"Damage": damage, "Buffs Applied": buffs_applied, "Resisted": resisted}

        def process_buffs(target):
            """Process buffs at the start of the target's turn."""
            to_remove = []
            for buff_name, buff_data in target["buffs"].items():
                for stat, effect in buff_data["Effect"].items():
                    if stat == "Damage Over Time":
                        dot_damage = round(target["HP"] * effect)
                        target["HP"] = max(0, target["HP"] - dot_damage)
                        
                if buff_data["Duration"] is not None:
                    buff_data["Duration"] -= 1
                    if buff_data["Duration"] <= 0:
                        for stat, original_value in buff_data["Original Stats"].items():
                            target[stat] = original_value
                        to_remove.append(buff_name)
            
            for buff_name in to_remove:
                del target["buffs"][buff_name]
        
        player = {"name": ctx.author.display_name, "cooldowns": {}, "buffs": {}, **BASESTATS}
        npc = {"name": opponents[0], "cooldowns": {}, "buffs": {}, **BASESTATS}

        for ability in ABILITIES:
            player["cooldowns"][ability] = 0
            npc["cooldowns"][ability] = 0

        embed_hp = discord.Embed(title="Duel Participants", description="Tracking HP and Energy.")
        embed_hp.add_field(name=f"{player['name']} (Player)", value=f"HP: {player['HP']} | Energy: {player['Energy']} | Buffs: {', '.join(player['buffs'].keys())}", inline=False)
        embed_hp.add_field(name=f"{npc['name']} (NPC)", value=f"HP: {npc['HP']} | Energy: {npc['Energy']} | Buffs: {', '.join(npc['buffs'].keys())}", inline=False)

        embed_actions = discord.Embed(title="Recent Actions", description="Tracking latest moves.")
        embed_actions.add_field(name="Actions", value="None yet.", inline=False)

        message_hp = await ctx.send(embed=embed_hp)
        message_actions = await ctx.send(embed=embed_actions)

        turn = 0
        while player["HP"] > 0 and npc["HP"] > 0:
            attacker, defender = (player, npc) if turn % 2 == 0 else (npc, player)
            
            if attacker == player:
                process_buffs(player)
                reduce_cooldowns(player)

                ability_options = get_ability_options(player)
                if not ability_options:
                    await ctx.send("No abilities are available to use.")
                buttons = [
                    discord.ui.Button(label=ability, style=discord.ButtonStyle.primary, custom_id=ability)
                    for ability in ability_options
                ]
                view = discord.ui.View()
                for button in buttons:
                    view.add_item(button)
                
                select_mess = await ctx.send(f"{player['name']}, choose your ability:", view=view)

                def ability_select_callback(interaction):
                    return interaction.user == ctx.author and interaction.data["custom_id"]
                try:
                    print("Waiting for ability selection...")
                    ability_interaction = await self.bot.wait_for("interaction", check=ability_select_callback)
                    print("Interaction received:", ability_interaction)
                    selected_ability = ability_interaction.data["custom_id"]
                except asyncio.TimeoutError:
                    await ctx.send("You took too long to respond so ability defaulted to Basic Slash.")
                    selected_ability = "Basic Slash"
                ability_effect = apply_ability_effect(player, npc, selected_ability)
                player["cooldowns"][selected_ability] = ABILITIES[selected_ability][2]["Cooldown"]
                await select_mess.delete()      

            else:
                process_buffs(npc)
                selected_ability = "Basic Slash"   
                ability_effect = apply_ability_effect(npc, player, selected_ability)
            
            damage, crit = 0, False
            if not ability_effect["Resisted"] and calculate_hit(attacker, defender):
                damage, crit = calculate_damage(attacker, defender, ability_effect)
                if defender["HP"] - damage < 0:
                    defender["HP"] = 0
                    damage = defender["HP"]
                else:
                    defender["HP"] -= damage
            
            
            counter_desc = process_counterattack(attacker, defender)
            
            action_desc = generate_action_desc(attacker, defender, selected_ability, damage, crit, ability_effect["Buffs Applied"], hit=not ability_effect["Resisted"], resisted=ability_effect["Resisted"])
            
            if counter_desc:
                action_desc += f"\n{counter_desc}"
            
            embed_hp.set_field_at(0, name=f"{player['name']} (Player)", value=f"HP: {player['HP']} | Energy: {player['Energy']} | Buffs: {', '.join(player['buffs'].keys())}", inline=False)
            embed_hp.set_field_at(1, name=f"{npc['name']} (NPC)", value=f"HP: {npc['HP']} | Energy: {npc['Energy']} | Buffs: {', '.join(npc['buffs'].keys())}", inline=False)
            update_actions_embed(embed_actions, actions_log, action_desc)

            await message_hp.edit(embed=embed_hp)
            await message_actions.edit(embed=embed_actions)

            turn += 1
            await asyncio.sleep(1)
        
        winner = player["name"] if player["HP"] > 0 else npc["name"]
        await ctx.send(f"The duel is over! {winner} wins!")
