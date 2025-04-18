import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks
from redbot.core import commands
import json
import os
import random
import asyncio
from datetime import datetime
import re
from collections import defaultdict

BASE_DIR = os.path.dirname(__file__)

static_path = os.path.join(BASE_DIR, "cold_war.json")
dynamic_path = os.path.join(BASE_DIR, "cold_war_modifiers.json")


def debug_log(message):
    log_path = os.path.expanduser("~/debug_output.log")
    with open(log_path, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")


BACKUP_CHANNEL_ID = 1357944150502412288

async def backup_dynamic_json(self):
    try:
        with open(dynamic_path, "r") as f:
            data = json.load(f)

        channel = self.bot.get_channel(BACKUP_CHANNEL_ID)
        if channel is None:
            channel = await self.bot.fetch_channel(BACKUP_CHANNEL_ID)

        content = json.dumps(data, indent=2)
        if len(content) > 1900:
            # If too big for a single message, send as a file
            file = discord.File(fp=dynamic_path, filename="cold_war_backup.json")
            await channel.send(content="📦 Cold War dynamic data backup on cog unload:", file=file)
        else:
            await channel.send(f"📦 Cold War dynamic data backup on cog unload:\n```json\n{content}\n```")

    except Exception as e:
        print(f"Failed to backup dynamic JSON: {e}")


class ConfirmSpyAssignView(discord.ui.View):
    def __init__(self, cog: "SpideyUtils", country: str, target: str, operation: str, op_data: dict, params: dict):
        super().__init__(timeout=30)
        self.cog = cog
        self.country = country
        self.target = target
        self.operation = operation
        self.op_data = op_data
        self.params = params

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: discord.ui.Button):
        # ensure our data is initialized
        self.cog.init_spy_data(self.country)
        actor = self.cog.cold_war_data["countries"][self.country]["espionage"]

        # recompute free = total – sum(already assigned)
        total = actor.get("total_operatives", 0)
        assigned = actor.get("assigned_ops", {})
        used = sum(
            self.cog.cold_war_data["ESPIONAGE"]["operations"][op]["required_operatives"]
            for tgt, ops in assigned.items()
            for op in ops
        )
        free = total - used

        req = self.op_data.get("required_operatives", 1)
        if free < req:
            return await interaction.response.edit_message(
                content=f"❌ Only {free} operatives free now — cannot assign {req}.",
                embed=None, view=None
            )

        # log the assignment
        assigned.setdefault(self.target, {})[self.operation] = self.params or True

        # optionally keep operatives_available in sync
        actor["operatives_available"] = free - req

        self.cog.save_data()

        await interaction.response.edit_message(
            content=(
                f"✅ **{self.country}** has launched "
                f"`{self.operation.replace('_',' ').title()}` against **{self.target}**!\n"
                f"🕵️ Operatives remaining: `{free - req}`"
            ),
            embed=None,
            view=None
        )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Operation canceled.",
            embed=None, view=None
        )


