import discord
from redbot.core import commands, Config
from discord.ext import tasks, app_commands
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

tzs_accepted = {
    "UTC": "Coordinated Universal Time",
    "America/Los_Angeles": "Pacific Time (US & Canada)",
    "America/New_York": "Eastern Time (US & Canada)",
    "Europe/London": "Greenwich Mean Time / British Time",
    "Europe/Berlin": "Central European Time",
    "Asia/Tokyo": "Japan Standard Time",
}


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

class QOTDModal(discord.ui.Modal, title="Upload Questions of the Day"):
    def __init__(self, cog: "SpideyServerTools"):
        super().__init__()
        self.cog = cog
        self.questions = discord.ui.TextInput(
            label="Questions",
            placeholder="Separate questions with a ; if multiple",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.questions)

    async def on_submit(self, interaction: discord.Interaction):
        parts = [q.strip() for q in self.questions.value.split(";")]
        questions = [q for q in parts if q]

        if not questions:
            await interaction.response.send_message("No valid questions provided.", ephemeral=True)
            return

        uid = str(interaction.user.id)
        store = self.cog.settings.setdefault("qotd_questions", {})
        bank = store.setdefault(uid, [])
        bank.extend(questions)

        save_settings(self.cog.settings)

        await interaction.response.send_message(
            f"Stored **{len(questions)}** question(s) under your bank.",
            ephemeral=True
        )


class SpideyServerTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = load_settings()
        self.qotd_task.start()
    

    def cog_unload(self):
        save_settings(self.settings)
        self.qotd_task.cancel()

    @tasks.loop(hours=1)
    async def qotd_task(self):
        channel_id = self.settings.get("qotd_channel")
        tzname = self.settings.get("timezone", "UTC")
        hour = self.settings.get("qotd_hour", 0)
        if not channel_id or hour is None:
            return

        # timezone-aware now
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo("UTC")
        now = datetime.now(tz)

        # ledger: once per local calendar day
        today_key = now.date().isoformat()
        last_key = self.settings.get("qotd_last_ran")
        if last_key == today_key:
            return

        # target time today in that tz
        target = now.replace(hour=int(hour), minute=0, second=0, microsecond=0)

        # only run if at/after target (catch-up if bot was down)
        if now < target:
            return

        # resolve forum channel
        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if not isinstance(channel, discord.ForumChannel):
            # safety: if someone misconfigured the channel, bail quietly
            return

        # build a (uid, idx, question) pool across all contributors
        bank = self.settings.get("qotd_questions", {})
        triples = [
            (uid, i, q.strip())
            for uid, qs in bank.items()
            for i, q in enumerate(qs)
            if q and q.strip()
        ]
        if not triples:
            return

        # choose one and POP it to avoid repeats
        uid, q_index, question = random.choice(triples)
        # pop from the original list so it's removed permanently
        chosen_list = bank.get(uid, [])
        if not chosen_list or q_index >= len(chosen_list):
            return  # defensive: list changed since we built the pool

        popped = chosen_list.pop(q_index)  # remove it
        if not chosen_list:
            # if this uploader has no questions left, clean up their key
            bank.pop(uid, None)

        # resolve the author (for embed author credit)
        author = self.bot.get_user(int(uid))
        author_name = author.display_name if author else "Unknown"
        author_icon = author.display_avatar.url if author else None

        title = f"QOTD - {now.strftime('%Y-%m-%d')}"
        embed = discord.Embed(description=question)
        embed.set_author(name=author_name, icon_url=author_icon)

        # create the forum post (thread) with the embed
        await channel.create_thread(name=title[:90], content=None, embeds=[embed])

        # mark done & persist the popped state
        self.settings["qotd_last_ran"] = today_key
        save_settings(self.settings)



    @qotd_task.before_loop
    async def _before_qotd(self):
        await self.bot.wait_until_ready()

    
    
    settings = app_commands.Group(name="settings", description="Server settings tools")

    async def autocomplete_timezones(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        choices = []
        for tz_key, tz_name in tzs_accepted.items():
            if current in tz_key.lower() or current in tz_name.lower():
                choices.append(app_commands.Choice(name=tz_name, value=tz_key))
        return choices[:25]  # Discord only allows up to 25 choices

    @settings.command(name="set_timezone", description="Set the default timezone for this server.")
    @app_commands.describe(timezone="Choose a timezone")
    @app_commands.autocomplete(timezone=autocomplete_timezones)
    async def set_timezone(self, interaction: discord.Interaction, timezone: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True
            )
            return

        if timezone not in tzs_accepted:
            await interaction.response.send_message("Invalid timezone selection.", ephemeral=True)
            return

        self.settings["timezone"] = timezone
        save_settings(self.settings)
        await interaction.response.send_message(
            f"Server timezone set to **{tzs_accepted[timezone]}** (`{timezone}`)."
        )


    qotd = app_commands.Group(name="qotd", description="Question of the Day tools")

    @qotd.command(name="set_channel", description="Set the channel for QOTD messages.")
    @app_commands.describe(channel="The channel to send QOTD messages to.")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.ForumChannel):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
        
        self.settings["qotd_channel"] = channel.id
        save_settings(self.settings)

        await interaction.response.send_message(f"QOTD channel set to {channel.mention}!")

    @qotd.command(name="set_time", description="Set the time for QOTD messages.")
    @app_commands.describe(hour="Hour (0-23) to send the QOTD messages")
    async def set_time(self, interaction: discord.Interaction, hour: int):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
        
        if hour < 0 or hour > 23:
            await interaction.response.send_message("Hour must be between 0 and 23.", ephemeral=True)
            return
        
        self.settings["qotd_hour"] = hour
        self.qotd_task.change_interval(hours=1)
        if not self.qotd_task.is_running():
            self.qotd_task.start()
        
        save_settings(self.settings)
        await interaction.response.send_message(f"QOTD time set to {hour}:00!\n(Disclaimers: \n-This will only work if the bot is online!\n-The task runs once an hour meaning that it may be up to 59 minutes late.)")
    

    @qotd.command(name="upload", description="Upload QOTD questions (semicolon-separated).")
    async def qotd_upload(self, interaction: discord.Interaction):
            # admin gate if you want:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        await interaction.response.send_modal(QOTDModal(self))