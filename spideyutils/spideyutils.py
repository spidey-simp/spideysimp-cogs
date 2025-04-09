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

    @app_commands.command(name="view_history", description="View the global timeline or a specific country's history.")
    @app_commands.describe(country="Choose a country or leave blank for global", global_view="Toggle to view global history")
    @app_commands.autocomplete(country=autocomplete_country)
    async def view_history(self, interaction: discord.Interaction, country: str = None, global_view: bool = False):
        await interaction.response.defer(thinking=True, ephemeral=True)


        embed = discord.Embed(color=discord.Color.blue())

        if not self.cold_war_data:
            embed.title = "⚠️ Data Load Error"
            embed.description = "`cold_war.json` failed to load or is empty. Please check the file path or syntax."
            return await interaction.followup.send(embed=embed, ephemeral=True)

        if global_view:
            global_history = self.cold_war_data.get("global_history", {})
            embed.title = "🗳️ Global History Timeline"
            for year in sorted(global_history.keys()):
                events = global_history[year]
                if isinstance(events, dict):
                    desc_lines = [f"**{headline}**\n{content['description']}" for headline, content in events.items()]
                    embed.add_field(name=f"__**{year}**__", value="\n\n".join(desc_lines), inline=False)
        elif country:
            country_data = self.cold_war_data.get("countries", {}).get(country)
            if not country_data:
                return await interaction.followup.send(f"⚠️ Country '{country}' not found.", ephemeral=True)
            history = country_data.get("country_history", {})
            embed.title = f"📜 {country} – National History"
            for year in sorted(history.keys()):
                entry = history[year]
                if isinstance(entry, list):
                    embed.add_field(name=f"__**{year}**__", value="\n".join(f"- {e}" for e in entry), inline=False)
                else:
                    embed.add_field(name=f"__**{year}**__", value=entry, inline=False)
        else:
            return await interaction.followup.send("⚠️ You must specify either a country or set global_view=True.", ephemeral=True)

        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="view_country_info", description="View basic public information about a Cold War RP country.")
    @app_commands.autocomplete(country=autocomplete_country)
    async def view_country_info(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        country_data = self.cold_war_data.get("countries", {}).get(country)
        if not country_data:
            return await interaction.followup.send(f"⚠️ Country '{country}' not found.", ephemeral=True)

        leader = country_data.get("leader", {})
        ideology = country_data.get("ideology", {})
        global_info = country_data.get("global", {})
        spirits = country_data.get("national_spirits", [])

        embed = discord.Embed(
            title=f"{country} – Public Overview",
            description=country_data.get("details", "No description available."),
            color=discord.Color.gold()
        )

        if leader.get("name"):
            embed.set_author(name=f"Leader: {leader['name']}", icon_url=leader.get("image", discord.Embed.Empty))
        if country_data.get("image"):
            embed.set_image(url=country_data["image"])

        if ideology:
            leading = ideology.get("leading_ideology", "Unknown")
            embed.add_field(name="Leading Ideology", value=leading, inline=True)

        doctrine = global_info.get("doctrine_focus", "N/A")
        conscription = global_info.get("conscription_policy", "N/A")
        embed.add_field(name="Doctrine Focus", value=doctrine, inline=True)
        embed.add_field(name="Conscription Policy", value=conscription, inline=True)

        if spirits:
            spirit_summaries = [f"**{sp['name']}**: {sp['description']}" for sp in spirits]
            joined = "\n\n".join(spirit_summaries)
            embed.add_field(name="National Spirits", value=joined[:1024], inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    
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

