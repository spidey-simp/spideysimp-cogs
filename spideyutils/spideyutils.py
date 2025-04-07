import discord
from discord.ext import commands
import json
import os
import random
import asyncio

BASE_DIR = "/mnt/data/rpdata"

class SpideyUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        embed_obj = discord.Embed(title=title, description=description, color=discord.Color.blurple())
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