class RequestRoll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="requestroll", description="Submit a roll request to the GM.")
    async def requestroll(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RequestRollModal())
    
    @app_commands.command(name="myrequests", description="View your own roll request history.")
    async def myrequests(self, interaction: discord.Interaction):
        filepath = "roll_requests.json"
        if not os.path.exists(filepath):
            return await interaction.response.send_message("You have no roll requests.", ephemeral=True)

        with open(filepath, "r") as f:
            requests = json.load(f)

        user_requests = [r for r in requests if r["user_id"] == interaction.user.id]
        if not user_requests:
            return await interaction.response.send_message("You have no roll requests.", ephemeral=True)

        embed = discord.Embed(title=f"🎲 Roll Requests for {interaction.user.display_name}", color=discord.Color.blurple())
        for r in reversed(user_requests[-10:]):
            embed.add_field(
                name=f"{r['reason']} (Turn {r['game_turn']}, {r['game_year']})",
                value=(
                    f"**Status:** {r['status']}\n"
                    f"**Modifier:** {r['modifier']}\n"
                    f"**Submitted:** {r['timestamp']} UTC"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class StartProjectConfirmView(discord.ui.View):
    def __init__(self, user_id, country, project_name, penalties, data_ref, save_callback):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.country = country
        self.project_name = project_name
        self.penalties = penalties
        self.data_ref = data_ref
        self.save_callback = save_callback

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("You're not authorized to confirm this action.", ephemeral=True)

        country_data = self.data_ref["countries"][self.country]
        research = country_data.get("research", {})
        np_data = country_data.setdefault("national_projects", {})

        # Determine default milestone logic
        project_name = self.project_name
        milestone_defs = self.data_ref.get("NATIONAL PROJECTS", {}).get("milestones", {}).get(project_name, {})
        milestone_1 = milestone_defs.get("milestone_1", {})
        duration = milestone_1.get("duration_days", 365)

        # Special case: country already has nukes
        if project_name == "nuclear_weapons" and research.get("nuclear_arsenal", 0) >= 1:
            np_data[project_name] = {
                "status": "paused_development",
                "days_remaining": None,
                "milestones_completed": ["milestone_1", "milestone_2", "milestone_3"]
            }
            abilities = country_data.setdefault("abilities", [])
            if "unlock_nuclear_production" not in abilities:
                abilities.append("unlock_nuclear_production")

            msg = (
                f"✅ `{project_name}` is now officially tracked.\n"
                f"🧨 This country has already completed early nuclear development.\n"
                f"Progress is marked as **paused** at milestone 3.\n"
                f"Abilities unlocked: `unlock_nuclear_production`."
            )
        else:
            # Standard project start
            np_data[project_name] = {
                "status": "milestone_1",
                "days_remaining": duration,
                "milestones_completed": []
            }

            msg = (
                f"✅ `{project_name}` project has begun in {self.country}.\n"
                f"🚀 Status: `milestone_1` — `{milestone_1.get('name', 'Unknown')}`\n"
                f"⏳ Time remaining: {duration} days."
            )

        # Apply penalties
        if "research_penalty" in self.penalties:
            country_data["research"]["research_bonus"] -= self.penalties["research_penalty"]
        if "espionage_penalty" in self.penalties:
            country_data["espionage"]["domestic_intelligence_score"] -= self.penalties["espionage_penalty"]
        if "factory_penalty" in self.penalties:
            country_data["economic"]["industrial_sectors"] = max(0, country_data["industrial_sectors"] - self.penalties["factory_penalty"])

        self.save_callback()
        await interaction.response.edit_message(content=msg, view=None, embed=None)


    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Project canceled.", view=None, embed=None)


class RequestRollModal(discord.ui.Modal, title="Request a GM Roll"):
    reason = discord.ui.TextInput(label="Reason for roll", style=discord.TextStyle.paragraph)
    modifier = discord.ui.TextInput(
        label="Suggested modifier",
        placeholder="examples: +10 for advantage, -5 for disadvantage, etc.",
        required=False
    )


    async def on_submit(self, interaction:discord.Interaction):
        if os.path.exists("current_turn.json"):
            with open("current_turn.json", "r") as f:
                game_state = json.load(f)
            game_turn = game_state["turn"]
            game_year = game_state["year"]
        else:
            game_turn = 0
            game_year = "Unknown"
        
        request = {
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "reason": self.reason.value,
            "modifier": self.modifier.value if self.modifier.value else "No suggestion",
            "status": "need_gm_evaluation",
            "channel": interaction.channel.name,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "game_turn": game_turn,
            "game_year": game_year
        }

        filepath = "roll_requests.json"
        requests = []
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                requests = json.load(f)
        requests.append(request)
        with open(filepath, "w") as f:
            json.dump(requests, f, indent=2)

        gm_channel_id = 1357944150502412288
        gm_channel = interaction.client.get_channel(gm_channel_id)
        if gm_channel:
            embed = discord.Embed(title="🎲 New Roll Request", color=discord.Color.orange())
            embed.add_field(name="User", value=interaction.user.mention)
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            embed.add_field(name="Modifier", value=self.modifier.value or "No suggestion")
            embed.add_field(name="In-Game Time", value=f"Turn {game_turn} ({game_year})")
            embed.set_footer(text=f"Requested in #{interaction.channel.name} at {request['timestamp']} UTC")
            await gm_channel.send(embed=embed)

        await interaction.response.send_message("✅ Your roll request has been submitted.", ephemeral=True)

class ResearchConfirmView(discord.ui.View):
    def __init__(self, interaction, country, slot, tech_name, remaining_days, carry_used, data_ref):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.country = country
        self.slot = slot
        self.tech_name = tech_name
        self.remaining_days = remaining_days
        self.carry_used = carry_used
        self.data_ref = data_ref  # Reference to cold_war_data

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        research = self.data_ref["countries"][self.country]["research"]

        if self.remaining_days == 0:
            research["unlocked_techs"].append(self.tech_name)
            research["carryover_days"][self.slot] = self.carry_used - self.remaining_days
            msg = f"✅ `{self.tech_name}` was instantly unlocked using {self.carry_used} rollover days! 🎉"
        else:
            research["active_slots"][self.slot] = {
                "tech": self.tech_name,
                "days_remaining": self.remaining_days
            }
            research["carryover_days"][self.slot] = 0
            msg = f"🛠 `{self.tech_name}` is now being researched in slot {self.slot}.\nEstimated time: {self.remaining_days} days."

        # 🧠 Save changes to disk
        with open(dynamic_path, "w") as f:
            json.dump(self.data_ref, f, indent=2)

        await interaction.response.edit_message(content=msg, embed=None, view=None)


    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Research canceled.", embed=None, view=None)


class SpideyUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cold_war_data = {}
        debug_log("The logger is active and running!")
        self.load_data()
        self.alternate_country_dict = {}
        self.scheduled_backup.start()
    
    async def run_turn_tick(self):
        await self.resolve_spy_ops()

        # future:
        # await self.process_turn_queue()
        # self.regenerate_surplus()
        # self.tick_research_slots()
        # self.increment_unrest()


    @tasks.loop(hours=24)
    async def scheduled_backup(self):
        try:
            with open(dynamic_path, "r") as f:
                data = json.load(f)

            channel = self.bot.get_channel(BACKUP_CHANNEL_ID)
            if channel is None:
                channel = await self.bot.fetch_channel(BACKUP_CHANNEL_ID)

            content = json.dumps(data, indent=2)
            if len(content) > 1900:
                file = discord.File(fp=dynamic_path, filename="cold_war_daily_backup.json")
                await channel.send(content="🕐 Daily Cold War backup:", file=file)
            else:
                await channel.send(f"🕐 Daily Cold War backup:\n```json\n{content}\n```")

        except Exception as e:
            print(f"Scheduled backup failed: {e}")
    
    def load_data(self):
         # 1) load the static + dynamic JSON
            with open(static_path, "r") as f:
                self.cold_war_data = json.load(f)
            with open(dynamic_path, "r") as f:
                modifiers = json.load(f)

            # 2) merge top‐level tick info
            for k in ("turn", "current_year", "day"):
                if k in modifiers:
                    self.cold_war_data[k] = modifiers[k]

            # 3) merge per‐country dynamic changes
            for country, dyn_data in modifiers.get("countries", {}).items():
                static_country = self.cold_war_data["countries"].setdefault(country, {})

                # ——— espionage gets an overwrite of exactly these three keys ———
                esp = static_country.setdefault("espionage", {})
                # always merge networks and assigned_ops
                if "spy_networks" in dyn_data["espionage"]:
                    esp["spy_networks"] = dyn_data["espionage"]["spy_networks"]
                if "assigned_ops" in dyn_data["espionage"]:
                    esp["assigned_ops"] = dyn_data["espionage"]["assigned_ops"]
                # only overwrite operatives_available if it's explicitly in the dynamic file;
                # otherwise leave the static total_operatives → operatives_available
                if "operatives_available" in dyn_data["espionage"]:
                    esp["operatives_available"] = dyn_data["espionage"]["operatives_available"]

                # ——— everything else still merges as base + delta ———
                for section in ("research", "national_projects", "abilities", "past_turns", "player_id"):
                    if section in dyn_data:
                        dyn_val = dyn_data[section]
                        base_section = static_country.setdefault(section, {} if isinstance(dyn_val, dict) else None)

                        # dict => merge subkeys
                        if isinstance(dyn_val, dict):
                            for subkey, subval in dyn_val.items():
                                base_val = base_section.get(subkey)
                                if isinstance(base_val, (int, float)) and isinstance(subval, (int, float)):
                                    base_section[subkey] = base_val + subval
                                else:
                                    base_section[subkey] = subval
                        else:
                            # non‐dict (e.g. player_id): overwrite
                            static_country[section] = dyn_val

    def save_data(self):
        try:
            # 1) load the original static file so we know the base values
            with open(static_path, "r") as f:
                static = json.load(f)

            dynamic = {}

            # 2) preserve your top‑level turn info
            for k in ("turn", "current_year", "day"):
                if k in self.cold_war_data:
                    dynamic[k] = self.cold_war_data[k]

            dynamic["countries"] = {}

            for country, cdata in self.cold_war_data.get("countries", {}).items():
                static_country = static.get("countries", {}).get(country, {})
                d: dict = {}

                # --- RESEARCH SECTION ---
                if "research" in cdata:
                    static_research = static_country.get("research", {})
                    current_research = cdata["research"]
                    dyn_research: dict = {}
                    for key, val in current_research.items():
                        base = static_research.get(key)
                        # if both base and current are numbers, write the delta
                        if isinstance(val, (int, float)) and isinstance(base, (int, float)):
                            dyn_research[key] = val - base
                        else:
                            # otherwise just copy it (lists, dicts, nested dicts...)
                            dyn_research[key] = val
                    d["research"] = dyn_research

                # --- ESPIONAGE SECTION ---
                if "espionage" in cdata:
                    static_esp = static_country.get("espionage", {})
                    current_esp = cdata["espionage"]
                    dyn_esp: dict = {}
                    for key, val in current_esp.items():
                        base = static_esp.get(key)
                        if isinstance(val, (int, float)) and isinstance(base, (int, float)):
                            dyn_esp[key] = val - base
                        else:
                            dyn_esp[key] = val
                    d["espionage"] = dyn_esp

                # --- NATIONAL PROJECTS, ABILITIES, PAST_TURNS, PLAYER_ID ---
                # these you always want to overwrite in full
                for section in ("national_projects", "abilities", "past_turns", "player_id"):
                    if section in cdata:
                        d[section] = cdata[section]

                if d:
                    dynamic["countries"][country] = d

            # 3) write out only the deltas
            with open(dynamic_path, "w") as f:
                json.dump(dynamic, f, indent=2)

        except Exception as e:
            print("Failed to save cold_war_modifiers.json:", e)



    
    async def cog_unload(self):
        self.scheduled_backup.cancel()
        self.save_data()
        await backup_dynamic_json()

    def init_spy_data(self, country: str):
        """
        Initializes espionage-related dynamic fields for the given country
        in self.cold_war_data if they aren't already set.
        """
        esp = self.cold_war_data["countries"].setdefault(country, {}).setdefault("espionage", {})

        # Initialize operatives_available only if not set
        if "operatives_available" not in esp:
            esp["operatives_available"] = esp.get("total_operatives", 0)

        # Always ensure these are present
        esp.setdefault("assigned_ops", {})
        esp.setdefault("spy_networks", {})
    
    
    async def resolve_spy_ops(self):
        espionage_defs = self.cold_war_data.get("ESPIONAGE", {}).get("operations", {})
        global_log = []
        spy_results = {}

        for country, data in self.cold_war_data.get("countries", {}).items():
            espionage = data.get("espionage", {})
            assigned = espionage.get("assigned_ops", {})
            total_ops = espionage.get("total_operatives", 0)

            for target, ops in assigned.items():
                for op_name, params in ops.items():
                    op_def = espionage_defs.get(op_name)
                    if not op_def:
                        continue

                    # Base values
                    base_success = op_def["base_success_rate"]
                    base_caught = op_def["base_caught_or_kill_rate"]
                    required_network = op_def["network_requirement"]

                    # Actor vs. Target intel scores
                    actor_score = espionage.get("foreign_intelligence_score", 0)
                    target_score = self.cold_war_data["countries"].get(target, {}).get("espionage", {}).get("domestic_intelligence_score", 0)
                    network = espionage.get("spy_networks", {}).get(target, 0)

                    # Calculate success
                    network_boost = max((network - required_network) / 100 + 1, 0.5)
                    intel_boost = max((actor_score - target_score) / 100 + 1, 0.5)

                    final_success = base_success * network_boost * intel_boost
                    caught_chance = base_caught * (1 - (network_boost - 1)) * (1 - (intel_boost - 1))

                    import random
                    success = random.random() < final_success
                    caught = not success and random.random() < caught_chance

                    # Build result message
                    actor_display = f"**{country}** attempted `{op_name}` in **{target}**"
                    result_msg = f"{actor_display} → {'✅ SUCCESS' if success else '❌ FAILURE'}"
                    if caught:
                        result_msg += " — 🛑 AGENTS CAUGHT"
                        espionage["total_operatives"] = max(0, espionage["total_operatives"] - 1)

                    # Apply effects if successful
                    if success:
                        for effect in op_def.get("actor_effects", []):
                            self.apply_espionage_effect(country, effect, target, params)
                        for effect in op_def.get("target_effects", []):
                            self.apply_espionage_effect(target, effect, target, params)

                    # Store result for player or GM notification
                    spy_results.setdefault(country, []).append(result_msg)
                    if op_def.get("opp_knowledge", False) and caught:
                        spy_results.setdefault(target, []).append(f"🔎 {actor_display} → Spies detected!")

                    # Add to global log if global event
                    if success and op_def.get("global_event", False):
                        global_log.append(
                            f"🌍 Global Event Triggered: **{country}** succeeded with `{op_name}` in **{target}**.\n<@684457913250480143> — consider posting a global RP event."
                        )

            # Reset turn data
            espionage["operatives_available"] = total_ops
            espionage["assigned_ops"] = {}

        self.save_data()

        # Send global log to backup log channel
        if global_log:
            channel = self.bot.get_channel(1357944150502412288)
            if channel is None:
                channel = await self.bot.fetch_channel(1357944150502412288)
            await channel.send("🕵️ **Espionage - Global Event Alerts**\n" + "\n".join(global_log))


    def apply_espionage_effect(self, country: str, effect: dict, target: str, params: dict):
        """
        Apply one actor_effect or target_effect to `country` in self.cold_war_data.
        If the path ends in 'target', we replace it with the real target country name.
        """
        # — resolve the raw value (with .format for any {ideology}, {project}, etc.)
        raw = effect["value"]
        if isinstance(raw, str):
            raw = raw.format(country=target, **params)
            # try to cast to number
            for cast in (int, float):
                try:
                    raw = cast(raw)
                    break
                except:
                    continue

        # — split path and substitute any "target" segment with the actual target
        segments = [
            (target if seg == "target" else seg)
            for seg in effect["path"].split(".")
        ]

        # — drill down to the penultimate node
        node = self.cold_war_data["countries"][country]
        for seg in segments[:-1]:
            node = node.setdefault(seg, {})

        final_key = segments[-1]

        # — perform the operation
        if effect["type"] == "add":
            node[final_key] = node.get(final_key, 0) + raw
        elif effect["type"] == "set":
            node[final_key] = raw
        else:
            raise ValueError(f"Unknown espionage effect type: {effect['type']}")





    async def autocomplete_country(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=country, value=country)
            for country in self.cold_war_data.get("countries", {}).keys()
            if current.lower() in country.lower()
            ][:25]
        
    def get_all_event_years(self, data):
        global_years = list(data.get("global_history", {}).keys())
        country_years = set()
        for country_data in data.get("countries", {}).values():
            country_years.update(country_data.get("country_history", {}).keys())
        return sorted(set(global_years).union(country_years), reverse=True)

    async def autocomplete_year(self, interaction: discord.Interaction, current: str):
        data = self.bot.get_cog("SpideyUtils").cold_war_data
        return [
                app_commands.Choice(name=yr, value=yr)
                for yr in self.get_all_event_years(data)
                if current in yr
            ][:25]

    @app_commands.command(name="view_history", description="View historical events for a specific country or globally.")
    @app_commands.describe(country="Optional country name to filter history.", global_view="Set to true to view global history.", year="Filter by a specific year")
    @app_commands.autocomplete(year=autocomplete_year)
    async def view_history(self, interaction: discord.Interaction, country: str = None, global_view: bool = False, year: str = None):
        await interaction.response.defer(thinking=True, ephemeral=False)

        
        data = self.bot.get_cog("SpideyUtils").cold_war_data

        if global_view:
            global_events = data.get("global_history", {})
            if not year:
                # Summary view – just year + headlines
                embed = discord.Embed(title="📰 Global Historical Record", color=discord.Color.blurple())
                for y, events in global_events.items():
                    if isinstance(events, dict):
                        event_names = "\n".join(f"• {title}" for title in events.keys())
                    else:
                        event_names = f"• {events}"
                    embed.add_field(name=f"{y}", value=event_names, inline=False)
                return await interaction.followup.send(embed=embed)
            else:
                # Specific year view – full embeds per event
                if year not in global_events:
                    return await interaction.followup.send(f"No global events found for {year}.", ephemeral=True)

                year_data = global_events[year]
                embeds = []
                if isinstance(year_data, dict):
                    for title, ev in year_data.items():
                        desc = ev.get("description", "No information available.")
                        img = ev.get("image")
                        dateline = ev.get("dateline")
                        byline = ev.get("byline")
                        quote = ev.get("quote")
                        tags = ev.get("tags", [])

                        dateline_str = f"**Dateline: {dateline}, {year}**\n\n" if dateline else ""
                        quote_str = f"\n\n_{quote}_" if quote else ""
                        tag_str = f"\n\n**TAGS:** {' | '.join(tag.upper() for tag in tags)}" if tags else ""

                        e = discord.Embed(
                            title=f"📰 {title} ({year})",
                            description=f"{dateline_str}{desc}{quote_str}{tag_str}",
                            color=discord.Color.blurple()
                        )

                        if img:
                            e.set_image(url=img)
                            e.set_footer(text="Image courtesy of the Associated Press")

                        if byline:
                            e.set_author(name=byline)

                        embeds.append(e)
                else:
                    e = discord.Embed(title=f"📰 Event in {year}", description=year_data, color=discord.Color.blurple())
                    embeds.append(e)
                return await interaction.followup.send(embeds=embeds[:10])

        # Country-specific view
        countries = data.get("countries", {})
        if country not in countries:
            return await interaction.response.send_message(f"❌ Country '{country}' not found.", ephemeral=True)

        country_data = countries[country].get("country_history", {})
        if not year:
            embed = discord.Embed(title=f"📜 Historical Timeline – {country}", color=discord.Color.gold())
            for y, ev in sorted(country_data.items()):
                if isinstance(ev, list):
                    embed.add_field(name=f"{y}", value="\n".join(f"• {e}" for e in ev), inline=False)
                else:
                    embed.add_field(name=f"{y}", value=f"• {ev}", inline=False)
            return await interaction.followup.send(embed=embed)
        else:
            events = country_data.get(year)
            if not events:
                return await interaction.followup.send(f"No events found for {country} in {year}.", ephemeral=True)

            embed = discord.Embed(title=f"📜 {country} – Historical Record ({year})", color=discord.Color.gold())
            if isinstance(events, list):
                embed.description = "\n".join(f"• {e}" for e in events)
            else:
                embed.description = f"• {events}"
            return await interaction.followup.send(embed=embed)
    
    def calculate_research_time(self, base_time, research_year, current_year, total_bonus=0):
        penalty = 0
        if research_year and int(current_year) < int(research_year):
            ahead = int(research_year) - int(current_year)
            penalty = int(base_time * (0.2 * ahead))
        adjusted = base_time + penalty
        return int(adjusted * (1 - total_bonus))

    def gather_the_children(self, node: dict, year: int, embed: discord.Embed, unlocked, in_progress, total_bonus):
        active_techs = [
            slot_data["tech"]
            for slot_data in in_progress.values()
            if isinstance(slot_data, dict) and "tech" in slot_data
        ]

        
        if not isinstance(node, dict):
            return

        tech_name = node.get("tech")
        if tech_name:
            base = node.get("research_time", 0)
            r_year = node.get("research_year", None)
            desc = node.get("description", "No description.")
            adjusted = self.calculate_research_time(base, r_year, year, total_bonus)
            status = "[✓]" if tech_name in unlocked else "[🛠]" if tech_name in active_techs else "[ ]"
            if status == "✓":
                label = f"[✓] {tech_name} ({r_year})"
            elif status == "🛠":
                days_remaining = next(
                    (slot_data["days_remaining"] for slot_data in in_progress.values()
                    if isinstance(slot_data, dict) and slot_data.get("tech") == tech_name),
                    adjusted
                )
                label = f"[🛠] {tech_name} ({r_year}) – {days_remaining} days remaining"
            else:
                label = f"[ ] {tech_name} ({r_year}) – {adjusted} days"

            embed.add_field(name=label, value=desc, inline=False)

        # Recurse into children only once
        if isinstance(node.get("child"), dict):
            self.gather_the_children(node["child"], year, embed, unlocked, in_progress, total_bonus)


    def create_the_embed(self, sub_branch, year, unlocked, in_progress, total_bonus, bonus_summary):
        active_techs = [
            slot_data["tech"]
            for slot_data in in_progress.values()
            if isinstance(slot_data, dict) and "tech" in slot_data
        ]
        
        embed = discord.Embed(
            title=f"📦 {sub_branch['sub_branch_name']} Sub-Branch",
            description=f"🔧 Research Speed Modifiers:\n{bonus_summary}",
            color=discord.Color.gold()
        )
        starter_name = sub_branch.get("starter_tech")
        base = sub_branch.get("research_time", 0)
        r_year = sub_branch.get("research_year", None)
        desc = sub_branch.get("description", "No description.")
        adjusted = self.calculate_research_time(base, r_year, year, total_bonus)
        status = "[✓]" if starter_name in unlocked else "[🛠]" if starter_name in active_techs else "[ ]"
        if status == "✓":
            label = f"[✓] {starter_name} ({r_year})"
        elif status == "🛠":
            days_remaining = next(
                (slot_data["days_remaining"] for slot_data in in_progress.values()
                if isinstance(slot_data, dict) and slot_data.get("tech") == starter_name),
                adjusted
            )
            label = f"[🛠] {starter_name} ({r_year}) – {days_remaining} days remaining"
        else:
            label = f"[ ] {starter_name} ({r_year}) – {adjusted} days"

        embed.add_field(name=label, value=desc, inline=False)
        if "child" in sub_branch:
            self.gather_the_children(sub_branch["child"], year, embed, unlocked, in_progress, total_bonus)
        return embed
    
    def format_bonus(self, bonus):
        sign = "+" if bonus > 0 else ""
        return f"{sign}{int(bonus * 100)}%"


    async def autocomplete_branch(self, interaction: discord.Interaction, current: str):
        branches = self.cold_war_data.get("tech_tree", {}).keys()
        return [app_commands.Choice(name=b, value=b) for b in branches if current.lower() in b.lower()][:25]

    async def autocomplete_sub_branch(self, interaction: discord.Interaction, current: str):
        tech_tree = self.cold_war_data.get("tech_tree", {})
        branch = interaction.namespace.branch
        results = []
        if branch:
            branch_data = tech_tree.get(branch, {})
            for sub_branch_data in branch_data.values():
                if isinstance(sub_branch_data, dict):
                    sub_branch_name = sub_branch_data.get("sub_branch_name")
                    if sub_branch_name and current.lower() in sub_branch_name.lower():
                        results.append(app_commands.Choice(name=sub_branch_name, value=sub_branch_name))
        else:
            for branch_data in tech_tree.values():
                for sub_branch_data in branch_data.values():
                    if isinstance(sub_branch_data, dict):
                        sub_branch_name = sub_branch_data.get("sub_branch_name")
                        if sub_branch_name and current.lower() in sub_branch_name.lower():
                            results.append(app_commands.Choice(name=sub_branch_name, value=sub_branch_name))
        return results[:25]

    async def autocomplete_my_country(self, interaction: discord.Interaction, current: str):
        countries = self.cold_war_data.get("countries", {})
        return [app_commands.Choice(name=c, value=c) for c in countries if (current.lower() in c.lower()) and (countries.get(c, {}).get("player_id")== interaction.user.id)][:25]
    
    def get_available_techs(self, branch: str, country_data: dict, tech_tree: dict):
        unlocked = country_data.get("research", {}).get("unlocked_techs", [])
        active = [
            data["tech"]
            for data in country_data.get("research", {}).get("active_slots", {}).values()
            if isinstance(data, dict) and "tech" in data
        ]
        available = []

        branch_data = tech_tree.get(branch, {})
        branch_starter = branch_data.get("branch", {}).get("starter_tech")
        if branch_starter and branch_starter not in unlocked and branch_starter not in active:
            available.append(branch_starter)
            return available

        for key, sub_branch in branch_data.items():
            if not isinstance(sub_branch, dict):
                continue

            starter = sub_branch.get("starter_tech")
            if starter and starter not in unlocked and starter not in active:
                available.append(starter)
                continue

            node = sub_branch.get("child")
            previous = None
            while node:
                tech = node.get("tech")
                if tech and tech not in unlocked and tech not in active:
                    parent = sub_branch.get("starter_tech") if previous is None else previous.get("tech")
                    if parent in unlocked:
                        available.append(tech)
                        break
                previous = node
                node = node.get("child")

        return available

    
    async def autocomplete_available_techs(self, interaction: discord.Interaction, current: str):
        branch = interaction.namespace.branch
        country = interaction.namespace.country

        if not branch:
            return []

        # Determine user’s country if not explicitly passed
        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict.get(str(interaction.user.id))
        elif not country:
            for c_key, details in self.cold_war_data["countries"].items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break

        if not country or country not in self.cold_war_data["countries"]:
            return []

        country_data = self.cold_war_data["countries"][country]
        tech_tree = self.cold_war_data.get("tech_tree", {})

        available = self.get_available_techs(branch, country_data, tech_tree)
        return [
            app_commands.Choice(name=t, value=t)
            for t in available if current.lower() in t.lower()
        ][:25]

        


    @app_commands.command(name="research_tech", description="Begin researching a tech.")
    @app_commands.autocomplete(country=autocomplete_my_country, branch=autocomplete_branch, tech_name=autocomplete_available_techs)
    async def research_tech(self, interaction: discord.Interaction, branch: str, tech_name: str, country: str = None, slot: int = None):
        await interaction.response.defer(thinking=True)

        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict.get(str(interaction.user.id))
        elif not country:
            for c_key, details in self.cold_war_data["countries"].items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break

        if not country or country not in self.cold_war_data["countries"]:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        country_data = self.cold_war_data["countries"][country]
        research = country_data.get("research", {})
        unlocked = research.get("unlocked_techs", [])
        active_slots = research.get("active_slots", {})
        carryover = research.get("carryover_days", {})
        year = self.cold_war_data.get("current_year", "1952")

        if slot is None:
            for k, v in active_slots.items():
                if v is None:
                    slot = int(k)
                    break
            if slot is None:
                return await interaction.followup.send("❌ No available research slots found.", ephemeral=True)

        slot = str(slot)
        if active_slots.get(slot):
            return await interaction.followup.send(f"❌ Slot {slot} is already occupied.", ephemeral=True)

        # Locate tech from available options
        tech_tree = self.cold_war_data.get("tech_tree", {})
        available_techs = self.get_available_techs(branch, country_data, tech_tree)

        if tech_name not in available_techs:
            return await interaction.followup.send(f"❌ `{tech_name}` is not currently researchable.", ephemeral=True)

        # Get the actual tech node for data lookup
        def find_tech_node(branch_data, name):
            for sb in branch_data.values():
                if not isinstance(sb, dict):
                    continue
                if sb.get("starter_tech") == name:
                    return sb
                node = sb.get("child")
                while node:
                    if node.get("tech") == name:
                        return node
                    node = node.get("child")
            return None

        target = find_tech_node(tech_tree.get(branch, {}), tech_name)
        if not target:
            return await interaction.followup.send("❌ Could not find that tech node.", ephemeral=True)

        base_time = target.get("research_time", 0)
        tech_year = target.get("research_year", int(year))

        # Calculate total bonus
        def calculate_total_bonus(branch_name: str, country_data: dict):
            generic_bonus = country_data.get("research", {}).get("research_bonus")
            bonus = generic_bonus
            for spirit in country_data.get("national_spirits", []):
                bonuses = spirit.get("research_bonus") or spirit.get("modifiers", {}).get("research_bonus", {})
                bonus += bonuses.get(branch_name.upper(), 0.0)
                bonus += bonuses.get("generic", 0.0)
            return bonus

        total_bonus = calculate_total_bonus(branch, country_data)
        adjusted_time = self.calculate_research_time(base_time, tech_year, year, total_bonus)
        carry_used = carryover.get(slot, 0)
        remaining_days = max(0, adjusted_time - carry_used)

        # Show confirmation embed and view
        embed = discord.Embed(
            title=f"Confirm Research Assignment",
            description=(
                f"🧪 **Tech:** `{tech_name}`\n"
                f"⏳ **Time Required:** {remaining_days} days\n"
                f"📦 **Slot:** {slot}\n"
                f"♻️ **Carryover Used:** {carry_used} days"
            ),
            color=discord.Color.teal()
        )

        view = ResearchConfirmView(
            interaction=interaction,
            country=country,
            slot=slot,
            tech_name=tech_name,
            remaining_days=remaining_days,
            carry_used=carry_used,
            data_ref=self.cold_war_data
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="view_slots", description="View which techs your country is currently researching.")
    @app_commands.autocomplete(country=autocomplete_my_country)
    async def view_slots(self, interaction: discord.Interaction, country: str = None):
        await interaction.response.defer(thinking=True)

        
        countries = self.cold_war_data.get("countries", {})

        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict[str(interaction.user.id)]
        elif not country:
            for c_key, details in countries.items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break

        if not country or country not in countries:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        data = countries[country]
        research = data.get("research", {})
        active_slots = research.get("active_slots", {})
        carryover = research.get("carryover_days", {})
        max_slots = research.get("research_slots", 1)

        embed = discord.Embed(
            title=f"🔬 {country} — Research Slots",
            description="Here's what you're currently researching.",
            color=discord.Color.green()
        )

        for i in range(1, max_slots + 1):
            slot_key = str(i)
            slot_data = active_slots.get(slot_key)
            carry = carryover.get(slot_key, 0)

            if isinstance(slot_data, dict) and "tech" in slot_data:
                tech = slot_data["tech"]
                remaining = slot_data.get("days_remaining", "???")
                embed.add_field(
                    name=f"📦 Slot {i}",
                    value=f"**{tech}**\n⏳ {remaining} days remaining\n♻️ {carry} rollover days",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"⚪ Slot {i}",
                    value=f"*Empty*\n♻️ {carry} rollover days",
                    inline=False
                )

        await interaction.followup.send(embed=embed, ephemeral=True)



    @app_commands.command(name="alternate_country", description="Switch which of your countries is active.")
    @app_commands.autocomplete(country=autocomplete_my_country)
    async def alternate_country(self, interaction: discord.Interaction, country: str):
        if country not in self.cold_war_data.get("countries", {}):
            return await interaction.response.send_message("Country not found.", ephemeral=True)
        self.alternate_country_dict[str(interaction.user.id)] = country
        await interaction.response.send_message(f"You are now viewing the game as **{country}**.", ephemeral=True)

    @app_commands.command(name="view_tech", description="View the Cold War RP tech tree.")
    @app_commands.autocomplete(branch=autocomplete_branch, sub_branch=autocomplete_sub_branch)
    async def view_tech(self, interaction: discord.Interaction, branch: str = None, sub_branch: str = None):
        await interaction.response.defer(thinking=True)

        tech_tree = self.cold_war_data.get("tech_tree", {})
        year = self.cold_war_data.get("current_year", "1952")

        user_id = str(interaction.user.id)
        if user_id in self.alternate_country_dict:
            country_name = self.alternate_country_dict[user_id]
        else:
            country_name = None
            for country_key, details in self.cold_war_data.get("countries", {}).items():
                if details.get("player_id") == interaction.user.id:
                    country_name = country_key
                    break
        if not country_name:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        country_data = self.cold_war_data["countries"].get(country_name, {})
        unlocked = country_data.get("research", {}).get("unlocked_techs", [])
        in_progress = dict(country_data.get("research", {}).get("active_slots"))
        generic_bonus = country_data.get("research", {}).get("research_bonus")

        def calculate_total_bonus(branch_name):
            bonus = generic_bonus
            for spirit in country_data.get("national_spirits", []):
                # Check both possible paths
                bonuses = spirit.get("research_bonus") or spirit.get("modifiers", {}).get("research_bonus", {})
                bonus += bonuses.get(branch_name.upper(), 0.0)
                bonus += bonuses.get("generic", 0.0)
            return bonus

        if not branch and not sub_branch:
            embed = discord.Embed(title="📚 Tech Tree Overview", color=discord.Color.blue())
            for branch_name, contents in tech_tree.items():
                subs = "\n".join([f"• {sub_data.get('sub_branch_name', sb)}" for sb, sub_data in contents.items() if sb != "branch"])
                embed.add_field(name=branch_name, value=subs or "(No sub-branches)", inline=False)
            return await interaction.followup.send(embed=embed)

        if branch and not sub_branch:
            branch_data = tech_tree.get(branch)
            if not branch_data:
                return await interaction.followup.send(f"Branch '{branch}' not found.", ephemeral=True)

            branch_info = branch_data.get("branch", {})
            starter_tech = branch_info.get("starter_tech")
            starter_desc = branch_info.get("description", "No description.")
            starter_time = branch_info.get("research_time", 0)
            starter_year = branch_info.get("research_year", "n/a")
            bonus = calculate_total_bonus(branch)
            bonus_summary = (
                f"{self.format_bonus(generic_bonus)} from generic bonus\n"
                f"{self.format_bonus(bonus - generic_bonus)} from national spirits\n"
                f"→ Effective bonus: {self.format_bonus(bonus)}"
            )
            adjusted_time = self.calculate_research_time(starter_time, starter_year, year, bonus)
            status = "✓" if starter_tech in unlocked else "🛠" if starter_tech in in_progress else " "
            label = (
                f"[{status}] {starter_tech} ({starter_year}) – {starter_time} → {adjusted_time} days"
                if adjusted_time != starter_time else
                f"[{status}] {starter_tech} ({starter_year}) – {starter_time} days"
            )

            starter_embed = discord.Embed(
                title=f"{branch_info.get('branch_name', branch)} Tech Tree",
                description="🔧 Research Speed Modifiers:\n" + bonus_summary,
                color=discord.Color.blue()
            )
            starter_embed.add_field(name=label, value=starter_desc, inline=False)

            if starter_tech not in unlocked:
                starter_embed.add_field(
                    name="🔒 Locked Branch",
                    value="More techs will become available once the branch starter tech is researched.",
                    inline=False
                )
                return await interaction.followup.send(embed=starter_embed)

            embeds = []
            for key, sub_data in branch_data.items():
                if key == "branch" or not isinstance(sub_data, dict):
                    continue
                bonus = calculate_total_bonus(branch)
                bonus_summary = f"{self.format_bonus(generic_bonus)} from generic bonus\n{self.format_bonus(bonus - generic_bonus)} from national spirits\n→ Effective bonus: {self.format_bonus(bonus)}"
                embeds.append(self.create_the_embed(sub_data, year, unlocked, in_progress, bonus, bonus_summary))
            return await interaction.followup.send(embeds=embeds[:10])

        for branch_name, contents in tech_tree.items():
            for sb_key, sub_data in contents.items():
                if sb_key == "branch" or not isinstance(sub_data, dict):
                    continue
                if sub_data.get("sub_branch_name", "").lower() == sub_branch.lower():
                    bonus = calculate_total_bonus(branch_name)
                    bonus_summary = f"{self.format_bonus(generic_bonus)} from generic bonus\n+{self.format_bonus(bonus - generic_bonus)}% from national spirits\n→ Effective bonus: +{self.format_bonus(bonus)}%"
                    embed = self.create_the_embed(sub_data, year, unlocked, in_progress, bonus, bonus_summary)
                    return await interaction.followup.send(embed=embed)

        await interaction.followup.send("❌ Could not find specified branch or sub-branch.", ephemeral=True)

    async def autocomplete_available_projects(self, interaction: discord.Interaction, current: str):
        country = interaction.namespace.country
        
        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict[str(interaction.user.id)]

        if not country:
            for c_key, details in self.cold_war_data["countries"].items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break

        if not country or country not in self.cold_war_data["countries"]:
            return []

        country_data = self.cold_war_data["countries"][country]
        active_projects = country_data.get("national_projects", {}).keys()

        # Static list of all projects — expand as needed
        all_projects = ["nuclear_weapons", "space_program"]

        available = [
            p for p in all_projects
            if p not in active_projects and current.lower() in p.lower()
        ]

        return [
            app_commands.Choice(name=p.replace("_", " ").title(), value=p)
            for p in available
        ][:25]


    @app_commands.command(name="start_project", description="Begin a high-level national project like nuclear weapons or space exploration.")
    @app_commands.autocomplete(country=autocomplete_my_country, project_name=autocomplete_available_projects)
    async def start_project(self, interaction: discord.Interaction, project_name: str, country: str = None):
        await interaction.response.defer(thinking=True)

        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict[str(interaction.user.id)]
        if not country:
            for c_key, details in self.cold_war_data["countries"].items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break

        if not country or country not in self.cold_war_data["countries"]:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        country_data = self.cold_war_data["countries"][country]
        np_data = country_data.setdefault("national_projects", {})

        if project_name in np_data:
            return await interaction.followup.send(f"❌ `{project_name}` is already in progress or completed.", ephemeral=True)

        # Tradeoff summary
        tradeoffs = {
            "nuclear_weapons": {
                "research_penalty": 0.05,
                "espionage_penalty": 10,
                "factory_penalty": 2
            },
            "space_program": {
                "research_penalty": 0.03,
                "budget_cost": 1,
                "factory_penalty": 1
            }
        }

        costs = tradeoffs.get(project_name, {})

        embed = discord.Embed(
            title=f"🧪 Start {project_name.replace('_', ' ').title()} Project?",
            description="Starting this national project will impose the following tradeoffs:",
            color=discord.Color.red()
        )

        if "research_penalty" in costs:
            embed.add_field(name="📉 Research Speed", value=f"-{int(costs['research_penalty'] * 100)}%", inline=False)
        if "espionage_penalty" in costs:
            embed.add_field(name="🕵️‍♂️ Domestic Intel Score", value=f"-{costs['espionage_penalty']}", inline=False)
        if "factory_penalty" in costs:
            embed.add_field(name="🏭 Industrial Sectors", value=f"-{costs['factory_penalty']}", inline=False)
        if "budget_cost" in costs:
            embed.add_field(name="💸 Budget Surplus", value=f"-{costs['budget_cost']} per turn", inline=False)

        embed.set_footer(text="Are you sure you want to begin this project?")

        view = StartProjectConfirmView(
            user_id=interaction.user.id,
            country=country,
            project_name=project_name,
            penalties=costs,
            data_ref=self.cold_war_data,
            save_callback=self.save_data
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="view_projects", description="View the status of your nation's strategic development projects.")
    @app_commands.autocomplete(country=autocomplete_my_country)
    async def view_projects(self, interaction: discord.Interaction, country: str = None):
        await interaction.response.defer(thinking=True)

        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict[str(interaction.user.id)]

        if not country:
            for c_key, details in self.cold_war_data["countries"].items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break

        if not country or country not in self.cold_war_data["countries"]:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        data = self.cold_war_data["countries"][country]
        projects = data.get("national_projects", {})
        all_defs = self.cold_war_data.get("NATIONAL PROJECTS", {})
        miles = all_defs.get("milestones", {})

        embed = discord.Embed(
            title=f"🔬 {country} – National Projects",
            description="Progress on major strategic programs:",
            color=discord.Color.purple()
        )

        if not projects:
            embed.description += "\n\n❌ No active or paused national projects."
            return await interaction.followup.send(embed=embed, ephemeral=True)

        for project_key, p_data in projects.items():
            project_lookup_key = project_key.lower().replace(" ", "_")
            milestone_defs = miles.get(project_lookup_key, {})

            status = p_data.get("status", "unknown")
            days = p_data.get("days_remaining", "—")
            completed = p_data.get("milestones_completed", [])

            # Convert milestone key to title
            milestone_title = "—"
            if status in milestone_defs:
                milestone_title = milestone_defs[status].get("name", "—")
            elif status == "paused_development":
                milestone_title = "Development Paused"

            summary = f"📍 **Status:** {milestone_title} (`{status}`)\n"
            if isinstance(days, int):
                summary += f"⏳ **Days remaining:** {days}\n"
            summary += f"✅ **Completed:** {', '.join(completed) if completed else 'None'}"

            name = "🧪 " + project_key.replace("_", " ").title()
            embed.add_field(name=name, value=summary, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


    
    def redact_paragraph_weighted(self, text, knowledge):
        words = text.split()
        redacted = []
        for word in words:
            clean = re.sub(r'[.,;!?()\"\']', '', word)
            is_proper = clean[:1].isupper()
            is_number = clean.isdigit() or re.match(r"\d{2,4}[hH]|\d{2,4}", clean)
            redact_chance = 100 - knowledge

            if is_proper or is_number:
                threshold = random.randint(0, 100)
                if threshold < redact_chance:
                    redacted.append("███████")
                    continue
            else:
                threshold = random.randint(0, 100)
                if threshold < redact_chance * 0.3:
                    redacted.append("███████")
                    continue
            redacted.append(word)

        # Join and collapse adjacent blocks of ███████ with no space
        paragraph = ' '.join(redacted)
        paragraph = re.sub(r'(█{3,})(\s+)(█{3,})', r'\1\3', paragraph)
        return paragraph
    
    def calculate_knowledge(self, viewer_data, target_data, target_name):
        spy_networks = viewer_data.get("espionage", {}).get("spy_networks", {})
        spy_score = spy_networks.get(target_name, 0)
        foreign = viewer_data.get("espionage", {}).get("foreign_intelligence_score", 0)
        domestic = target_data.get("espionage", {}).get("domestic_intelligence_score", 0)
        return max(10, (foreign + spy_score) - domestic)

    def get_best_intel_country(self, user_id, countries):
        options = [(name, data) for name, data in countries.items() if data.get("player_id") == user_id]
        if not options:
            return None
        return max(options, key=lambda x: x[1].get("espionage", {}).get("foreign_intelligence_score", 0) +
                                          x[1].get("espionage", {}).get("spy_network_score", 0))

    def redacted(self, text, knowledge, threshold=50):
        return text if knowledge >= threshold else self.redact_paragraph_weighted(text, knowledge)

    def ranged_value(self, actual, knowledge, stat_type="generic"):
        if knowledge >= 100:
            return str(actual)

        thresholds = {
            "population": (0.02, 40),
            "research": (None, 80),  # Show only if knowledge >= 80
            "military": (0.15, 30),
            "intel": (0.10, 50),
            "generic": (0.10, 50)
        }
        variance, redact_threshold = thresholds.get(stat_type, thresholds["generic"])

        if knowledge < redact_threshold:
            return random.choice(["Information Unclear", "**[REDACTED]**", "██████████"])

        if variance is None:
            return str(actual) if knowledge >= 100 else random.choice(["Information Unclear", "**[REDACTED]**", "██████████"])

        margin = max(1, int(actual * variance))
        low = max(0, actual - random.randint(0, margin))
        high = actual + random.randint(0, margin)
        estimate = f"{low}–{high}"
        if max(low, high) >= 1000000:
            formatted_estimate = self.pretty_number_range(low, high)
        else:
            formatted_estimate = self.clean_duplicate_ranges(estimate)
        
        return formatted_estimate
    
    def general_report(self, country: str, knowledge: int) -> str:
        agent = random.choice(["RAVEN-7", "WOLFHOUND", "WHISPER FLARE", "SHADOW ECHO"])
        if knowledge >= 90:
            return f"_Report received via Asset {agent}. Data believed accurate._\nOur operatives report near-complete visibility into {country}."
        elif knowledge >= 60:
            return f"_Report received via Asset {agent}. Source reliability: moderate._\nPartial visibility into {country}'s internal affairs. Data may be speculative."
        elif knowledge >= 30:
            return f"_Report received via Asset {agent}. Surveillance limited._\nMinimal intelligence retrieved from {country}. Further infiltration required."
        else:
            return f"_Report intercepted by {agent}. Subject heavily encrypted._\nOur agents failed to penetrate the intelligence sector of {country}. Greater resources necessary."

    def classify_stamp(self, knowledge: int):
        if knowledge >= 90:
            return "**// TOP SECRET //**\n**// EYES ONLY – DO NOT DISTRIBUTE //**"
        elif knowledge >= 60:
            return "**// RESTRICTED ACCESS //**"
        else:
            return "**// UNCONFIRMED FILES //**"

    def rotating_footer(self, knowledge: int):
        if knowledge >= 100:
            return "Compiled by the Office of the Secretary of State | Confidential – Authorized Personnel Only"
        return random.choice([
            "Compiled by Division 7 | Clearance: SIGINT-3",
            "Intercepted by Field Agent WOLFHOUND | Source not verified",
            "Retrieved from Cipher Channel 22–Delta | Clearance Level III"
        ]) + f" | Confidence Rating: {min(100, max(0, knowledge))}%"
    
    def clean_duplicate_ranges(self, text) -> str:
        return re.sub(r'\b(\d+)[–-]\1\b', r'\1', text)
    
    def pretty_number_range(self, low, high):
        def round_mil(n):
            return round(n / 100000) / 10
        
        if low == high:
            return f"{round_mil(low):.1f} million"
        else:
            return f"{round_mil(low):.1f}-{round_mil(high):.1f} million"

    @app_commands.command(name="view_country_info_detailed", description="View detailed info for a Cold War RP country.")
    @app_commands.autocomplete(country= autocomplete_country)
    async def view_country_info_detailed(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        cold_war_data = self.bot.get_cog("SpideyUtils").cold_war_data
        countries = cold_war_data.get("countries", {})
        target = countries.get(country)
        if not target:
            return await interaction.followup.send(f"❌ Country '{country}' not found.", ephemeral=True)

        is_owner = interaction.user.id == target.get("player_id")
        viewer_info = self.get_best_intel_country(interaction.user.id, countries)
        viewer_data = viewer_info[1] if viewer_info else None
        knowledge = 100 if is_owner else self.calculate_knowledge(viewer_data, target, country)

        embeds = []
        leader = target.get("leader", {})

        # OVERVIEW
        if is_owner:
            title = f"[GOVERNMENT FILE] – {country}"
        else:
            title = f"[CONFIDENTIAL DOSSIER] – {country}"

        footer_text = self.rotating_footer(knowledge)

        # OVERVIEW
        overview = discord.Embed(title=title, color=discord.Color.dark_blue())
        if not is_owner:
            overview.add_field(name=self.classify_stamp(knowledge), value=self.general_report(country, knowledge), inline=False)
        overview.description = self.redacted(target.get("details", "No description."), knowledge)
        overview.set_footer(text=footer_text)
        if target.get("image"):
            overview.set_image(url=target["image"])
        ideology = target.get("ideology", {})
        overview.add_field(name="Leading Ideology", value=ideology.get("leading_ideology", "Unknown"))
        overview.add_field(name="Doctrine", value=target.get("global", {}).get("doctrine_focus", "N/A"), inline=True)
        overview.add_field(name="Conscription", value=target.get("global", {}).get("conscription_policy", "N/A"), inline=True)
        embeds.append(overview)

        # LEADER
        leader_name = leader.get("name", "Unknown")
        leader_desc = []
        if not is_owner:
            leader_desc.append("// EYES ONLY - DO NOT DISTRIBUTE //")
        if leader.get("description"):
            leader_desc.append(self.redact_paragraph_weighted(leader.get("description"), knowledge))
        leader_img = leader.get("image", None)

        leader_description = "\n\n".join(leader_desc)

        if leader_name or leader_desc:
            leader_embed = discord.Embed(
                title=f"[CONFIDENTIAL] - EVAL. OF {leader_name.upper()}" if not is_owner else f"{leader_name} Profile",
                description=f"{leader_description}"
            )
            if leader_img:
                leader_embed.set_image(url=leader_img)
            embeds.append(leader_embed)

        # MILITARY
        m = target.get("military", {})
        mil = discord.Embed(title="🪖 Military Overview", color=discord.Color.red())
        for k, label in [("army_divisions", "Army Divisions"),
                         ("aviation_wings", "Aviation Wings"),
                         ("fleet_task_groups", "Fleet Task Groups"),
                         ("officer_skill_level", "Officer Skill Level"),
                         ("avg_troop_skill_level", "Troop Skill Level"),
                         ("military_readiness", "Readiness")]:
            value = m.get(k, 0 if "level" in k else "Unknown")
            stat_type = "military"
            if isinstance(value, int):
                mil.add_field(name=label, value=self.ranged_value(value, knowledge, stat_type))
            else:
                mil.add_field(name=label, value=self.redacted(value, knowledge))
        embeds.append(mil)

        # ECONOMY
        econ = target.get("economic", {})
        eco = discord.Embed(title="💰 Economic Overview", color=discord.Color.green())
        for k, label in [("budget_surplus", "Budget Surplus"),
                         ("industrial_sectors", "Industrial Sectors"),
                         ("oil_reserves", "Oil Reserves"),
                         ("infrastructure_rating", "Infrastructure")]:
            eco.add_field(name=label, value=self.ranged_value(econ.get(k, 0), knowledge))
        embeds.append(eco)

        # POLITICAL
        p = target.get("political", {})
        pol = discord.Embed(title="📊 Political/Demographic Overview", color=discord.Color.purple())
        for k, label in [("population", "Population"),
                         ("recruitable_manpower", "Recruitable Manpower"),
                         ("public_support_score", "Public Support"),
                         ("civil_unrest_level", "Civil Unrest")]:
            pol.add_field(name=label, value=self.ranged_value(p.get(k, 0), knowledge, "population" if k == "population" else "generic"))
        ideology_breakdown = target.get("ideology", {})
        for ideol in ["democratic", "fascist", "communist", "authoritarian", "monarchic"]:
            pol.add_field(name=f"{ideol.title()} Support", value=self.ranged_value(ideology_breakdown.get(ideol, 0), knowledge), inline=True)
        embeds.append(pol)

        # INTEL
        esp = target.get("espionage", {})
        intel = discord.Embed(title="🕵️ Intelligence & Research", color=discord.Color.greyple())
        intel.add_field(name="Research Coefficient", value=self.ranged_value(target.get("research", {}).get("research_coefficient", 0), knowledge, "research"))
        intel.add_field(name="Nuclear Arsenal", value=self.ranged_value(target.get("research", {}).get("nuclear_arsenal", 0), knowledge))
        intel.add_field(name="Foreign Intel Score", value=self.ranged_value(esp.get("foreign_intelligence_score", 0), knowledge, "intel"))
        intel.add_field(name="Domestic Intel Score", value=self.ranged_value(esp.get("domestic_intelligence_score", 0), knowledge, "intel"))
        intel.add_field(name="Spy Network Efficiency", value=self.ranged_value(esp.get("spy_network_score", 0), knowledge, "intel"))

        # NATIONAL SPIRITS
        spirits_data = target.get("national_spirits", [])
        if spirits_data:
            # Group spirits by type
            spirit_groups = defaultdict(list)
            for spirit in spirits_data:
                spirit_type = spirit.get("type", "misc").replace("_", " ").title()
                spirit_groups[spirit_type].append(spirit)

            for category, spirits in spirit_groups.items():
                embed = discord.Embed(
                    title=(f"[CONFIDENTIAL] – {category} National Spirits" if not is_owner else f"{category} National Spirits"),
                    color=discord.Color.teal()
                )

                if not is_owner:
                    embed.description = (
                        f"Our operatives suspect **{country}** maintains the following initiatives under **{category}**:\n"
                        f"Confidence Level: **{min(100, max(0, knowledge))}%**\n\n"
                        "// EYES ONLY – DO NOT DISTRIBUTE //"
                    )

                for spirit in spirits:
                    name = self.redacted(spirit.get("name", "Unknown"), knowledge) if not spirit.get("public") else spirit.get("name")
                    desc = self.redact_paragraph_weighted(spirit.get("description", "No description available."), (knowledge if not spirit.get("public") else (knowledge + 25)))
                    embed.add_field(name=f"**{name}**", value=desc, inline=False)

                embeds.append(embed)


        if esp.get("spy_networks") and knowledge >= 70:
            for tgt, val in esp.get("spy_networks", {}).items():
                intel.add_field(name=f"Network in {tgt}", value=self.ranged_value(val, knowledge, "intel"), inline=True)

        embeds.append(intel)

        await interaction.followup.send(embeds=embeds, ephemeral=True)

    async def autocomplete_espionage_actions(self, interaction: discord.Interaction, current:str):
        return [
            app_commands.Choice(name=operation.replace('_', ' ').title(), value=operation)
            for operation in self.cold_war_data.get("ESPIONAGE").get("operations").keys()
        ][:25]
    

    @app_commands.command(name="assign_spy", description="Assign a spy operation to a target country.")
    @app_commands.describe(
        country="Your country",
        target="Target country to spy on",
        operation="Espionage operation to assign",
        ideology="(If required) Ideology to sway toward",
        project="(If required) Project to monitor"
    )
    @app_commands.autocomplete(country=autocomplete_my_country, target=autocomplete_country, operation=autocomplete_espionage_actions)
    @app_commands.choices(
        ideology=[
            app_commands.Choice(name="Democratic", value="democratic"),
            app_commands.Choice(name="Fascist",    value="fascist"),
            app_commands.Choice(name="Communist",  value="communist"),
            app_commands.Choice(name="Authoritarian", value="authoritarian"),
            app_commands.Choice(name="Monarchic",  value="monarchic")
        ],
        project=[
            app_commands.Choice(name="Nuclear Weapons", value="nuclear_weapons"),
            app_commands.Choice(name="Space Program",    value="space_program")
        ]
    )
    async def assign_spy(
        self,
        interaction: Interaction,
        target: str,
        operation: str,
        country: str = None,
        ideology: str = None,
        project: str = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # ── Resolve acting country ──
        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict[str(interaction.user.id)]
        if not country:
            for c_key, det in self.cold_war_data["countries"].items():
                if det.get("player_id") == interaction.user.id:
                    country = c_key
                    break
        if not country or country not in self.cold_war_data["countries"]:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        # ── Validate target & operation ──
        if target not in self.cold_war_data["countries"]:
            return await interaction.followup.send("❌ Target country not found.", ephemeral=True)
        op_data = self.cold_war_data.get("ESPIONAGE", {}).get("operations", {}).get(operation)
        if not op_data:
            return await interaction.followup.send("❌ Unknown espionage operation.", ephemeral=True)

        # ── Parameter checks ──
        missing = []
        for p in op_data.get("parameters", []):
            if p == "ideology" and not ideology: missing.append("ideology")
            if p == "project"  and not project:  missing.append("project")
        if missing:
            return await interaction.followup.send(
                f"❌ Missing required parameter(s): {', '.join(missing)}",
                ephemeral=True
            )

        # ── Prepare confirmation ──
        leader = self.cold_war_data["countries"][target].get("leader", {}).get("name", "<leader>")
        desc = op_data["description"].format(
            country=country,
            target=target,
            leader=leader,
            ideology=ideology  or "<ideology>",
            project=project   or "<project>"
        )
        embed = Embed(
            title="🕵️ Confirm Espionage Operation",
            description=(
                f"**Operator:** {country}\n"
                f"**Target:** {target}\n"
                f"**Operation:** {operation.replace('_',' ').title()}\n\n"
                f"**Details:** {desc}\n\n"
                f"**Requires:** {op_data.get('required_operatives',1)} operatives, "
                f"network ≥ {op_data['network_requirement']}"
            ),
            color=discord.Color.dark_purple()
        )

        params = {}
        if ideology: params["ideology"] = ideology
        if project:  params["project"]  = project

        view = ConfirmSpyAssignView(self, country, target, operation, op_data, params)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="spy_hq", description="View your espionage headquarters and operational status.")
    @app_commands.autocomplete(country=autocomplete_my_country)
    async def spy_hq(self, interaction: discord.Interaction, country: str = None):
        await interaction.response.defer(ephemeral=True)

        # Resolve country
        if not country and str(interaction.user.id) in self.alternate_country_dict:
            country = self.alternate_country_dict[str(interaction.user.id)]
        if not country:
            for c_key, details in self.cold_war_data["countries"].items():
                if details.get("player_id") == interaction.user.id:
                    country = c_key
                    break
        if not country or country not in self.cold_war_data["countries"]:
            return await interaction.followup.send("❌ Could not determine your country.", ephemeral=True)

        # Init and pull data
        self.init_spy_data(country)
        esp = self.cold_war_data["countries"][country]["espionage"]
        total_ops = esp.get("total_operatives", 0)
        free_ops = esp.get("operatives_available", 0)
        assigned = esp.get("assigned_ops", {})
        # recompute “used” operatives from assignments
        used_ops = sum(
            op_defs.get(op_name, {}).get("required_operatives", 1)
            for tgt, ops in assigned.items()
            for op_name in ops
        )
        free_ops = max(0, total_ops - used_ops)
        spy_nets = esp.get("spy_networks", {})
        op_defs = self.cold_war_data.get("ESPIONAGE", {}).get("operations", {})

        embeds = []

        # 🕵️ Headquarters Overview
        main = discord.Embed(
            title="🕵️ Espionage Headquarters",
            description="`// CONFIDENTIAL - DO NOT COPY //`\n`// FOR EYES ONLY //`",
            color=discord.Color.dark_purple()
        )
        main.add_field(name="Total Field Operatives", value=str(total_ops))
        main.add_field(name="Unassigned Operatives", value=str(free_ops), inline=True)
        # list assignments you could launch right now
        avail = []
        for key, op in op_defs.items():
            req_net = op.get("network_requirement", 0)
            req_ops = op.get("required_operatives", 1)
            if free_ops >= req_ops:
                avail.append(f"• {key.replace('_',' ').title()} — network ≥ {req_net}")
        if avail:
            main.add_field(name="Available Assignments", value="\n".join(avail), inline=False)

        main.set_footer(text=f"---\nProduct of the Intelligence Agency of {country}.\nInternal Use Only!\n---")
        embeds.append(main)

        # 🎯 Per-country briefs
        tracked = set(spy_nets) | set(assigned)
        for tgt in sorted(tracked, key=lambda c: spy_nets.get(c, 0), reverse=True):
            net = spy_nets.get(tgt, 0)
            ops = assigned.get(tgt, {})

            e = discord.Embed(
                title=f"🎯 {tgt}",
                description="`// CONFIDENTIAL - DO NOT COPY //`\n`// CLASSIFIED INTELLIGENCE - FOR EYES ONLY //`",
                color=discord.Color.blurple()
            )
            e.add_field(name="Spy Network", value=str(net), inline=True)

            # Active missions
            if ops:
                lines = []
                for name, params in ops.items():
                    if isinstance(params, dict):
                        pstr = ", ".join(f"{k}: {v}" for k,v in params.items())
                        lines.append(f"• {name.replace('_',' ').title()} ({pstr})")
                    else:
                        lines.append(f"• {name.replace('_',' ').title()}")
                e.add_field(name="Active Missions", value="\n".join(lines), inline=False)
            else:
                e.add_field(name="Active Missions", value="*None*", inline=False)

            # Eligible Operations with real leader names
            eligible = []
            for key, op in op_defs.items():
                req_net = op.get("network_requirement", 0)
                req_ops = op.get("required_operatives", 1)
                if free_ops >= req_ops and net >= req_net:
                    # fetch real leader for this target
                    leader_name = (
                        self.cold_war_data["countries"]
                            .get(tgt, {})
                            .get("leader", {})
                            .get("name", "<leader>")
                    )
                    desc = op["description"].format(
                        country=tgt,
                        project="<project>",
                        ideology="<ideology>",
                        leader=leader_name
                    )
                    eligible.append(f"• {key.replace('_',' ').title()} — {desc}")

            e.add_field(
                name="Eligible Operations",
                value="\n".join(eligible) or "*None*",
                inline=False
            )
            e.set_footer(text=f"---\nProduct of the Intelligence Agency of {country}.\nInternal Use Only\n---")

            embeds.append(e)

        await interaction.followup.send(embeds=embeds, ephemeral=True)



    
    @app_commands.command(name="view_country_info", description="View basic public information about a Cold War RP country.")
    @app_commands.autocomplete(country=autocomplete_country)
    async def view_country_info(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer(thinking=True,ephemeral=False)
        
        data = self.bot.get_cog("SpideyUtils").cold_war_data
        countries = data.get("countries", {})
        info = countries.get(country)
        if not info:
            return await interaction.followup.send(f"❌ Country '{country}' not found.", ephemeral=True)

        global_data = info.get("global", {})
        ideology = info.get("ideology", {})
        leader = info.get("leader", {})

        # Basic Info Embed
        embed = discord.Embed(
            title=f"📋 Bureau of Global Intelligence – Summary Report",
            description=info.get("public_desc", "No public information available."),
            color=discord.Color.blue()
        )
        embed.set_author(name=f"Filed under: Public Record – {country}")

        embed.add_field(name="Ideology", value=ideology.get("leading_ideology", "Unknown"))
        embed.add_field(name="Doctrine", value=global_data.get("doctrine_focus", "Unknown"), inline=True)
        embed.add_field(name="Conscription", value=global_data.get("conscription_policy", "Unknown"), inline=True)

        if info.get("image"):
            embed.set_image(url=info["image"])
        
        embed.set_footer(text="United Nations' Materials | Not for Public Distribution")

        # Leader Embed
        leader_embed = discord.Embed(
            title=f"{country}'s Leader",
            description=leader.get("name", "Unknown"),
            color=discord.Color.dark_gold()
        )
        if leader.get("image"):
            leader_embed.set_image(url=leader["image"])

        # National Spirits (public only)
        spirits_data = info.get("national_spirits", [])
        public_spirits = [s for s in spirits_data if s.get("public")]

        spirit_embed = discord.Embed(
            title=f"🕊️ National Spirits",
            color=discord.Color.teal()
        )

        spirit_embed.set_footer(text="United Nations' Advisory Committee Report | Not to be treated as factual")

        if len(public_spirits) == 0:
            summary = f"The UN advisory report lacks any knowledge of {country}'s internal or foreign policy goals. Please contact the Secretary of State's Office of {country} or visit the {country} Embassy in your nation to lodge a diplomatic decree."
        elif len(public_spirits) <= 2:
            summary = f"The UN advisory report does not encapsulate all of {country}'s spirits. The committee has compiled some of the publicly available ones."
        else:
            summary = f"The UN advisory report has a compilation of most all of {country}'s spirit."

        if public_spirits:
            spirit_names = "\n".join(f"• {s['name']}" for s in public_spirits)
            spirit_embed.description = f"{summary}\n\n{spirit_names}"
        else:
            spirit_embed.description = summary

        await interaction.followup.send(embeds=[embed, leader_embed, spirit_embed], ephemeral=False)


    
    @app_commands.command(name="setturn", description="Set the current in-game turn, year, and day.")
    @app_commands.describe(turn="The current turn number", year="The in-game year", day="The sub-division of the year (1–2 or 1–3)")
    async def setturn(self, interaction: discord.Interaction, turn: int, year: str, day: int):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        # Set values in modifiers
        self.cold_war_data["turn"] = turn
        self.cold_war_data["current_year"] = year
        self.cold_war_data["day"] = day

        # Run all background systems (espionage resolution, regen, etc.)
        await self.run_turn_tick()

        self.save_data()

        await interaction.response.send_message(
            f"🕰️ Turn updated to Turn {turn}, Year {year}, Day {day}. Background actions processed.",
        ephemeral=True
        )

    @app_commands.command(name="reset_data", description="(Owner only) Reset turn/year and scrub stray {target} entry from Spain.")
    @commands.is_owner()
    async def reset_data(self, interaction: Interaction):
        """Resets turn to 0, year to 1952, day to 1, and removes '{target}' from Spain's spy_networks."""
        # load the existing dynamic file
        try:
            with open(dynamic_path, "r") as f:
                dyn = json.load(f)
        except FileNotFoundError:
            return await interaction.response.send_message("❌ No modifiers file found.", ephemeral=True)

        # reset turn counters
        dyn["turn"] = 0
        dyn["current_year"] = 1952
        dyn["day"] = 1

        # remove the bad key under Spain
        spain = dyn.get("countries", {}).get("Kingdom of Spain", {})
        spy_nets = spain.get("espionage", {}).get("spy_networks", {})
        if "{target}" in spy_nets:
            spy_nets.pop("{target}")

        # write it back out
        with open(dynamic_path, "w") as f:
            json.dump(dyn, f, indent=2)

        # reload into memory
        self.load_data()

        await interaction.response.send_message(
            "✅ Data reset: turn=0, year=1952, day=1, stray `{target}` removed.",
            ephemeral=True
        )



    @commands.command()
    @commands.has_permissions(administrator=True)
    async def embed(self, ctx):
        """Interactive embed builder."""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("📝 What's the **title** of your post?")
        title = (await self.bot.wait_for("message", check=check)).content

        await ctx.send("🗒️ What's the **main description**?")
        description = (await self.bot.wait_for("message", check=check)).content

        await ctx.send("🖼️ Thumbnail URL? (Paste a link or type `no`)")
        thumbnail = (await self.bot.wait_for("message", check=check)).content
        thumbnail = thumbnail if thumbnail.lower() != "no" else None

        await ctx.send("🖼️ Main image URL? (Paste a link or type `no`)")
        image = (await self.bot.wait_for("message", check=check)).content
        image = image if image.lower() != "no" else None

        await ctx.send("📦 How many **additional fields** do you want to add?")
        try:
            num_fields = int((await self.bot.wait_for("message", check=check)).content)
        except ValueError:
            return await ctx.send("⚠️ Invalid number. Cancelling.")

        fields = []
        for i in range(num_fields):
            await ctx.send(f"🧷 Name of **field {i+1}?**")
            name = (await self.bot.wait_for("message", check=check)).content

            await ctx.send(f"✏️ Value of **field {i+1}?**")
            value = (await self.bot.wait_for("message", check=check)).content

            await ctx.send(f"📐 Should **field {i+1}** be inline? Type `True` or `False`")
            inline_input = (await self.bot.wait_for("message", check=check)).content.lower()
            inline = inline_input == "true"

            fields.append({"name": name, "value": value, "inline": inline})

        await ctx.send("📢 What channel should this be posted in? Mention it (e.g., #announcements)")
        channel_msg = await self.bot.wait_for("message", check=check)
        channel = channel_msg.channel_mentions[0] if channel_msg.channel_mentions else None
        if not channel:
            return await ctx.send("⚠️ Couldn't find that channel. Cancelling.")

        embed_obj = discord.Embed(title=title, description=description, color=discord.Color.dark_gray())
        if thumbnail:
            embed_obj.set_thumbnail(url=thumbnail)
        if image:
            embed_obj.set_image(url=image)

        for field in fields:
            embed_obj.add_field(name=field["name"], value=field["value"], inline=field["inline"])

        await ctx.send("✅ Ready to send this embed? Type `yes` or `no`")
        confirm = (await self.bot.wait_for("message", check=check)).content.lower()
        if confirm != "yes":
            return await ctx.send("❌ Embed cancelled.")

        await channel.send(embed=embed_obj)
        await ctx.send(f"📨 Embed sent to {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setuprp(self, ctx, rp_name: str, time_period: str, *, description: str):
        """Set up a new RP campaign."""
        filename = f"{rp_name.replace(' ', '_').lower()}.json"
        filepath = os.path.join(BASE_DIR, filename)
        os.makedirs(BASE_DIR, exist_ok=True)
        rp_structure = {
            "rp_name": rp_name,
            "time_period": time_period,
            "description": description,
            "global_history": {},
            "countries": {}
        }
        with open(filepath, "w") as f:
            json.dump(rp_structure, f, indent=4)
        await ctx.send(f"RP '{rp_name}' has been set up successfully.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def gmroll(self, ctx, base: int = 100, modifier: int = 0, target: discord.Member = None, *, reason: str = "No reason provided"):
        """
        Rolls a die (default 1d100), applies a modifier, and sends the results.
        Optionally, target a user to DM the result. This is intended for GM use.
        
        Example: [p]gmroll 100 -20 @User Suppression of rebels
        """
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # Prompt for modifier summary
        await ctx.send("Would you like to include a modifier summary for this roll? Type your summary or `no` to skip.")
        try:
            mod_summary_msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            mod_summary = None
        else:
            if mod_summary_msg.content.lower() != "no":
                mod_summary = mod_summary_msg.content
            else:
                mod_summary = None

        # Perform the roll
        base_roll = random.randint(1, base)
        final_result = base_roll + modifier

        # Clamp final result between 1 and base (optional)
        final_result = max(1, min(final_result, base))

        # Determine outcome category (adjust thresholds as needed)
        if final_result >= 85:
            outcome = "Great Success"
        elif final_result >= 70:
            outcome = "Success"
        elif final_result >= 55:
            outcome = "Success at Great Cost"
        elif final_result >= 45:
            outcome = "Stalemate"
        else:
            outcome = "Failure"

        # Build the result message
        result_text = (
            f"**Roll for:** {reason}\n"
            f"**Base Roll:** {base_roll}\n"
            f"**Modifier:** {modifier}\n"
            f"**Final Result:** {final_result} → {outcome}"
        )
        if mod_summary:
            result_text += f"\n**Modifier Summary:** {mod_summary}"

        # Determine target user: if no target provided, use the invoker
        if not target:
            target = ctx.author

        # DM the result to the target user
        try:
            await target.send(result_text)
        except Exception as e:
            await ctx.send(f"Could not send DM to {target.mention}: {e}")

        # Also post the result in the current (GM) channel
        await ctx.send(f"Roll result for {target.mention}:\n{result_text}")
    
    
    
    @app_commands.command(name="viewrequests", description="View all roll requests categorized by status.")
    async def viewrequests(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        filepath = "roll_requests.json"
        if not os.path.exists(filepath):
            return await interaction.response.send_message("No requests found.", ephemeral=True)

        with open(filepath, "r") as f:
            requests = json.load(f)

        pending = [r for r in requests if r["status"] == "need_gm_evaluation"]
        resolved = [r for r in requests if r["status"] == "need_player_implementation"]

        def build_embed(title, reqs, color):
            embed = discord.Embed(title=title, color=color)
            if not reqs:
                embed.description = "No requests."
                return embed
            for r in reqs:
                embed.add_field(
                    name=f"{r['username']} ({r['channel']})",
                    value=(
                        f"**Reason:** {r['reason']}\n"
                        f"**Modifier:** {r['modifier']}\n"
                        f"🕰️ Turn {r['game_turn']} ({r['game_year']})\n"
                        f"⏱️ {r['timestamp']} UTC"
                    ),
                    inline=False
                )
            return embed

        await interaction.response.send_message(embeds=[
            build_embed("🕵️ Requests Needing GM Evaluation", pending, discord.Color.gold()),
            build_embed("📌 Requests Needing Player Implementation", resolved, discord.Color.green())
        ], ephemeral=True)


    async def get_user_choices(self, interaction: discord.Interaction, current: str):
        if not os.path.exists("roll_requests.json"):
            return []
        with open("roll_requests.json", "r") as f:
            requests = json.load(f)

        seen = set()
        return [
            app_commands.Choice(name=req["username"], value=req["username"])
            for req in reversed(requests)
            if req["status"] != "archived" and req["username"] not in seen and not seen.add(req["username"])
            and current.lower() in req["username"].lower()
        ][:25]

    @app_commands.command(name="change")
    async def change_status(self, interaction: discord.Interaction,
                            username: app_commands.Transform[str, app_commands.Transformer()],
                            new_status: app_commands.Choice[str]):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        valid_statuses = ["need_gm_evaluation", "need_player_implementation", "archived"]
        filepath = "roll_requests.json"
        if not os.path.exists(filepath):
            return await interaction.response.send_message("⚠️ No requests found.", ephemeral=True)

        with open(filepath, "r") as f:
            requests = json.load(f)

        matched = None
        for r in reversed(requests):
            if username.lower() in r["username"].lower():
                matched = r
                break

        if not matched:
            return await interaction.response.send_message("⚠️ No matching request found.", ephemeral=True)

        matched["status"] = new_status.value
        with open(filepath, "w") as f:
            json.dump(requests, f, indent=2)

        await interaction.response.send_message(f"✅ Updated request from **{matched['username']}** to **{new_status.value}**.", ephemeral=True)

    @change_status.autocomplete("username")
    async def username_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.get_user_choices(interaction, current)

    @app_commands.choices(new_status=[
        app_commands.Choice(name="Needs GM Evaluation", value="need_gm_evaluation"),
        app_commands.Choice(name="Needs Player Implementation", value="need_player_implementation"),
        app_commands.Choice(name="Archived", value="archived")
    ])
    async def new_status_autocomplete(self, interaction: discord.Interaction, current: str):
        pass





    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addcountrytorp(self, ctx, rp_name: str, country_name: str, *, details: str):
        """
        [Admin] Add a country to an RP campaign.
        Details is a string containing key info (e.g., "leader: None; ideology: authoritarian; stability: low; ...")
        """
        filename = f"{rp_name.replace(' ', '_').lower()}.json"
        filepath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(filepath):
            return await ctx.send("RP not found. Please set up the RP first using [p]setuprp.")
        with open(filepath, "r") as f:
            rp_data = json.load(f)
        if "countries" not in rp_data:
            rp_data["countries"] = {}
        rp_data["countries"][country_name] = {
            "leader": None,
            "details": details,
            "military": {},
            "economic": {},
            "political": {},
            "research": {},
            "country_history": {},
            "past_turns": {}
        }
        with open(filepath, "w") as f:
            json.dump(rp_data, f, indent=4)
        await ctx.send(f"Country **{country_name}** added to RP **{rp_name}**.")

    @commands.command()
    async def inputrpdata(self, ctx, private: bool = False):
        """Interactive command to input RP data (military, economic, research, political)."""
        # Placeholder: This command will walk you through prompts to input your nation's data
        await ctx.send("This command is under development. Stay tuned for updates!")

