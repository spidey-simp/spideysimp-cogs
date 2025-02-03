import random
import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands, Config
import asyncio

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

    @app_commands.command(name="duel", description="Challenge another user to a duel based on your RPG stats.")
    @app_commands.describe(opponent="The user you want to duel", nsfw="Enable NSFW battle messages?")
    async def duel(self, interaction: discord.Interaction, opponent: discord.User, nsfw: bool = False):
        if opponent == interaction.user:
            await interaction.response.send_message("You can't duel yourself!", ephemeral=True)
            return
        
        user_stats = await self.config.user(interaction.user).stats()
        opponent_stats = await self.config.user(opponent).stats()

        if not user_stats or not opponent_stats:
            await interaction.response.send_message("Both players must generate their stats using `/stats` first!", ephemeral=True)
            return
        
        user_hp = 20 + user_stats["Endurance"]
        opponent_hp = 20 + opponent_stats["Endurance"]

        user_speed = user_stats["Speed"] + random.randint(1, 3)
        opponent_speed = opponent_stats["Speed"] + random.randint(1, 3)
        user_first = user_speed > opponent_speed

        user_attack = user_stats["Strength"] + (random.randint(1, user_stats["Luck"]) // 2)
        opponent_attack = opponent_stats["Strength"] + (random.randint(1, opponent_stats["Luck"]) // 2)

        
        attacker, defender = (interaction.user, opponent) if user_first else (opponent, interaction.user)
        attacker_stats, defender_stats = (user_stats, opponent_stats) if user_first else (opponent_stats, user_stats)
        attacker_hp, defender_hp = (user_hp, opponent_hp) if user_first else (opponent_hp, user_hp)
        attacker_attack, defender_attack = (user_attack, opponent_attack) if user_first else(opponent_attack, user_attack)
        
        await interaction.response.defer(thinking=True)
        await asyncio.sleep(1)
        await interaction.followup.send(f"⚔️ {interaction.user.mention} challenges {opponent.mention} to a duel!")
        await asyncio.sleep(1)
        await interaction.followup.send(f"**{attacker.display_name}** is faster and will go first!")
        await asyncio.sleep(1)

        attack_messages = {
            "low": [
                "{attacker} throws a pebble at {defender}. It barely does anything. **{damage}** damage!",
                "{attacker} slaps {defender} across the face. Disrespectful! **{damage}** damage.",
                "{attacker} flicks {defender} on the forehead. {defender} is annoyed. **{damage}** damage."
            ],
            "medium": [
                "{attacker} swings their sword and cuts {defender} for **{damage}** damage!",
                "{attacker} kicks {defender} square in the chest. **{damage}** damage!",
                "{attacker} smashes a chair over {defender}’s back. **{damage}** damage!"
            ],
            "high": [
                "{attacker} dropkicks {defender} through a wall! **{damage}** damage!",
                "{attacker} body slams {defender} like a WWE wrestler! **{damage}** damage!",
                "{attacker} launches {defender} into the air with a cannon blast! **{damage}** damage!"
            ],
            "super": [
                "{attacker} drops a NUKE on {defender}. Rest in peace. **{damage}** damage!",
                "{attacker} summons a meteor to crash directly onto {defender}! **{damage}** damage!",
                "{attacker} unleashes an **earthquake**, splitting the ground beneath {defender}! **{damage}** damage!"
            ]
        }

        # NSFW Attack Messages
        nsfw_attack_messages = {
            "low": [
                "{attacker} flicks {defender} on the nipple. **Weird.** **{damage}** damage.",
                "{attacker} gives {defender} a 'friendly' slap on the ass. **{damage}** damage.",
                "{attacker} spits directly into {defender}’s mouth. **Why?** **{damage}** damage."
            ],
            "medium": [
                "{attacker} kicks {defender} **right in the dick**! **{damage}** damage!",
                "{attacker} slaps {defender} so hard, they rethink their life choices. **{damage}** damage!",
                "{attacker} yanks {defender}’s pants down, humiliating them before striking. **{damage}** damage!"
            ],
            "high": [
                "{attacker} grabs {defender} by the throat and **slams them against the wall**! **{damage}** damage!",
                "{attacker} chokeslams {defender} through a flaming table! **{damage}** damage!",
                "{attacker} grinds against {defender} aggressively before delivering a brutal punch! **{damage}** damage!"
            ],
            "super": [
                "{attacker} pulls out the **World's Largest Dildo** and smashes {defender} with it. **{damage}** damage!",
                "{attacker} suplexes {defender} **off a moving airplane**! **{damage}** damage!",
                "{attacker} rides a **stampede of naked people** straight into {defender}! **{damage}** damage!"
            ]
        }

        dodge_messages = [
            "{defender} gracefully dodges {attacker}'s attack like a true ninja!",
            "{defender} slips just in time, and {attacker} completely misses!",
            "{defender} ducks at the last second, making {attacker} hit thin air!",
            "{defender} blocks {attacker}'s attack using sheer willpower!"
        ]

        nsfw_dodge_messages = [
            "{defender} twerks out of the way at the last second. {attacker} is confused!",
            "{defender} dodges with the grace of a stripper on payday.",
            "{defender} Matrix-dodges {attacker}’s attack like they’re dodging responsibilities.",
            "{defender} says ‘Not today, bitch’ and sidesteps flawlessly!"
        ]

        # When an attack completely fails but no self-damage
        nodamagefail_messages = [
            "{attacker} swings... and completely misses. Embarrassing.",
            "{attacker} charges with full force, but {defender} casually sidesteps.",
            "{attacker} loses focus mid-attack and just stands there awkwardly.",
            "{attacker} tries to attack but immediately regrets all their life choices."
        ]

        nsfw_nodamagefail_messages = [
            "{attacker} winds up for a powerful swing... but just flops like a limp noodle.",
            "{attacker} lunges at {defender}, but {defender} just laughs and walks away.",
            "{attacker} flexes dramatically before attacking, only to get distracted by their own biceps.",
            "{attacker} forgets what they were doing and just moans seductively instead."
        ]

        # When the attacker physically hurts themselves
        selfhurtfail_messages = [
            "{attacker} trips over their own feet and takes **{damage}** damage!",
            "{attacker} swings wildly and accidentally smacks themselves in the face! **Self-damage: {damage} HP!**",
            "{attacker} fumbles their weapon and somehow slices their own leg. **{damage} HP lost!**"
        ]

        nsfw_selfhurtfail_messages = [
            "{attacker} swings so hard they throw out their back! **Self-damage: {damage} HP!**",
            "{attacker} tries a fancy move but somehow manages to uppercut themselves in the crotch. **{damage} HP lost!**",
            "{attacker} attempts a powerful strike but steps on their own balls. **{damage} HP!**"
        ]

        # Fun healing messages
        heal_messages = [
            "{attacker} takes a moment to breathe and patches up their wounds. **Heals {heal} HP!**",
            "{attacker} drinks a mysterious potion. Somehow, it works! **+{heal} HP!**",
            "{attacker} slaps a bandage on their injuries. It’s not much, but it helps! **Heals {heal} HP!**",
            "{attacker} eats a banana mid-fight. **Regains {heal} HP!**"
        ]

        nsfw_heal_messages = [
            "{attacker} stops to rub themselves down... somehow, they feel better. **Heals {heal} HP!**",
            "{attacker} licks their wounds in the most sensual way possible. **+{heal} HP!**",
            "{attacker} takes a break to ‘hydrate’—and by hydrate, I mean tequila. **Heals {heal} HP!**",
            "{attacker} moans loudly while applying ointment. **Regains {heal} HP!**"
            "{attacker} takes a break to edge themselves, which surprisingly heals them. **Heals {heal} HP!**"
        ]


        while attacker_hp > 0 and defender_hp > 0:
            if nsfw:
                nsfw_chance = random.randint(1,2)
                nsfw_mess = True if nsfw_chance == 1 else False
            heal_chance = random.randint(1, 10)
            if heal_chance == 1:
                heal_amount = random.randint(5, 15)
                attacker_hp += heal_amount
                message_list = nsfw_heal_messages if nsfw_mess else heal_messages
                message = random.choice(message_list).format(attacker=attacker.display_name, heal=heal_amount)
            else:
                apoc_chance = random.randint(1, 100)
                if apoc_chance > 99:
                    damage = random.randint(100, 10000000)
                    damage_tier = "super"
                else:
                    base_attack = random.randint(attacker_attack // 2, attacker_attack)
                    damage = base_attack + random.randint(-10, 10)

                    if damage >= 15:
                        damage_tier = "super"
                    elif damage > 7:
                        damage_tier = "high"
                    elif damage > 3:
                        damage_tier = "medium"
                    elif damage > 0:
                        damage_tier = "low"

                dodge = False
                dodge_chance = min(50, defender_stats["Dexterity"] * 3 + defender_stats["Intelligence"] * 2 + random.randint(-10, 10))
                if random.randint(1, 100) <= dodge_chance and damage_tier != "super":
                    dodge = True
                
                if dodge:
                    message_list = nsfw_dodge_messages if nsfw_mess else dodge_messages
                    message = random.choice(message_list).format(attacker=attacker.display_name, defender=defender.display_name)
                else:
                    if damage < 0:
                        message_list = nsfw_selfhurtfail_messages if nsfw_mess else selfhurtfail_messages
                        message = random.choice(message_list).format(attacker=attacker.display_name, damage=-damage)
                        attacker_hp += damage
                    elif damage == 0:
                        message_list = nsfw_nodamagefail_messages if nsfw_mess else nodamagefail_messages
                        message = random.choice(message_list).format(attacker=attacker.display_name, defender=defender.display_name)
                    else:
                        message_list = nsfw_attack_messages if nsfw_mess else attack_messages
                        message = random.choice(message_list[damage_tier]).format(attacker=attacker.display_name, defender=defender.display_name, damage=damage)
                        defender_hp -= damage
                    
                
            await interaction.followup.send(message)
            await asyncio.sleep(2)

            if defender_hp > 0:
                attacker, defender = defender, attacker
                attacker_hp, defender_hp = defender_hp, attacker_hp
            
        winner = attacker.mention if attacker_hp > 0 else defender.mention
        loser = defender.mention if attacker_hp > 0 else attacker.mention

        await interaction.followup.send(f"🏆 **{winner} stands victorious over {loser}!**")
