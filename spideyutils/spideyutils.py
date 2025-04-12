import discord
from discord import app_commands
from discord.ext import commands
from discord import Interaction
from redbot.core import commands
import json
import os
import random
import asyncio
import datetime
import re
from collections import defaultdict

BASE_DIR = "/mnt/data/rpdata"


file_path = os.path.join(os.path.dirname(__file__), "cold_war.json")




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



class SpideyUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cold_war_data = {}
        self.load_data()

    
    def load_data(self):
        try:
            with open(file_path, "r") as f:
                self.cold_war_data = json.load(f)
        except Exception as e:
            print("Failed to load cold_war.json:", e)

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
    
    def calculate_research_time(self, base_time, research_year, current_year):
        penalty = 0
        if research_year and int(current_year) < int(research_year):
            ahead = int(research_year) - int(current_year)
            penalty = int(base_time * (0.2 * ahead))
        return base_time + penalty

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

    def add_tech_with_children(self, embed, tech_name, data, year):
        if not isinstance(data, dict):
            return
        base = data.get("research_time", 0)
        r_year = data.get("research_year", None)
        desc = data.get("description", "No description.")
        calc_time = self.calculate_research_time(base, r_year, year)
        label = f"**{tech_name} ({r_year or 'n/a'}) – {calc_time} days**"
        embed.add_field(name=label, value=desc, inline=False)
        if "child" in data:
            for child_tech_name, child_data in data["child"].items():
                self.add_tech_with_children(embed, child_tech_name, child_data, year)

    @app_commands.command(name="view_tech", description="View the Cold War RP tech tree.")
    @app_commands.autocomplete(branch=autocomplete_branch, sub_branch=autocomplete_sub_branch)
    async def view_tech(self, interaction: discord.Interaction, branch: str = None, sub_branch: str = None):
        await interaction.response.defer(thinking=True)

        tech_tree = self.cold_war_data.get("tech_tree", {})
        year = self.cold_war_data.get("current_year", "1952")

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

            embeds = []
            for key, sub_data in branch_data.items():
                if key == "branch" or not isinstance(sub_data, dict):
                    continue
                sub_name = sub_data.get("sub_branch_name", key)
                sub_embed = discord.Embed(title=f"📦 {sub_name} Sub-Branch", color=discord.Color.gold())
                tech_name = sub_data.get("starter_tech")
                self.add_tech_with_children(sub_embed, tech_name, sub_data, year)
                embeds.append(sub_embed)
            return await interaction.followup.send(embeds=embeds[:10])

        for branch_name, contents in tech_tree.items():
            for sb_key, sub_data in contents.items():
                if sb_key == "branch" or not isinstance(sub_data, dict):
                    continue
                if sub_data.get("sub_branch_name", "").lower() == sub_branch.lower():
                    embed = discord.Embed(title=f"🔬 {sub_data['sub_branch_name']} Sub-Branch", color=discord.Color.blurple())
                    tech_name = sub_data.get("starter_tech")
                    self.add_tech_with_children(embed, tech_name, sub_data, year)
                    return await interaction.followup.send(embed=embed)

        await interaction.followup.send("❌ Could not find specified branch or sub-branch.", ephemeral=True)




    
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


    
    @app_commands.command(name="setturn", description="Set the current in-game turn and year.")
    async def setturn(self, interaction: discord.Interaction, turn: int, year: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        data = {"turn": turn, "year": year}
        with open("current_turn.json", "w") as f:
            json.dump(data, f)
        await interaction.response.send_message(f"🕰️ Turn updated to Turn {turn}, Year {year}.", ephemeral=True)


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

