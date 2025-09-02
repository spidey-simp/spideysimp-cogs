import discord
from redbot.core import commands, Config
from discord import app_commands
from discord.ext import tasks
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

STATUS_CHOICES = ["planned", "in_progress", "stalled", "done"]
STATUS_EMOJI = {
    "planned": "🛠️",
    "in_progress": "🟡",
    "stalled": "💤",
    "done": "🟢",
}

FIELD_LIMIT = 1024

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
    
    @commands.is_owner()
    @commands.command()
    async def slash_nuke(self, ctx, scope: str = "global"):
        """
        PURGE stale application commands.
        Usage: [p]slash_nuke           -> global
               [p]slash_nuke guild     -> this guild only
               [p]slash_nuke allguilds -> all guilds the bot is in
        """
        app_id = (await self.bot.application_info()).id
        scope = scope.lower()

        if scope == "global":
            await self.bot.http.bulk_upsert_global_commands(app_id, [])
            await ctx.send("✅ Purged **global** app commands.")
        elif scope == "guild":
            g = ctx.guild
            await self.bot.http.bulk_upsert_guild_commands(app_id, g.id, [])
            await ctx.send(f"✅ Purged app commands for **{g.name}**.")
        elif scope == "allguilds":
            for g in list(self.bot.guilds):
                await self.bot.http.bulk_upsert_guild_commands(app_id, g.id, [])
            await ctx.send(f"✅ Purged app commands for **{len(self.bot.guilds)}** guild(s).")
        else:
            await ctx.send("Usage: `[p]slash_nuke` | `[p]slash_nuke guild` | `[p]slash_nuke allguilds`")
            return

    @commands.is_owner()
    @commands.command()
    async def slash_resync(self, ctx):
        """Re-sync current local tree (global + this guild)."""
        # Global sync
        global_cmds = await self.bot.tree.sync()
        # Guild sync (fast register for this guild)
        guild_cmds = []
        if ctx.guild:
            guild_cmds = await self.bot.tree.sync(guild=ctx.guild)

        await ctx.send(
            f"🔁 Re-synced. Global: {len(global_cmds)} | Guild({ctx.guild and ctx.guild.name}): {len(guild_cmds)}"
        )

    @commands.is_owner()
    @commands.command()
    async def slash_audit(self, ctx):
        """List remote vs local top-level commands so you can verify cleanup."""
        app_id = (await self.bot.application_info()).id
        local = {c.name for c in self.bot.tree.get_commands()}  # current local top-level
        remote_global = await self.bot.tree.fetch_commands()
        rg = ", ".join(sorted(c.name for c in remote_global)) or "—"
        lg = ", ".join(sorted(local)) or "—"

        msg = [f"**Local (top-level):** {lg}",
               f"**Remote Global:** {rg}"]

        if ctx.guild:
            remote_guild = await self.bot.tree.fetch_commands(guild=ctx.guild)
            rgl = ", ".join(sorted(c.name for c in remote_guild)) or "—"
            msg.append(f"**Remote {ctx.guild.name}:** {rgl}")

        await ctx.send("\n".join(msg))

    
    cogsgrp = app_commands.Group(name="cogs", description="Cog status tracker")



    def _chunk_lines(self, lines: list[str], title: str):
        """Yield (name, value) field tuples under the 1024-char limit."""
        chunk = []
        length = 0
        chunks = []
        for line in lines:
            ln = len(line) + 1  # +1 for newline
            if length + ln > FIELD_LIMIT:
                chunks.append("\n".join(chunk))
                chunk, length = [line], ln
            else:
                chunk.append(line)
                length += ln
        if chunk:
            chunks.append("\n".join(chunk))

        for i, val in enumerate(chunks, 1):
            name = f"{title} ({i}/{len(chunks)})" if len(chunks) > 1 else title
            yield name, val


    async def _render_tracker_embed(self):
        tracker = self.settings.setdefault("cog_tracker", {})
        items = tracker.setdefault("items", {})

        by_status = {"planned": [], "in_progress": [], "stalled": [], "done": []}
        for name, meta in items.items():
            st = meta.get("status", "planned")
            note = meta.get("note", "") or "no note"
            when = meta.get("updated_at", "—")
            who  = meta.get("updated_by", "unknown")
            line = f"**{name}** — _{note}_ • updated {when}"  # drop “by” if it’s always you
            by_status.setdefault(st, []).append(line)

        embed = discord.Embed(
            title="🗂️ Cog Status Tracker",
            description="A quick view of project states. Use `/cogs add` and `/cogs update`.",
            timestamp=datetime.utcnow(),
        )
        total = sum(len(v) for v in by_status.values())
        embed.set_footer(text=f"{total} tracked | last render")

        # Add fields, chunking any that overflow
        for st, lines in by_status.items():
            if not lines:
                continue
            title = f"{STATUS_EMOJI.get(st,'•')} {st.replace('_',' ').title()}  ({len(lines)})"
            for name, val in self._chunk_lines(lines, title):
                embed.add_field(name=name, value=val, inline=False)

        return embed


    async def _ensure_tracker_message(self, guild: discord.Guild):
        tracker = self.settings.setdefault("cog_tracker", {})
        chan_id = tracker.get("channel_id")
        msg_id = tracker.get("message_id")
        if not chan_id:
            return None, None

        channel = guild.get_channel(chan_id) or await self.bot.fetch_channel(chan_id)
        embed = await self._render_tracker_embed()

        message = None
        if msg_id:
            try:
                message = await channel.fetch_message(msg_id)
                await message.edit(embed=embed)
                return channel, message
            except Exception:
                pass  # message was deleted or invalid

        # create fresh message
        message = await channel.send(embed=embed)
        tracker["message_id"] = message.id
        save_settings(self.settings)
        return channel, message

    async def _status_autocomplete(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        return [
            app_commands.Choice(name=s.replace("_", " ").title(), value=s)
            for s in STATUS_CHOICES
            if current in s
        ][:25]

    @cogsgrp.command(name="set_channel", description="Set the channel that shows the cog tracker.")
    @app_commands.describe(channel="Text channel where the tracker embed lives")
    async def cogs_set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        tracker = self.settings.setdefault("cog_tracker", {})
        tracker["channel_id"] = channel.id
        tracker.pop("message_id", None)  # force re-create
        save_settings(self.settings)
        await self._ensure_tracker_message(interaction.guild)
        await interaction.response.send_message(f"Tracker channel set to {channel.mention}.")

    @cogsgrp.command(name="add", description="Track a new cog/project.")
    @app_commands.describe(name="Short identifier", status="planned/in_progress/stalled/done", note="Optional note")
    @app_commands.autocomplete(status=_status_autocomplete)
    async def cogs_add(self, interaction: discord.Interaction, name: str, status: str, note: str | None = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        if status not in STATUS_CHOICES:
            await interaction.response.send_message("Invalid status.", ephemeral=True)
            return
        tracker = self.settings.setdefault("cog_tracker", {})
        items = tracker.setdefault("items", {})
        items[name] = {
            "status": status,
            "note": (note or "").strip(),
            "updated_by": str(interaction.user.id),
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        save_settings(self.settings)
        await self._ensure_tracker_message(interaction.guild)
        await interaction.response.send_message(f"Added **{name}** as {STATUS_EMOJI[status]} {status.replace('_',' ')}.", ephemeral=True)

    @cogsgrp.command(name="update", description="Update status/note for a tracked cog.")
    @app_commands.describe(name="Identifier to update", status="planned/in_progress/stalled/done", note="Optional note")
    @app_commands.autocomplete(status=_status_autocomplete)
    async def cogs_update(self, interaction: discord.Interaction, name: str, status: str | None = None, note: str | None = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return
        tracker = self.settings.setdefault("cog_tracker", {})
        items = tracker.setdefault("items", {})
        if name not in items:
            await interaction.response.send_message("Unknown cog name.", ephemeral=True)
            return
        if status:
            if status not in STATUS_CHOICES:
                await interaction.response.send_message("Invalid status.", ephemeral=True)
                return
            items[name]["status"] = status
        if note is not None:
            items[name]["note"] = note.strip()
        items[name]["updated_by"] = str(interaction.user.id)
        items[name]["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d")

        save_settings(self.settings)
        await self._ensure_tracker_message(interaction.guild)
        await interaction.response.send_message("Updated.", ephemeral=True)



    @cogsgrp.command(name="refresh", description="Refresh the cog tracker embed(s).")
    @app_commands.describe(
        recreate="Post new message(s) instead of editing existing ones (use if IDs are stale)."
    )
    async def cogs_refresh(self, interaction: discord.Interaction, recreate: bool = False):
        # admin gate
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True)
            return

        tracker = self.settings.setdefault("cog_tracker", {})
        chan_id = tracker.get("channel_id")
        if not chan_id:
            await interaction.response.send_message(
                "Tracker channel not set. Use `/cogs set_channel` first.",
                ephemeral=True,
            )
            return

        # If you're using the split-per-status approach, we store "message_ids" as a dict.
        # Otherwise we store a single "message_id".
        is_split = isinstance(tracker.get("message_ids"), dict)

        if recreate:
            # Blow away saved IDs so we force-create fresh messages.
            if is_split:
                tracker["message_ids"] = {}
            else:
                tracker.pop("message_id", None)
            save_settings(self.settings)

        # Re-render and upsert message(s)
        try:
            if is_split:
                await self._ensure_tracker_messages(interaction.guild)
            else:
                await self._ensure_tracker_message(interaction.guild)
            await interaction.response.send_message("✅ Tracker refreshed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Refresh failed: `{e}`", ephemeral=True)