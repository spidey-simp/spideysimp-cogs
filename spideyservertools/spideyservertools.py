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
SUG_STATUSES = {
    "planned":      ("🛠️ Planned",      0x808080),
    "in_progress":  ("🟡 In Progress",   0xF1C40F),
    "resolved":     ("🟢 Resolved",      0x2ECC71),
    "rejected":     ("🔴 Rejected",      0xE74C3C),
}

EMOJI_CREATORS = 1287650335896371230

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
    @app_commands.checks.has_role(EMOJI_CREATORS, admin_bypass=True)
    async def qotd_upload(self, interaction: discord.Interaction):

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
                await self._ensure_tracker_message(interaction.guild)
            else:
                await self._ensure_tracker_message(interaction.guild)
            await interaction.response.send_message("✅ Tracker refreshed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Refresh failed: `{e}`", ephemeral=True)

    
    def _now_str(self):
        return datetime.utcnow().strftime("%Y-%m-%d")

    def _guild_sug_store(self, guild_id: int):
        store = self.settings.setdefault("cog_suggestions", {})
        g = store.setdefault(str(guild_id), {})
        g.setdefault("counter", 0)
        g.setdefault("channel_id", None)
        g.setdefault("items", {})  # id -> dict
        return g

    def _render_suggestion_embed(self, data: dict) -> discord.Embed:
        """data keys: id, cog, title, desc, status, created_by, created_at, updated_by, updated_at"""
        label, color = SUG_STATUSES.get(data["status"], ("❓ Unknown", 0x95A5A6))
        embed = discord.Embed(
            title=f"Feature Suggestion • #{data['id']} • {data['cog']}",
            description=(data["title"] if data["title"] else "No title"),
            color=color,
            timestamp=datetime.utcnow(),
        )
        if data.get("desc"):
            embed.add_field(name="Details", value=data["desc"][:1024], inline=False)
        embed.add_field(name="Status", value=label, inline=True)
        embed.add_field(name="Last Updated", value=data.get("updated_at") or data["created_at"], inline=True)
        submitter = data.get("created_by")
        if submitter:
            embed.set_footer(text=f"Submitted by @{submitter} • use /cogs suggest_status to update")
        return embed

    async def _suggest_status_autocomplete(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        return [
            app_commands.Choice(name=label, value=key)
            for key, (label, _) in SUG_STATUSES.items()
            if current in key or current in label.lower()
        ][:25]

    # optionally, autocomplete cog names from your tracker (if you use it)
    async def _cogname_autocomplete(self, interaction: discord.Interaction, current: str):
        tracker = self.settings.get("cog_tracker", {})
        items = tracker.get("items", {}) if isinstance(tracker.get("items"), dict) else {}
        names = sorted(items.keys())
        cur = (current or "").lower()
        return [app_commands.Choice(name=n, value=n) for n in names if cur in n.lower()][:25]

    # -------- Commands --------

    cogsgrp = app_commands.Group(name="cogs", description="Cog status & suggestions")

    @cogsgrp.command(name="set_suggestions_channel", description="Set the channel where cog suggestions are logged.")
    @app_commands.describe(channel="Text channel for suggestion logs")
    async def set_suggestions_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True); return
        g = self._guild_sug_store(interaction.guild_id)
        g["channel_id"] = channel.id
        save_settings(self.settings)
        await interaction.response.send_message(f"Suggestions will be logged in {channel.mention}.", ephemeral=True)

    @cogsgrp.command(name="suggest", description="Suggest a feature/update for a cog.")
    @app_commands.describe(
        cog="Which cog the suggestion is for",
        title="Short title of the suggestion",
        details="Optional details"
    )
    @app_commands.autocomplete(cog=_cogname_autocomplete)
    async def suggest(self, interaction: discord.Interaction, cog: str, title: str, details: str | None = None):
        g = self._guild_sug_store(interaction.guild_id)
        chan_id = g.get("channel_id")
        if not chan_id:
            await interaction.response.send_message("Suggestions channel not set. Ask an admin to run `/cogs set_suggestions_channel`.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(chan_id) or await self.bot.fetch_channel(chan_id)

        g["counter"] += 1
        sug_id = g["counter"]
        data = {
            "id": sug_id,
            "cog": cog.strip(),
            "title": title.strip(),
            "desc": (details or "").strip(),
            "status": "planned",  # default
            "created_by": str(interaction.user.name),
            "created_at": self._now_str(),
            "updated_by": str(interaction.user.name),
            "updated_at": self._now_str(),
            "message_id": None,
        }

        embed = self._render_suggestion_embed(data)

        try:
            msg = await channel.send(embed=embed)
            data["message_id"] = msg.id
            g["items"][str(sug_id)] = data
            save_settings(self.settings)
            await interaction.response.send_message(f"✅ Logged suggestion **#{sug_id}** in {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Failed to post suggestion: `{e}`", ephemeral=True)

    @cogsgrp.command(name="suggest_status", description="Update the status of a suggestion.")
    @app_commands.describe(
        suggestion_id="ID number shown in the suggestion title",
        status="New status",
        note="Optional new title/desc note to add or replace"
    )
    @app_commands.autocomplete(status=_suggest_status_autocomplete)
    async def suggest_status(self, interaction: discord.Interaction, suggestion_id: int, status: str, note: str | None = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Admin only.", ephemeral=True); return

        g = self._guild_sug_store(interaction.guild_id)
        items = g.get("items", {})
        data = items.get(str(suggestion_id))
        if not data:
            await interaction.response.send_message("Unknown suggestion ID.", ephemeral=True); return

        if status not in SUG_STATUSES:
            await interaction.response.send_message("Invalid status. Use planned / in_progress / resolved / rejected.", ephemeral=True); return

        data["status"] = status
        if note:
            # if you want to *replace* title/desc, adjust here. For now, this updates the description line.
            data["desc"] = note.strip()
        data["updated_by"] = str(interaction.user.name)
        data["updated_at"] = self._now_str()

        # Try to edit the original message; recreate if it's gone
        chan_id = g.get("channel_id")
        if not chan_id:
            await interaction.response.send_message("Suggestions channel not set.", ephemeral=True); return
        channel = interaction.guild.get_channel(chan_id) or await self.bot.fetch_channel(chan_id)

        embed = self._render_suggestion_embed(data)

        try:
            if data.get("message_id"):
                msg = await channel.fetch_message(data["message_id"])
                await msg.edit(embed=embed)
            else:
                msg = await channel.send(embed=embed)
                data["message_id"] = msg.id
        except Exception:
            # message was deleted or can't be fetched; post a fresh one
            msg = await channel.send(embed=embed)
            data["message_id"] = msg.id

        save_settings(self.settings)
        await interaction.response.send_message(f"Updated suggestion **#{suggestion_id}** → {SUG_STATUSES[status][0]}.", ephemeral=True)