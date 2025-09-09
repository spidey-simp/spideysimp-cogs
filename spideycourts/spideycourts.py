from __future__ import annotations
import asyncio
import discord
from discord import app_commands
from discord.ext import tasks
from discord import Object
from redbot.core import commands
import json
import os
from datetime import datetime, UTC
from typing import List
import textwrap
import io
import re



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COURT_FILE = os.path.join(BASE_DIR, 'courts.json')
SYSTEM_FILE = os.path.join(BASE_DIR, 'system.json')

SUPREME_COURT_CHANNEL_ID = 1302331990829174896
FIRST_CIRCUIT_CHANNEL_ID = 1400567992726716583
GEN_CHAT_DIST_CT_CHANNEL_ID = 1401700220181549289
GEN_SWGOH_DIST_CT_CHANNEL_ID = 1401721949134258286
PUBLIC_SQUARE_DIST_CT_CHANNEL_ID = 1401722584566861834
FED_JUDICIARY_ROLE_ID = 1401712141584826489
FED_CHAMBERS_CHANNEL_ID = 1401812137780838431
ONGOING_CASES_CHANNEL_ID = 1402401313370931371
EXHIBITS_CHANNEL_ID = 1402400976983425075
COURT_STEPS_CHANNEL_ID = 1402482794650931231
DIST_REPORTER_FORUM_ID = 1415079896161718375
CIRCUIT_REPORTER_FORUM_ID = 1415080169965879478
SUPREME_REPORTER_FORUM_ID = 1415080326761287761

VENUE_CHANNEL_MAP = {
    "gen_chat": GEN_CHAT_DIST_CT_CHANNEL_ID,
    "swgoh": GEN_SWGOH_DIST_CT_CHANNEL_ID,
    "public_square": PUBLIC_SQUARE_DIST_CT_CHANNEL_ID,
    "first_circuit": FIRST_CIRCUIT_CHANNEL_ID,
    "ssc": SUPREME_COURT_CHANNEL_ID
}

VENUE_NAMES = {
    "gen_chat": "General Chat District Court",
    "swgoh": "General SWGOH District Court",
    "public_square": "Public Square District Court",
    "first_circuit": "First Circuit Court of Appeals",
    "ssc": "Supreme Court"
}

JUDGE_INITS = {
    "gen_chat": "SS",
    "swgoh": "LF",
    "public_square": "S"
}

JUDGE_VENUES = {
    "gen_chat": {"name": "spidey simp", "id": 684457913250480143},
    "swgoh": {"name": "LegoFan", "id": 650814947437182977},
    "public_square": {"name": "Shadows", "id": 1325115385871204386}
}

PROCEEDING_TYPES = [
"Trial",
"Status Conference",
"Oral Argument",
"Evidentiary Hearing",
"Settlement Conference",
"Other"
]

REPORTER_KEY = "_reporter"

# How big a “page” is (must be < 2000)
TARGET_CHARS_PER_PAGE = 1400

# Map your court venues to a reporter “tier”
VENUE_TO_REPORTER = {
    # district courts
    "gen_chat": "district",
    "public_square": "district",
    "swgoh": "district",
    # circuit
    "first_circuit": "circuit",
    # supreme
    "ssc": "supreme",
}

# Reporter abbreviations + their forum channel
REPORTERS = {
    "district": {"abbr": "SPIDEYLAW", "forum_id": DIST_REPORTER_FORUM_ID},
    "circuit":  {"abbr": "F.",         "forum_id": CIRCUIT_REPORTER_FORUM_ID},
    "supreme":  {"abbr": "S.R.",       "forum_id": SUPREME_REPORTER_FORUM_ID},
}

# Bluebook-ish court parentheticals (you can tweak anytime)
COURT_PAREN = {
    # Supreme — not used (S.R. itself implies Supreme), kept here for completeness
    "ssc": {"long": "S.S.C.", "short": "S.S.C."},

    # Circuit
    "first_circuit": {"long": "1st Cir.", "short": "1st Cir."},

    # Districts — customize these to your taste
    "gen_chat":      {"long": "D. Gen. Chat", "short": "D.G.C."},
    "public_square": {"long": "D. Pub. Sq.",  "short": "D.P.S."},
    "swgoh":         {"long": "D. SWGOH",     "short": "D.SWGOH"},
}

DEFAULT_PAREN_STYLE = "long"

CITE_MULTI_RX = re.compile(
    r"""^\s*
        (\d+)\s*                        # volume
        (S\.?R\.?|F\.|SPIDEYLAW)\s+     # reporter abbr
        (\d+)\s*                        # page (or first page)
        (?:,\s*(\d+))?                  # optional pin page
        (?:\s*\([^)]*\))?               # optional trailing parenthetical (ignored)
        \s*$""",
    re.IGNORECASE | re.VERBOSE
)

def load_json(file_path):
    """Load JSON data from a file."""
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(file_path, data):
    """Save JSON data to a file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

class ComplaintFilingModal(discord.ui.Modal, title="File a Complaint"):
    def __init__(self, bot, venue: str, plaintiff: discord.Member, defendant: discord.Member):
        super().__init__()
        self.bot = bot
        self.venue = venue
        self.plaintiff = plaintiff
        self.defendant = defendant

        self.additional_plaintiffs = discord.ui.TextInput(
            label="Additional Plaintiffs (optional)",
            placeholder="Enter additional plaintiffs (semi-colon separated)...",
            style=discord.TextStyle.short,
            max_length=100,
            required=False
        )
        self.additional_defendants = discord.ui.TextInput(
            label="Additional Defendants (optional)",
            placeholder="Enter additional defendants (semi-colon separated)...",
            style=discord.TextStyle.short,
            max_length=100,
            required=False
        )
        self.complaint_text = discord.ui.TextInput(
            label="Complaint Text",
            placeholder="Enter the facts and legal basis for your complaint...",
            style=discord.TextStyle.paragraph,
            max_length=1800,
            required=True
        )
        self.add_item(self.additional_plaintiffs)
        self.add_item(self.additional_defendants)
        self.add_item(self.complaint_text)
        

    async def on_submit(self, interaction: discord.Interaction):
        venue_channel_id = VENUE_CHANNEL_MAP.get(self.venue)
        if not venue_channel_id:
            await interaction.response.send_message("❌ Invalid venue selected.", ephemeral=True)
            return

        extra_plaintiffs_raw = self.additional_plaintiffs.value
        extra_plaintiffs = [p.strip() for p in extra_plaintiffs_raw.split(';') if p.strip()]
        extra_plaintiffs_formatted = [await self.resolve_party_entry(interaction.guild, p) for p in extra_plaintiffs]
        extra_defendants_raw = self.additional_defendants.value
        extra_defendants = [d.strip() for d in extra_defendants_raw.split(';') if d.strip()]
        extra_defendants_formatted = [await self.resolve_party_entry(interaction.guild, d) for d in extra_defendants]

        court_data = self.bot.get_cog("SpideyCourts").court_data
        case_number = f"1:{interaction.created_at.year % 100:02d}-cv-{len(court_data)+1:06d}-{JUDGE_INITS.get(self.venue, 'SS')}"

        court_data[case_number] = {
            "plaintiff": self.plaintiff.id,
            "additional_plaintiffs": extra_plaintiffs_formatted,
            "defendant": self.defendant.id,
            "additional_defendants": extra_defendants_formatted,
            "counsel_for_plaintiff": interaction.user.id,
            "venue": self.venue,
            "judge": JUDGE_VENUES.get(self.venue, {}).get("name", "SS"),
            "judge_id": JUDGE_VENUES.get(self.venue, {}).get("id", 684457913250480143),
            "filings": [
                {
                    "entry": 1,
                    "document_type": "Complaint",
                    "author": interaction.user.name,
                    "author_id": interaction.user.id,
                    "content": self.complaint_text.value,
                    "timestamp": interaction.created_at.isoformat()
                }
            ]
        }

       

        # Try to send the summary message to the correct channel
        venue_channel = self.bot.get_channel(venue_channel_id)
        summary = (
            f"📁 **New Complaint Filed**\n"
            f"**Case Number:** `{case_number}`\n"
            f"**Plaintiff:** {self.plaintiff.mention}"
        )
        formatted_extra_plaintiffs = [self.format_party(interaction.guild, p) for p in extra_plaintiffs_formatted]
        formatted_extra_defendants = [self.format_party(interaction.guild, d) for d in extra_defendants_formatted]

        if extra_plaintiffs:
            summary += f"\n**Additional Plaintiffs:** {', '.join(formatted_extra_plaintiffs)}"

        summary += f"\n**Defendant:** {self.defendant.mention}"

        if extra_defendants:
            summary += f"\n**Additional Defendants:** {', '.join(formatted_extra_defendants)}"

        summary += f"\nFiled by: {interaction.user.mention}"

        summary_msg = await venue_channel.send(summary)

        filing_msg = await venue_channel.send(
            f"**Complaint Document - {case_number}**\n\n{self.complaint_text.value}"
        )

        court_data[case_number]["filings"][0]["message_id"] = filing_msg.id
        court_data[case_number]["filings"][0]["channel_id"] = filing_msg.channel.id

        save_json(COURT_FILE, court_data)

        await interaction.response.send_message(
            f"✅ Complaint filed successfully under case number `{case_number}`.",
            ephemeral=True
        )
    
    @staticmethod
    async def resolve_party_entry(guild: discord.Guild, entry: str):
        """Attempt to resolve a party string into a user ID. Fallback to string."""
        name = entry.strip().lstrip("@")
        for member in guild.members:
            if member.name == name or member.display_name == name:
                return member.id
        return name  # fallback to raw string
    
    @staticmethod
    def format_party(guild: discord.Guild, party):
        if isinstance(party, int):
            member = guild.get_member(party)
            return member.mention if member else f"<@{party}>"
        return party

class DocumentFilingModal(discord.ui.Modal, title="File another document"):
    def __init__(self, bot: commands.Bot, case_number:str, case_dict:dict, related_docs:str=None):
        super().__init__()
        self.bot = bot
        self.case_number = case_number
        self.case_dict = case_dict
        self.related_docs = related_docs

        self.doc_title = discord.ui.TextInput(
            label="Input the title of your document",
            style=discord.TextStyle.short,
            required=True,
            placeholder="Document name such as Motion to Dismiss"
        )

        self.doc_contents = discord.ui.TextInput(
            label="The contents of the document",
            placeholder="Enter the contents",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.doc_title)
        self.add_item(self.doc_contents)
        
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        filings = self.case_dict.setdefault("filings", [])
        entry_num = len(filings) + 1
        timestamp = datetime.now(UTC).isoformat()

        new_doc = {
            "entry": entry_num,
            "document_type": self.doc_title.value,
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "content": self.doc_contents.value,
            "timestamp": timestamp
        }

        if self.related_docs:
            formatted_related = [int(x.strip()) for x in self.related_docs.split(";") if x.strip().isdigit()]
            new_doc["related_docs"] = formatted_related

        filings.append(new_doc)

        # Try to send message to court channel
        cog = self.bot.get_cog("SpideyCourts")
        if not cog:
            await interaction.followup.send("Internal error: courts cog not loaded.", ephemeral=True)
            return

        venue = self.case_dict.get("venue")
        channel_id = VENUE_CHANNEL_MAP.get(venue)
        court_channel = self.bot.get_channel(channel_id)
        if not court_channel:
            await interaction.followup.send("❌ Venue channel not found.", ephemeral=True)
            return

        content = self.doc_contents.value or ""
        title = self.doc_title.value or "Document"

        if len(content) <= 1800:
            message = await court_channel.send(
                f"**{title} — {self.case_number}**\n\n{content}",
                allowed_mentions=discord.AllowedMentions.none()
            )
            thread_id = None
        else:
            message, thread = await cog._post_long_filing(
                court_channel=court_channel,
                title=title,
                case_number=self.case_number,
                author=interaction.user,
                content=content
            )
            thread_id = thread.id

        # save IDs
        new_doc["message_id"] = message.id
        new_doc["channel_id"] = message.channel.id
        if thread_id:
            new_doc["thread_id"] = thread_id

        save_json(COURT_FILE, cog.court_data)  # use the cog you already fetched


        await interaction.followup.send(f"✅ Document filed as docket entry #{entry_num}.", ephemeral=True)

class OrderModal(discord.ui.Modal, title="Issue Order / Opinion"):
    def __init__(self, bot: commands.Bot, case_number: str, order_type: str, related_entry: int | None, outcome: str | None):
        super().__init__()
        self.bot = bot
        self.case_number = case_number
        self.order_type = order_type
        self.related_entry = related_entry
        self.outcome = outcome

        self.body = discord.ui.TextInput(
            label="Order / Opinion Text",
            style=discord.TextStyle.paragraph,
            placeholder="Write the order or opinion here…",
            required=True,
            max_length=4000,
        )
        self.add_item(self.body)

    async def on_submit(self, interaction: discord.Interaction):
        # Always ACK fast; use followups later
        await interaction.response.defer(ephemeral=True, thinking=True)

        cog = self.bot.get_cog("SpideyCourts")
        if not cog:
            return await interaction.followup.send("❌ Courts cog not loaded.", ephemeral=True)

        case = cog.court_data.get(self.case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        # venue channel
        venue_key = case.get("venue")
        ch_id = VENUE_CHANNEL_MAP.get(venue_key)
        venue_ch = self.bot.get_channel(ch_id) if ch_id else None
        if not venue_ch:
            return await interaction.followup.send("❌ Venue channel not found.", ephemeral=True)

        title = f"{self.order_type} — {self.case_number}"
        content = self.body.value or ""

        # Post with long-text safety (thread + .txt for > 1800)
        try:
            if len(content) <= 1800:
                msg = await venue_ch.send(
                    f"**{title}**\n\n{content}",
                    allowed_mentions=discord.AllowedMentions.none()
                )
                thread_id = None
            else:
                msg, thread = await cog._post_long_filing(
                    court_channel=venue_ch,
                    title=title,
                    case_number=self.case_number,
                    author=interaction.user,
                    content=content,
                )
                thread_id = thread.id
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to post the order: {e}", ephemeral=True)

        # Docket entry
        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        doc = {
            "entry": entry,
            "document_type": self.order_type,
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": msg.id,
            "channel_id": msg.channel.id,
            "content": (f"Outcome: {self.outcome}" if self.outcome else None),
        }
        if thread_id:
            doc["thread_id"] = thread_id
        if self.related_entry:
            doc["related_docs"] = [self.related_entry]

        filings.append(doc)

        # If it resolves a motion, mark it
        if self.related_entry:
            rel = next((d for d in filings if d.get("entry") == self.related_entry), None)
            if rel:
                rel["resolved"] = True
                if self.outcome:
                    rel["ruling_outcome"] = self.outcome

        save_json(COURT_FILE, cog.court_data)
        await interaction.followup.send(f"✅ {self.order_type} docketed as Entry {entry}.", ephemeral=True)

class ReporterPublishModal(discord.ui.Modal, title="Publish to Reporter"):
    def __init__(self, bot: commands.Bot, case_number: str, entry: int, reporter_key: str | None, paren_style: str, parenthetical_override: str | None):
        super().__init__()
        self.bot = bot
        self.case_number = case_number
        self.entry = entry
        self.reporter_key = reporter_key
        self.paren_style = paren_style
        self.parenthetical_override = parenthetical_override

        self.headnotes = discord.ui.TextInput(
            label="Headnotes (not part of the opinion)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )
        self.keywords = discord.ui.TextInput(
            label="Keywords (comma-separated)",
            style=discord.TextStyle.short,
            required=False,
            max_length=200
        )
        self.add_item(self.headnotes)
        self.add_item(self.keywords)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        cog = self.bot.get_cog("SpideyCourts")
        if not cog:
            return await interaction.followup.send("❌ Courts cog not loaded.", ephemeral=True)

        case = cog.court_data.get(self.case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        rep_key = self.reporter_key or cog._get_reporter_for_case(case)
        rep_conf = REPORTERS.get(rep_key)
        rep_root = cog._ensure_reporter()
        rep_bucket = rep_root[rep_key]

        # Pull the opinion text from docket (thread-based long text preferred)
        opinion = await cog._gather_opinion_text_from_docket(case, self.entry)
        if not opinion:
            return await interaction.followup.send("❌ Couldn’t locate the opinion text for that entry.", ephemeral=True)

        # Forum channel
        forum = cog.bot.get_channel(rep_conf["forum_id"])
        if not forum or str(getattr(forum, "type", "")).lower() != "forum":
            return await interaction.followup.send("❌ Reporter forum not found.", ephemeral=True)

        # Caption & citation
        guild = interaction.guild
        pl = await cog.try_get_display_name(guild, case.get("plaintiff"))
        df = await cog.try_get_display_name(guild, case.get("defendant"))
        caption = f"{pl} v. {df}"

        vol = rep_bucket["current_volume"]
        first_page = rep_bucket["current_page"]
        year = datetime.now(UTC).year

        court_paren = cog._court_parenthetical(
            case=case,
            reporter_key=rep_key,
            style=self.paren_style,
            override=self.parenthetical_override
        )
        citation = cog._make_citation(rep_conf["abbr"], vol, first_page, year, court_paren=court_paren)

        # Starter post with headnotes
        starter = f"**{caption}**\n`{citation}`\n\n"
        if str(self.headnotes.value or "").strip():
            starter += f"**Headnotes (not part of the opinion)**\n{self.headnotes.value.strip()}\n\n"
        if str(self.keywords.value or "").strip():
            starter += f"*Keywords:* {self.keywords.value.strip()}\n\n"
        starter += "*Opinion follows in paginated messages below.*"

        # Create forum thread
        thread = await forum.create_thread(
            name=f"{caption} — {citation}",
            content=starter,
            allowed_mentions=discord.AllowedMentions.none()
        )

        # Paginate and post pages
        pages = cog._paginate_for_reporter(opinion, TARGET_CHARS_PER_PAGE)
        page_message_ids = []
        for pg in pages:
            m = await thread.send(pg, allowed_mentions=discord.AllowedMentions.none())
            page_message_ids.append(m.id)

        # Record in reporter
        rep_bucket["opinions"].append({
            "case_number": self.case_number,
            "entry": self.entry,
            "caption": caption,
            "year": year,
            "volume": vol,
            "first_page": first_page,
            "pages": len(pages),
            "thread_id": thread.id,
            "page_message_ids": page_message_ids,
            "headnotes": (self.headnotes.value or "").strip(),
            "keywords": [k.strip() for k in (self.keywords.value or "").split(",") if k.strip()],
        })
        rep_bucket["current_page"] = first_page + len(pages)
        cog.court_data[REPORTER_KEY] = rep_root
        save_json(COURT_FILE, cog.court_data)

        # Optional: docket that it was published
        filings = case.setdefault("filings", [])
        filings.append({
            "entry": len(filings) + 1,
            "document_type": "Reporter Publication",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"Published as {citation} ({rep_key})",
            "channel_id": rep_conf["forum_id"],
            "message_id": page_message_ids[0] if page_message_ids else None,
        })
        save_json(COURT_FILE, cog.court_data)

        await interaction.followup.send(f"✅ Published as `{citation}` in **{rep_conf['abbr']}**.", ephemeral=True)


class SpideyCourts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.court_data = load_json(COURT_FILE)
        self.show_applicants.start()
        self.show_cases.start()
    
    def cog_unload(self):
        """Stop the daily task when the cog is unloaded."""
        self.show_applicants.cancel()
        self.show_cases.cancel()
    
    @tasks.loop(hours=24)
    async def show_applicants(self):
        """Daily task to show pending applicants in the Supreme Court channel."""
        if not self.court_data:
            return

        channel = self.bot.get_channel(FED_CHAMBERS_CHANNEL_ID)
        if not channel:
            return
        
        pending_applicants = [user_id for user_id, data in self.court_data.items() if data.get('status') == 'pending']
        if not pending_applicants:
            return
        
        message = "Pending Court Applicants:\n"
        for user_id in pending_applicants:
            user = await self.bot.fetch_user(int(user_id))
            message += f"- {user.name} (ID: {user_id})\n"
        
        await channel.send(message)
    
    @tasks.loop(hours=24)
    async def show_cases(self):
        """Daily task to show ongoing cases in the Ongoing Cases channel."""
        if not self.court_data:
            return

        channel = self.bot.get_channel(ONGOING_CASES_CHANNEL_ID)
        if not channel:
            return

        # Compose new message
        ongoing = []
        for case_number, data in self.court_data.items():
            if case_number.startswith("_"):
                continue
            if not isinstance(data, dict):
                continue
            # must look like a case
            if "plaintiff" not in data or "defendant" not in data or "filings" not in data:
                continue
            if data.get("status") == "closed":
                continue
            ongoing.append((case_number, data))

        if not ongoing:
            return

        message = "**Ongoing Court Cases:**\n"
        for case_number, case_data in ongoing:
            try:
                p = await channel.guild.fetch_member(case_data["plaintiff"])
                d = await channel.guild.fetch_member(case_data["defendant"])
                pn, dn = p.display_name, d.display_name
            except Exception:
                pn, dn = str(case_data.get("plaintiff", "Unknown")), str(case_data.get("defendant", "Unknown"))
            latest = case_data['filings'][-1] if case_data.get('filings') else {}
            message += f"- `{pn}` v. `{dn}`, {case_number} (Most recent: {latest.get('document_type', 'Unknown')})\n"

        meta = self.court_data.setdefault("_meta", {})
        msg_id = meta.get("ongoing_cases_msg_id")  # if you used system.json before, use that key instead

        try:
            if msg_id:
                # edit existing message (no new notification)
                existing = await channel.fetch_message(int(msg_id))
                await existing.edit(content=message, allowed_mentions=discord.AllowedMentions.none())
            else:
                # first time: send and remember id
                new_msg = await channel.send(message, allowed_mentions=discord.AllowedMentions.none())
                meta["ongoing_cases_msg_id"] = new_msg.id
                save_json(COURT_FILE, self.court_data)

        except (discord.NotFound, discord.Forbidden):
            # if it was deleted or inaccessible, post a fresh one and save its id
            new_msg = await channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            meta["ongoing_cases_msg_id"] = new_msg.id
            save_json(COURT_FILE, self.court_data)
        
    @show_cases.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    def _ensure_reporter(self):
        """
        Ensure reporter buckets exist in self.court_data[REPORTER_KEY].
        Structure:
        {
        "_reporter": {
            "district": {"current_volume":1,"current_page":1,"opinions":[]},
            "circuit":  {"current_volume":1,"current_page":1,"opinions":[]},
            "supreme":  {"current_volume":1,"current_page":1,"opinions":[]}
        }
        }
        """
        root = self.court_data.setdefault(REPORTER_KEY, {})
        for key in REPORTERS.keys():
            root.setdefault(key, {"current_volume": 1, "current_page": 1, "opinions": []})
        return root

    def _get_reporter_for_case(self, case: dict) -> str:
        return VENUE_TO_REPORTER.get(case.get("venue"), "district")

    def _paginate_for_reporter(self, text: str, max_chars: int = TARGET_CHARS_PER_PAGE):
        """Split opinion text into fake 'pages' and prefix each with [*n]."""
        chunks, page, buf = [], 1, ""
        paras = [p.strip() for p in (text or "").split("\n\n")]
        for para in paras:
            if not para:
                continue
            parts = textwrap.wrap(para, width=max_chars, replace_whitespace=False, drop_whitespace=False)
            for part in parts:
                if len(buf) + len(part) + 2 > max_chars:
                    chunks.append(f"[*{page}]\n{buf.strip()}")
                    page += 1
                    buf = part + "\n\n"
                else:
                    buf += part + "\n\n"
        if buf.strip():
            chunks.append(f"[*{page}]\n{buf.strip()}")
        return chunks

    async def _gather_opinion_text_from_docket(self, case: dict, entry_num: int) -> str | None:
        """
        Pulls long opinion text from the filing's thread (preferred), else uses the 'content' field.
        Assumes your long-text filings/orders posted chunks as bot messages in the thread.
        """
        doc = next((d for d in case.get("filings", []) if d.get("entry") == entry_num), None)
        if not doc:
            return None
        thread_id = doc.get("thread_id")
        if thread_id:
            thread = self.bot.get_channel(int(thread_id))
            if thread and hasattr(thread, "history"):
                parts = []
                async for m in thread.history(limit=200, oldest_first=True):
                    if m.author == self.bot.user and not m.attachments:
                        parts.append(m.content)
                if parts:
                    return "\n\n".join(parts).strip()
        return (doc.get("content") or "").strip() or None

    def _needs_court_parenthetical(self, reporter_key: str) -> bool:
        # Supreme reporter (S.R.) does NOT include a court name in the parenthetical
        return reporter_key in ("district", "circuit")

    def _auto_district_parenthetical(self, venue_key: str, style: str) -> str:
        """Fallback if COURT_PAREN lacks a specific district entry."""
        raw = (globals().get("VENUE_NAMES", {}) or {}).get(venue_key, venue_key or "District Court")
        words = re.findall(r"[A-Za-z]+", raw)
        if not words:
            return "D. Dist. Ct."
        abbrev_map = {"General":"Gen.", "Public":"Pub.", "Square":"Sq.", "District":"", "Court":""}
        long_parts = [abbrev_map.get(w, w) for w in words if abbrev_map.get(w, w) != ""]
        long_txt = "D. " + " ".join(long_parts)
        if style == "long":
            return long_txt
        initials = "".join(w[0] for w in long_parts if w and w[0].isalpha()).upper()
        return f"D.{'.'.join(list(initials))}."

    def _court_parenthetical(self, case: dict, reporter_key: str, style: str = DEFAULT_PAREN_STYLE, override: str | None = None) -> str | None:
        if not self._needs_court_parenthetical(reporter_key):
            return None  # Supreme: no court name in parenthetical
        if override:
            return override.strip()
        key = case.get("venue")
        if reporter_key == "circuit":
            key = key or "first_circuit"
        if key in COURT_PAREN:
            return COURT_PAREN[key]["short" if style == "short" else "long"]
        if reporter_key == "district":
            return self._auto_district_parenthetical(key or "", style)
        return "Ct. App."

    def _make_citation(self, abbr: str, vol: int, first_page: int, year: int, court_paren: str | None = None, pin: int | None = None) -> str:
        """
        Build a reporter citation.
        Supreme:  1 S.R. 1 (2025)
        Circuit:  3 F. 245 (1st Cir. 2026)
        District: 1 SPIDEYLAW 1 (D. Gen. Chat 2025)
        With pin: 1 S.R. 1, 5 (2025)
        """
        core = f"{vol} {abbr} {first_page}"
        if pin is not None:
            core += f", {pin}"
        if court_paren:
            return f"{core} ({court_paren} {year})"
        return f"{core} ({year})"

    def _abbr_to_reporter_key(self, abbr: str) -> str | None:
        a = abbr.strip().upper().replace(" ", "")
        if a in ("S.R.", "SR", "S.R"): return "supreme"
        if a in ("F.", "F"):           return "circuit"
        if a == "SPIDEYLAW":           return "district"
        return None


    def _chunk_text(self, s: str, limit: int = 1900):
        # chunk by paragraphs first, then wrap if needed
        chunks = []
        for para in s.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if len(para) <= limit:
                chunks.append(para)
                continue
            # long paragraph → wrap by words
            for wrapped in textwrap.wrap(para, width=limit, replace_whitespace=False, drop_whitespace=False):
                chunks.append(wrapped)
        return chunks

    async def _post_long_filing(self, court_channel: discord.TextChannel, title: str, case_number: str, author: discord.Member, content: str):
        # 1) short header in channel
        header = await court_channel.send(
            f"**{title} — {case_number}**\nFiled by {author.mention}. Full text in thread ⤵️",
            allowed_mentions=discord.AllowedMentions.none()
        )
        # 2) create thread and stream content
        thread = await header.create_thread(
            name=f"{case_number} • Entry (pending) — {title}",
            auto_archive_duration=10080  # 7 days
        )
        for chunk in self._chunk_text(content, 1900):
            await thread.send(chunk)

        # 3) attach canonical .txt
        file_bytes = io.BytesIO(content.encode("utf-8"))
        safe_case = case_number.replace(":", "_")
        await thread.send(file=discord.File(fp=file_bytes, filename=f"{safe_case}_{title.replace(' ', '_')}.txt"))

        return header, thread

    
    court = app_commands.Group(name="court", description="Court related commands")

    def is_judge(self, interaction: discord.Interaction) -> bool:
        return any(role.id == FED_JUDICIARY_ROLE_ID for role in interaction.user.roles)


    @court.command(name="apply_for_creds", description="Apply for court credentials")
    @app_commands.describe(context="Reason for applying", bar_number="Bar number (if applicable)")
    @app_commands.choices(
        context=[
            app_commands.Choice(name="General Inquiry", value="general_inquiry"),
            app_commands.Choice(name="Attorney", value="attorney"),
            app_commands.Choice(name="Pro Se", value="pro_se"),
            app_commands.Choice(name="Other", value="other")
        ]
    )
    async def apply_for_creds(self, interaction: discord.Interaction, context: str, bar_number: str = None):
        """Apply for court credentials."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_id = str(interaction.user.id)
        if user_id in self.court_data:
            await interaction.followup.send("You have already applied for court credentials.", ephemeral=True)
            return
        
        self.court_data[user_id] = {'status': 'pending', 'context': context}
        if bar_number:
            self.court_data[user_id]['bar_number'] = bar_number
        await interaction.followup.send("Your application has been submitted and is pending review.", ephemeral=True)
        save_json(COURT_FILE, self.court_data)
    
    @court.command(name="view_applicants", description="View all court applicants")
    async def view_applicants(self, interaction: discord.Interaction):
        """View all court applicants."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not self.is_judge(interaction):
            await interaction.followup.send("You do not have permission to view applicants.", ephemeral=True)
            return
        if not self.court_data:
            await interaction.followup.send("No applicants found.", ephemeral=True)
            return
        
        applicants = []
        for user_id, data in self.court_data.items():
            user = await self.bot.fetch_user(int(user_id))
            status = data.get('status', 'unknown')
            context = data.get('context', 'N/A')
            bar_number = data.get('bar_number', 'N/A')
            applicants.append(f"{user.name} (ID: {user_id}) - Status: {status}, Context: {context}, Bar Number: {bar_number}")
        
        response = "\n".join(applicants)
        await interaction.followup.send(f"Applicants:\n{response}", ephemeral=True)


    async def pending_applicants_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        matches = []
        for user_id, data in self.court_data.items():
            if data.get("status") != "pending":
                continue

            try:
                user = await self.bot.fetch_user(int(user_id))
                if current.lower() in user.name.lower():
                    matches.append(app_commands.Choice(name=user.name, value=str(user.id)))
            except discord.NotFound:
                continue  # User might’ve left server or changed ID

            if len(matches) >= 25:  # Discord limit
                break

        return matches


    @court.command(name="grant_creds", description="Grant court credentials to an applicant")
    @app_commands.describe(user="The user to grant credentials to")
    @app_commands.autocomplete(user=pending_applicants_autocomplete)
    async def grant_creds(self, interaction: discord.Interaction, user: str):
        """Grant court credentials to an applicant."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not self.is_judge(interaction):
            await interaction.followup.send("You do not have permission to view applicants.", ephemeral=True)
            return
        
        user_id = str(user)
        if user_id not in self.court_data:
            await interaction.followup.send("User has not applied for court credentials.", ephemeral=True)
            return

        self.court_data[user_id]['status'] = 'granted'
        save_json(COURT_FILE, self.court_data)

        try:
            user_obj = await self.bot.fetch_user(int(user_id))
            await interaction.followup.send(f"Granted court credentials to {user_obj.name}.", ephemeral=True)
            try:
                await user_obj.send("You have been granted court credentials. Please check the court channels for more information.")
            except discord.Forbidden:
                await interaction.followup.send(f"Granted credentials, but could not DM {user_obj.name}.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"Granted credentials, but could not DM or resolve username.", ephemeral=True)

    @court.command(name="deny_creds", description="Deny court credentials to an applicant")
    @app_commands.describe(user="The user to deny credentials to", reason="Reason for denial")
    @app_commands.autocomplete(user=pending_applicants_autocomplete)
    async def deny_creds(self, interaction: discord.Interaction, user: str, reason: str):
        """Deny court credentials to an applicant."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not self.is_judge(interaction):
            await interaction.followup.send("You do not have permission to view applicants.", ephemeral=True)
            return

        user_id = str(user)
        if user_id not in self.court_data:
            await interaction.followup.send("User has not applied for court credentials.", ephemeral=True)
            return

        self.court_data[user_id]['status'] = 'denied'
        save_json(COURT_FILE, self.court_data)

        try:
            user_obj = await self.bot.fetch_user(int(user_id))
            await interaction.followup.send(f"Denied court credentials to {user_obj.name}.", ephemeral=True)
            try:
                await user_obj.send(f"You have been denied court credentials. Reason: {reason}")
            except discord.Forbidden:
                await interaction.followup.send(f"Denied credentials, but could not DM {user_obj.name}.", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send(f"Denied credentials, but could not DM or resolve username.", ephemeral=True)

    
    @court.command(name="file_complaint", description="File a new complaint")
    @app_commands.describe(plaintiff="Plaintiff's name", defendant="Defendant's name", venue="Venue for the complaint")
    @app_commands.choices(
        venue=[
            app_commands.Choice(name="General Chat District Court", value="gen_chat"),
            app_commands.Choice(name="SWGOH District Court", value="swgoh"),
            app_commands.Choice(name="Public Square District Court", value="public_square"),
            app_commands.Choice(name="First Circuit", value="first_circuit"),
            app_commands.Choice(name="Supreme Court", value="ssc")
        ]
    )
    async def file_complaint(self, interaction: discord.Interaction, plaintiff: discord.Member, defendant: discord.Member, venue: str):
        """File a new complaint."""
        if plaintiff == defendant:
            await interaction.response.send_message("❌ Plaintiff and defendant cannot be the same person.", ephemeral=True)
            return
        
        await interaction.response.send_modal(
            ComplaintFilingModal(self.bot, venue, plaintiff, defendant)
        )

    async def case_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for case numbers where the user is a party or counsel."""
        matches = []

        for case_number, case_data in self.court_data.items():
            user_id = interaction.user.id

            # Ensure ID lists for additional parties
            additional_plaintiffs = case_data.get("additional_plaintiffs", [])
            additional_defendants = case_data.get("additional_defendants", [])

            if isinstance(additional_plaintiffs, list) and isinstance(additional_defendants, list):
                # Only include cases where user is relevant
                is_relevant = (
                    user_id == case_data.get("plaintiff") or
                    user_id == case_data.get("defendant") or
                    user_id == case_data.get("counsel_for_plaintiff") or
                    user_id == case_data.get("counsel_for_defendant") or
                    user_id == case_data.get("judge_id") or
                    str(user_id) in additional_plaintiffs or
                    str(user_id) in additional_defendants
                )

                if is_relevant and (current.lower() in case_number.lower() or current.lower() in f"{case_data.get('plaintiff', 'Unknown')} v. {case_data.get('defendant', 'Unknown')} {case_number.lower()}".lower()):
                    # Try resolving names for nicer autocomplete display
                    plaintiff_name = str(case_data.get("plaintiff", "Unknown"))
                    defendant_name = str(case_data.get("defendant", "Unknown"))
                    guild = interaction.guild
                    try:
                        plaintiff_member = guild.get_member(case_data["plaintiff"]) or await guild.fetch_member(case_data["plaintiff"])
                        plaintiff_name = plaintiff_member.display_name
                    except Exception:
                        pass

                    try:
                        defendant_member = guild.get_member(case_data["defendant"]) or await guild.fetch_member(case_data["defendant"])
                        defendant_name = defendant_member.display_name
                    except Exception:
                        pass

                    matches.append(
                        app_commands.Choice(
                            name=f"{plaintiff_name} v. {defendant_name}, {case_number}",
                            value=case_number
                        )
                    )

            if len(matches) >= 25:
                break

        return matches
    
    @court.command(name="view_docket", description="View the docket for a case")
    @app_commands.describe(case_number="The case number to view")
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def view_docket(self, interaction: discord.Interaction, case_number: str):
        """View the docket for a specific case."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        case_data = self.court_data.get(case_number)

        if not case_data:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return
        
        guild = interaction.guild

        plaintiff_member = guild.get_member(case_data["plaintiff"]) or await guild.fetch_member(case_data["plaintiff"])
        defendant_member = guild.get_member(case_data["defendant"]) or await guild.fetch_member(case_data["defendant"])

        plaintiff_name = plaintiff_member.display_name
        defendant_name = defendant_member.display_name

        plaintiff_id = str(case_data.get("plaintiff"))
        defendant_id = str(case_data.get("defendant"))
        counsel_map = case_data.get("counsel_of_record", {})

        plaintiff_counsel_id = counsel_map.get(plaintiff_id)
        defendant_counsel_id = counsel_map.get(defendant_id)

        if plaintiff_counsel_id:
            plaintiff_counsel = await self.try_get_display_name(guild, plaintiff_counsel_id)
        else:
            plaintiff_counsel = "<@Unknown>"

        if defendant_counsel_id:
            defendant_counsel = await self.try_get_display_name(guild, defendant_counsel_id)
        else:
            defendant_counsel = "<@Unknown>"



        docket_text = f"**Docket for Case {plaintiff_name} v. {defendant_name}, {case_number}**\n\n"
        docket_text += f"**Counsel for Plaintiff:** {plaintiff_counsel}\n"
        docket_text += f"**Counsel for Defendant:** {defendant_counsel}\n"
        venue = case_data.get("venue", "Unknown")
        if venue in VENUE_NAMES:
            docket_text += f"**Venue:** {VENUE_NAMES[venue]}\n"
        docket_text += f"**Judge:** {case_data.get('judge', 'Unknown')}\n"
        filings = []
        for doc in case_data.get("filings", []):
            try:
                link = f"https://discord.com/channels/{interaction.guild.id}/{doc.get('channel_id')}/{doc.get('message_id')}"
            except KeyError:
                link = "#"
            
            ts = doc.get('timestamp')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts = dt.strftime("%m/%d/%y")
                except Exception:
                    pass
            
            exhibits = []
            for ex in doc.get("exhibits", []):
                ex_link = f"https://discord.com/channels/{interaction.guild.id}/{ex['channel_id']}/{ex['file_id']}"
                exhibits.append(f"  ↳ Exhibit {ex['exhibit_number']}: [{ex['text']}]({ex_link})\n")

            related_docs = doc.get("related_docs", [])
            related_str = ""
            if related_docs:
                related_str = " (Related to: " + ", ".join(f"Entry {r}" for r in related_docs) + ")"

            filings.append(
                f"**[{doc.get('entry', 1)}] [{doc.get('document_type', 'Unknown')}]({link})** by {doc.get('author', 'Unknown')} on {ts}{related_str}\n"
                f"{''.join(exhibits) if exhibits else ''}"
            )
            
        
        reversed_filings = filings[::-1]
        docket_text += "\n".join(reversed_filings) if reversed_filings else "No filings found."

        await interaction.followup.send(docket_text, ephemeral=True)

    @court.command(name="connect_document", description="Manually update the link for a document.")
    @app_commands.describe(
        case_number="Case number (e.g., 1:25-cv-000001-SS)",
        doc_num="Docket entry number",
        link="Discord message link to connect"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    async def connect_document(self, interaction: discord.Interaction, case_number: str, doc_num: int, link: str):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return

        try:
            channel_id, message_id = link.split("/")[-2:]
            channel_id = int(channel_id)
            message_id = int(message_id)
        except ValueError:
            await interaction.followup.send("❌ Invalid message link format.", ephemeral=True)
            return

        filings = case.get("filings", [])
        for doc in filings:
            if doc.get("entry") == doc_num:
                doc["channel_id"] = channel_id
                doc["message_id"] = message_id
                save_json(COURT_FILE, self.court_data)
                await interaction.followup.send(f"✅ Updated docket entry #{doc_num} with new link.", ephemeral=True)
                return

        await interaction.followup.send("❌ Docket entry not found.", ephemeral=True)

    async def try_get_display_name(self, guild, user_id):
        try:
            member = await guild.fetch_member(user_id)
            return member.display_name
        except:
            return str(user_id)


    async def docket_entry_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        choices = []

        for case_number, case_data in self.court_data.items():
            filings = case_data.get("filings", [])
            for doc in filings:
                if doc.get("author_id") != interaction.user.id:
                    continue
                entry = doc.get("entry")
                if not entry:
                    continue

                # Fetch names
                plaintiff = await self.try_get_display_name(interaction.guild, case_data.get("plaintiff"))
                defendant = await self.try_get_display_name(interaction.guild, case_data.get("defendant"))
                header = f"{plaintiff} v. {defendant}"

                label = f"{header}, {case_number} Entry {entry}"
                value = f"{case_number};{entry}"
                choices.append(app_commands.Choice(name=label, value=value))

        return choices[:25]


    @court.command(name="file_exhibit", description="File an exhibit to an existing document")
    @app_commands.describe(
        docket_entry="Docket entry number",
        caption="Text description of the exhibit",
        exhibit_file="File to upload as an exhibit"
    )
    @app_commands.autocomplete(docket_entry=docket_entry_autocomplete)
    async def file_exhibit(self, interaction:discord.Interaction, docket_entry: str, exhibit_file: discord.Attachment, caption: str = "No caption provided"):
        """File an exhibit to an existing document."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        case_number, entry_num = docket_entry.split(";")
        entry_num = int(entry_num)


        case_data = self.court_data.get(case_number)
        if not case_data:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return
        
        doc = next((d for d in case_data.get("filings", []) if d.get("entry") == entry_num), None)
        if not doc:
            await interaction.followup.send("❌ Docket entry not found for that case.", ephemeral=True)
            return


        # Save the file to the exhibits channel
        exhibits_channel = self.bot.get_channel(EXHIBITS_CHANNEL_ID)
        if not exhibits_channel:
            await interaction.followup.send("❌ Exhibits channel not found.", ephemeral=True)
            return
                
        doc.setdefault("exhibits", [])
        exhibit_num = len(doc["exhibits"]) + 1
        exhibit_msg = await exhibits_channel.send(
            f"Exhibit #{exhibit_num} for Case {case_number}, Docket Entry #{entry_num}:\n{caption}",
            file=await exhibit_file.to_file()
        )

        doc["exhibits"].append( {
            "exhibit_number": f"{entry_num}-{exhibit_num}",
            "text": caption,
            "file_url": exhibit_msg.attachments[0].url,
            "file_id": exhibit_msg.id,
            "channel_id": exhibits_channel.id,
            "submitted_by": interaction.user.id,
            "timestamp": str(datetime.now(UTC).isoformat())
        }
        )

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ Exhibit #{exhibit_num} filed successfully for Docket Entry #{entry_num}.", ephemeral=True)


    @court.command(name="file_document", description="File other documents for a case.")
    @app_commands.describe(
        case_number="The case to file a document for",
        document_type="What type of document",
        related_docs="Any docs related to this one (separate with ;)"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(document_type=[
        app_commands.Choice(name="Motion", value="motion"),
        app_commands.Choice(name="Response", value="response"),
        app_commands.Choice(name="Reply", value="reply"),
        app_commands.Choice(name="Countermotion", value="countermotion"),
        app_commands.Choice(name="Amendment", value="amended"),
        app_commands.Choice(name="Supplement", value="supplemental"),
        app_commands.Choice(name="Other (answer, etc.)", value="other")
    ])
    async def file_document(self, interaction:discord.Interaction, case_number:str, document_type:str, related_docs:str=None):

        case_data = self.court_data.get(case_number)
        if not case_data:
            await interaction.response.send_message("No case data found for that case number.", ephemeral=True)
            return

        case_data = self.court_data[case_number]
        
        related_doc_reqs = ["response", "reply", "countermotion", "amended", "supplemental"]
        if document_type in related_doc_reqs and not related_docs:
            await interaction.response.send_message("That kind of document should have at least one related document. Please confer with the docket to see other docket numbers.")
            return
        
        await interaction.response.send_modal(DocumentFilingModal(bot=self.bot, case_number=case_number, case_dict=case_data, related_docs=related_docs))
        

    @court.command(name="serve", description="Serve a party with a complaint")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        case_number="The case number to serve",
        defendant="The defendant being served",
        method="The method of service"
    )
    @app_commands.choices(method=[
        app_commands.Choice(name="Mention in court channel", value="mention"),
        app_commands.Choice(name="Direct Message", value="dm"),
        app_commands.Choice(name="Both", value="both")
    ])
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def serve(self, interaction: discord.Interaction, case_number: str, defendant: discord.Member, method: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        # Validate case
        case = self.court_data.get(case_number)
        if not case:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return

        # Validate defendant
        valid_parties = [case.get("defendant")] + case.get("additional_defendants", [])
        if str(defendant.id) not in map(str, valid_parties):
            await interaction.followup.send("❌ This user is not listed as a defendant in the case.", ephemeral=True)
            return


        # Format notification
        plaintiff_name = await self.try_get_display_name(interaction.guild, case.get("plaintiff"))
        defendant_name = await self.try_get_display_name(interaction.guild, case.get("defendant"))
        venue_id = VENUE_CHANNEL_MAP.get(case.get("venue"))
        venue = self.bot.get_channel(venue_id).mention if venue_id else "Unknown Venue"
        service_notice = (
            f"📨 **You have been served.**\n\n"
            f"A complaint has been filed against you in the case:\n\n"
            f"`{plaintiff_name} v. {defendant_name}`\n"
            f"Case Number: `{case_number}`\n"
            f"Venue: {venue}\n\n"
            f"You are required to respond within 72 hours. Failure to respond may result in a default judgment."
        )

        # Notify defendant
        served_publicly = False
        if method.value in ["mention", "both"]:
            channel_id = COURT_STEPS_CHANNEL_ID  # public place to post
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"{defendant.mention}\n{service_notice}")
                served_publicly = True

        if method.value in ["dm", "both"]:
            try:
                await defendant.send(service_notice)
            except discord.Forbidden:
                if not served_publicly:
                    await interaction.followup.send("❌ Could not DM the defendant and no public mention made.", ephemeral=True)
                    return

        # Record service
        service_data = case.setdefault("service", {})
        service_data[str(defendant.id)] = {
            "method": method.value,
            "served_at": datetime.now(UTC).isoformat(),
            "served_by": interaction.user.id
        }

        # Update status
        case["status"] = "ready_for_response"

        # Add docket entry
        filings = case.setdefault("filings", [])
        entry_num = len(filings) + 1
        timestamp = datetime.now(UTC).isoformat()
        filings.append({
            "entry": entry_num,
            "document_type": "Proof of Service",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "content": f"Served {defendant.display_name} via {method.name}.",
            "timestamp": timestamp
        })

        save_json(COURT_FILE, self.court_data)

        await interaction.followup.send(f"✅ {defendant.display_name} has been served via {method.name}. Docket updated (Entry {entry_num}).", ephemeral=True)

    @court.command(name="notice_of_appearance", description="File a Notice of Appearance in a case")
    @app_commands.describe(
        case_number="The case in which you are appearing",
        party="The party you are representing (must be named in the case)"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def notice_of_appearance(self, interaction: discord.Interaction, case_number: str, party: discord.Member):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return

        valid_parties = [case.get("plaintiff"), case.get("defendant")] + case.get("additional_defendants", [])
        if str(party.id) not in map(str, valid_parties):
            await interaction.followup.send("❌ That user is not a listed party in this case.", ephemeral=True)
            return

        # Save appearance
        counsel_map = case.setdefault("counsel_of_record", {})
        counsel_map[str(party.id)] = interaction.user.id

        # Add to docket
        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        timestamp = datetime.now(UTC).isoformat()
        party_name = await self.try_get_display_name(interaction.guild, party.id)
        author_name = await self.try_get_display_name(interaction.guild, interaction.user.id)

        filings.append({
            "entry": entry,
            "document_type": "Notice of Appearance",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "content": f"{author_name} appeared on behalf of {party_name}.",
            "timestamp": timestamp
        })

        save_json(COURT_FILE, self.court_data)

        await interaction.followup.send(f"✅ {author_name} has appeared on behalf of {party_name} in {case_number}.", ephemeral=True)

    
    @court.command(name="schedule", description="Schedule a conference, hearing, or trial")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        case_number="The case you're scheduling for (e.g., 1:25-cv-000001-SS)",
        event_type="Type of proceeding",
        date="Date (MM/DD/YY)",
        time="Time (HH:MM AM/PM, server time)",
        notes="Optional notes for the parties"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(event_type=[app_commands.Choice(name=t, value=t) for t in PROCEEDING_TYPES])
    async def schedule(
        self,
        interaction: discord.Interaction,
        case_number: str,
        event_type: app_commands.Choice[str],
        date: str,
        time: str,
        notes: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        # Validate case
        case = self.court_data.get(case_number)
        if not case:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return

        # Parse date/time (server-local input), store as ISO string for record
        try:
            local_dt = datetime.strptime(f"{date} {time}", "%m/%d/%y %I:%M %p")
        except ValueError:
            await interaction.followup.send("❌ Invalid date/time. Use MM/DD/YY and HH:MM AM/PM.", ephemeral=True)
            return

        # Names + venue mention
        plaintiff_name = await self.try_get_display_name(interaction.guild, case.get("plaintiff"))
        defendant_name = await self.try_get_display_name(interaction.guild, case.get("defendant"))
        venue_id = VENUE_CHANNEL_MAP.get(case.get("venue"))
        venue_mention = self.bot.get_channel(venue_id).mention if venue_id else "Unknown Venue"

        # Public notice on courthouse steps
        steps_ch = self.bot.get_channel(COURT_STEPS_CHANNEL_ID)
        notice = (
            f"📅 **{event_type.value} Scheduled**\n\n"
            f"**Case:** {plaintiff_name} v. {defendant_name}\n"
            f"**Case No.:** `{case_number}`\n"
            f"**Proceeding:** {event_type.value}\n"
            f"**Date:** {local_dt.strftime('%m/%d/%y')}\n"
            f"**Time:** {local_dt.strftime('%I:%M %p')}\n"
            f"**Location:** {venue_mention}"
        )
        if notes:
            notice += f"\n**Notes:** {notes}"

        msg = None
        if steps_ch:
            msg = await steps_ch.send(notice)

        # Persist lightweight schedule record (optional but handy)
        schedule_list = case.setdefault("schedule", [])
        schedule_list.append({
            "event_type": event_type.value,
            "scheduled_for_local": local_dt.strftime("%m/%d/%y %I:%M %p"),
            "notes": notes,
            "created_by": interaction.user.id,
            "created_at": datetime.now(UTC).isoformat(),
            "message_id": msg.id if msg else None,
            "channel_id": steps_ch.id if steps_ch else None,
        })

        # Docket entry (one line; detail lives in the notice we just posted)
        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        filings.append({
            "entry": entry,
            "document_type": f"{event_type.value} Scheduled",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": msg.id if msg else None,
            "channel_id": steps_ch.id if steps_ch else None,
            # Keep a compact summary so your current /view_docket prints something meaningful:
            "related_docs": [],  # optional
            "content": f"Set for {local_dt.strftime('%m/%d/%y at %I:%M %p')}" + (f" | Notes: {notes}" if notes else "")
        })

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(
            f"✅ Scheduled **{event_type.value}** for `{case_number}` on {local_dt.strftime('%m/%d/%y at %I:%M %p')}. "
            f"Docket entry #{entry} added.",
            ephemeral=True
        )

    
    @court.command(name="order", description="Issue an Order / Opinion (optionally resolves a motion).")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        case_number="Case number (e.g., 1:25-cv-000001-SS)",
        related_entry="Optional docket entry this resolves (e.g., a motion)",
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(order_type=[
        app_commands.Choice(name="Order", value="Order"),
        app_commands.Choice(name="Opinion", value="Opinion"),
        app_commands.Choice(name="Opinion & Order", value="Opinion & Order"),
    ])
    @app_commands.choices(outcome=[
        app_commands.Choice(name="Granted", value="Granted"),
        app_commands.Choice(name="Denied", value="Denied"),
        app_commands.Choice(name="Partial", value="Partial"),
        app_commands.Choice(name="Other", value="Other"),
    ])
    async def order(
        self,
        interaction: discord.Interaction,
        case_number: str,
        order_type: app_commands.Choice[str],
        related_entry: int | None = None,
        outcome: app_commands.Choice[str] | None = None,
    ):
        # (Optional) Only the assigned judge may issue orders
        case = self.court_data.get(case_number)
        if not case:
            await interaction.response.send_message("❌ Case not found.", ephemeral=True)
            return
        cid = case.get("judge_id")
        if cid and int(cid) != interaction.user.id:
            await interaction.response.send_message("❌ Only the assigned judge may issue orders in this case.", ephemeral=True)
            return

        await interaction.response.send_modal(
            OrderModal(
                bot=self.bot,
                case_number=case_number,
                order_type=order_type.value,
                related_entry=related_entry,
                outcome=(outcome.value if outcome else None),
            )
        )



    @court.command(name="enter_judgment", description="Enter final judgment and close the case.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        case_number="Case number",
        judgment_text="Short judgment text (e.g., Dismissed; costs to Defendant)",
        prejudice="If dismissal, choose prejudice (ignored otherwise)"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(judgment_type=[
        app_commands.Choice(name="Dismissal", value="Dismissal"),
        app_commands.Choice(name="Default Judgment", value="Default Judgment"),
        app_commands.Choice(name="Summary Judgment", value="Summary Judgment"),
        app_commands.Choice(name="Consent Judgment", value="Consent Judgment"),
        app_commands.Choice(name="Bench Verdict", value="Bench Verdict"),
        app_commands.Choice(name="Declaratory Judgment", value="Declaratory Judgment"),
    ])
    @app_commands.choices(prejudice=[
        app_commands.Choice(name="With Prejudice", value="with prejudice"),
        app_commands.Choice(name="Without Prejudice", value="without prejudice"),
    ])
    async def enter_judgment(
        self,
        interaction: discord.Interaction,
        case_number: str,
        judgment_type: app_commands.Choice[str],
        judgment_text: str,
        prejudice: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        steps = self.bot.get_channel(COURT_STEPS_CHANNEL_ID)
        tail = f" ({prejudice.value})" if (judgment_type.value == "Dismissal" and prejudice) else ""
        body = f"⚖️ **Judgment Entered**\n\n`{case_number}`\n**Type:** {judgment_type.value}{tail}\n{textwrap.shorten(judgment_text, 180)}"
        msg = await steps.send(body) if steps else None

        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        filings.append({
            "entry": entry,
            "document_type": "Judgment",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": (msg.id if msg else None),
            "channel_id": (steps.id if steps else None),
            "content": f"{judgment_type.value}{tail} — {judgment_text}"
        })

        case["status"] = "closed"
        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ {judgment_type.value} entered (Entry {entry}). Case **closed**.", ephemeral=True)


    
    @court.command(name="file_appeal", description="File a Notice of Appeal (or petition to the Supreme Server Court).")
    @app_commands.describe(
        case_number="District or circuit case you are appealing",
        target_court="Court to appeal to (e.g., First Circuit, Supreme Server Court)",
        reason="Short reason/grounds for appeal",
        as_cert="If appealing to the SSC, file as a Petition for Cert (True) or direct appeal (False)"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(target_court=[
        app_commands.Choice(name="First Circuit", value="first_circuit"),
        app_commands.Choice(name="Supreme Server Court", value="ssc"),
    ])
    async def file_appeal(
        self,
        interaction: discord.Interaction,
        case_number: str,
        target_court: app_commands.Choice[str],
        reason: str,
        as_cert: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)

        orig = self.court_data.get(case_number)
        if not orig:
            return await interaction.followup.send("❌ Original case not found.", ephemeral=True)

        target_venue = target_court.value
        # Build new appellate case number in your familiar format
        judge_inits = JUDGE_INITS.get(target_venue, "AP")
        new_seq = len(self.court_data) + 1
        new_case_number = f"1:{interaction.created_at.year % 100:02d}-cv-{new_seq:06d}-{judge_inits}"

        # Parties carry over
        new_case = {
            "plaintiff": orig.get("plaintiff"),
            "additional_plaintiffs": orig.get("additional_plaintiffs", []),
            "defendant": orig.get("defendant"),
            "additional_defendants": orig.get("additional_defendants", []),
            "venue": target_venue,
            "judge": JUDGE_VENUES.get(target_venue, {}).get("name", None),
            "judge_id": JUDGE_VENUES.get(target_venue, {}).get("id", None),
            "origin_case": case_number,
            "origin_venue": orig.get("venue"),
            "case_type": "appeal",
            "status": "open",
            "filings": []
        }

        # First filing in appellate case
        is_ssc = (target_venue == "ssc")
        doc_type = "Petition for Certiorari" if (is_ssc and as_cert) else "Notice of Appeal"
        first_filing = {
            "entry": 1,
            "document_type": doc_type,
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"Appeal taken from {case_number}. Grounds: {reason}"
        }
        new_case["filings"].append(first_filing)

        # Persist new case
        self.court_data[new_case_number] = new_case

        # Public notice on courthouse steps
        steps = self.bot.get_channel(COURT_STEPS_CHANNEL_ID)
        if steps:
            pl = await self.try_get_display_name(interaction.guild, new_case["plaintiff"])
            df = await self.try_get_display_name(interaction.guild, new_case["defendant"])
            notice = (
                f"📤 **Appeal Filed**\n\n"
                f"From `{case_number}` → **{target_court.name}** as `{new_case_number}`\n"
                f"Case: {pl} v. {df}\n"
                f"Filed by: {interaction.user.mention}\n"
                f"Grounds: {reason}\n"
                f"Document: {doc_type}"
            )
            msg = await steps.send(notice)
            first_filing["message_id"] = msg.id
            first_filing["channel_id"] = steps.id

        # Add a docket entry in the origin case
        orig_filings = orig.setdefault("filings", [])
        origin_entry = len(orig_filings) + 1
        orig_filings.append({
            "entry": origin_entry,
            "document_type": f"{doc_type} Filed",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"Appeal to {target_court.name} as `{new_case_number}` (Grounds: {reason})"
        })

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ Appeal filed to **{target_court.name}**. New case: `{new_case_number}`.", ephemeral=True)

    
    @court.command(name="appeal_disposition", description="Enter a disposition in an appellate case, optionally with remand.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        appellate_case="The appellate case number",
        outcome="The result",
        text="Short disposition text (e.g., 'Affirmed for reasons stated in opinion.')",
        remand="If checked, remand to the origin court",
        instructions="Optional remand instructions for the lower court"
    )
    @app_commands.autocomplete(appellate_case=case_autocomplete)
    @app_commands.choices(outcome=[
        app_commands.Choice(name="Affirmed", value="Affirmed"),
        app_commands.Choice(name="Reversed", value="Reversed"),
        app_commands.Choice(name="Vacated", value="Vacated"),
        app_commands.Choice(name="Affirmed in part / Reversed in part", value="Affirmed in part / Reversed in part"),
        app_commands.Choice(name="Dismissed", value="Dismissed"),
        app_commands.Choice(name="Denied Certiorari", value="Denied Certiorari"),
        app_commands.Choice(name="Granted Certiorari", value="Granted Certiorari"),
    ])
    async def appeal_disposition(
        self,
        interaction: discord.Interaction,
        appellate_case: str,
        outcome: app_commands.Choice[str],
        text: str,
        remand: bool = False,
        instructions: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        app_case = self.court_data.get(appellate_case)
        if not app_case or app_case.get("case_type") != "appeal":
            return await interaction.followup.send("❌ Appellate case not found.", ephemeral=True)

        origin_case_no = app_case.get("origin_case")
        origin = self.court_data.get(origin_case_no)

        # Post disposition in appellate venue or courthouse steps
        steps = self.bot.get_channel(COURT_STEPS_CHANNEL_ID)
        link_msg = None
        if steps:
            pl = await self.try_get_display_name(interaction.guild, app_case["plaintiff"])
            df = await self.try_get_display_name(interaction.guild, app_case["defendant"])
            body = (
                f"📜 **Appellate Disposition**\n\n"
                f"Case `{appellate_case}` — {pl} v. {df}\n"
                f"Outcome: **{outcome.value}**\n"
                f"{text}"
            )
            if remand and origin_case_no:
                body += f"\n**Remanded to:** `{origin_case_no}`"
                if instructions:
                    body += f"\n**Instructions:** {instructions}"
            link_msg = await steps.send(body)

        # Add appellate docket entry
        app_filings = app_case.setdefault("filings", [])
        app_entry = len(app_filings) + 1
        app_filings.append({
            "entry": app_entry,
            "document_type": "Appellate Disposition",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": (link_msg.id if link_msg else None),
            "channel_id": (steps.id if steps else None),
            "content": f"{outcome.value}: {text}",
            "related_docs": []
        })
        app_case["status"] = "closed"

        # If remand, add entry to origin and set status open (or reopened)
        if remand and origin:
            o_filings = origin.setdefault("filings", [])
            o_entry = len(o_filings) + 1
            remand_text = f"Remanded from `{appellate_case}`. {('Instructions: ' + instructions) if instructions else ''}".strip()
            o_filings.append({
                "entry": o_entry,
                "document_type": "Remand",
                "author": interaction.user.name,
                "author_id": interaction.user.id,
                "timestamp": datetime.now(UTC).isoformat(),
                "content": remand_text
            })
            # Reopen if previously closed
            if origin.get("status") == "closed":
                origin["status"] = "open"

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ Disposition recorded for `{appellate_case}`.", ephemeral=True)


    @court.command(name="pocket_dep", description="Pocket courtroom deputy: quick announcements/actions.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        instruction="What should the deputy do?",
        case_number="Case number (needed for introduce / call_case / confirm_schedule)",
        person="User to act on (needed for swear_witness)",
        affirm="Use 'affirm' in the oath instead of 'swear' (default: False)",
        pace_seconds="Optional pause between prompts; default 7s for oaths, 3s otherwise",
        text="For 'minute_order': the announcement text (e.g., 'dismissing the action without prejudice')"
    )
    @app_commands.choices(instruction=[
        app_commands.Choice(name="Introduce the Judge", value="introduce"),
        app_commands.Choice(name="Call the Case", value="call_case"),
        app_commands.Choice(name="Swear in Witness", value="swear_witness"),
        app_commands.Choice(name="Recess", value="recess"),
        app_commands.Choice(name="Adjourn", value="adjourn"),
        app_commands.Choice(name="Confirm Schedule", value="confirm_schedule"),
        app_commands.Choice(name="Minute Order", value="minute_order"),
    ])
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def pocket_dep(
        self,
        interaction: discord.Interaction,
        instruction: app_commands.Choice[str],
        case_number: str | None = None,
        person: discord.Member | None = None,
        affirm: bool = False,
        pace_seconds: float | None = None,
        text: str | None = None,
    ):
        # Ephemeral ack so we can post publicly + sleep
        await interaction.response.defer(ephemeral=True)

        # Defaults: a smidge longer where users need to respond
        default_pause = 7.0 if instruction.value == "swear_witness" else 3.0
        pause = float(pace_seconds) if pace_seconds is not None else default_pause

        async def _need_case() -> dict | None:
            if not case_number:
                await interaction.followup.send("❌ Please provide a case_number for this instruction.", ephemeral=True)
                return None
            c = self.court_data.get(case_number)
            if not c:
                await interaction.followup.send("❌ Case not found.", ephemeral=True)
                return None
            return c

        # INTRODUCE
        if instruction.value == "introduce":
            case = await _need_case()
            if not case:
                return
            judge_name = None
            jid = case.get("judge_id")
            if jid:
                judge_name = await self.try_get_display_name(interaction.guild, jid)
            judge_name = judge_name or case.get("judge") or "the Court"

            await interaction.channel.send(f"🔨 **Bang! Bang! Bang!** All rise for the Honorable **{judge_name}**!")
            await asyncio.sleep(pause)  # slightly longer pause
            await interaction.channel.send("You may be seated.")
            return await interaction.followup.send("✅ Introduced.", ephemeral=True)

        # CALL CASE
        if instruction.value == "call_case":
            case = await _need_case()
            if not case:
                return
            pl = await self.try_get_display_name(interaction.guild, case.get("plaintiff"))
            df = await self.try_get_display_name(interaction.guild, case.get("defendant"))
            await interaction.channel.send(
                f"🗂️ Calling case `{case_number}`: **{pl} v. {df}**.\n"
                f"Counsel, please state your appearances for the record."
            )
            return await interaction.followup.send("✅ Case called.", ephemeral=True)

        # SWEAR WITNESS
        if instruction.value == "swear_witness":
            if not person:
                return await interaction.followup.send("❌ Please provide the witness in `person`.", ephemeral=True)
            style = "affirm" if affirm else "swear"
            await interaction.channel.send(f"✋ {person.mention}, please raise your right hand.")
            await asyncio.sleep(2.0)
            await interaction.channel.send(
                f"Do you solemnly **{style}** that the testimony you shall give in this matter "
                f"will be the **truth, the whole truth, and nothing but the truth**?"
            )
            await asyncio.sleep(pause)  # longer window so they can reply “I do.”
            await interaction.channel.send("Please answer: **“I do.”**")
            return await interaction.followup.send("✅ Witness oath prompted.", ephemeral=True)

        # RECESS
        if instruction.value == "recess":
            await interaction.channel.send("🔔 All rise. The Court will take a brief recess.")
            await asyncio.sleep(pause)
            await interaction.channel.send("You may be seated. (Recess.)")
            return await interaction.followup.send("✅ Recess announced.", ephemeral=True)

        # ADJOURN
        if instruction.value == "adjourn":
            await interaction.channel.send("🔔 All rise. This Court is **adjourned**.")
            await asyncio.sleep(pause)
            await interaction.channel.send("You may be seated.")
            return await interaction.followup.send("✅ Adjournment announced.", ephemeral=True)

        # CONFIRM SCHEDULE (pull most recent from case['schedule'])
        if instruction.value == "confirm_schedule":
            case = await _need_case()
            if not case:
                return
            schedule = case.get("schedule", [])
            if not schedule:
                return await interaction.followup.send("❌ No scheduled events found for this case.", ephemeral=True)
            last = schedule[-1]
            kind = last.get("event_type", "Proceeding")
            when = last.get("scheduled_for_local") or "TBD"
            await interaction.channel.send(f"📣 **{kind}** is scheduled for **{when}**.")
            return await interaction.followup.send("✅ Schedule confirmed.", ephemeral=True)

        # MINUTE ORDER (free-form deputy confirmation)
        if instruction.value == "minute_order":
            # need a case number to docket it
            if not case_number:
                return await interaction.followup.send("❌ Provide `case_number` to docket the minute order.", ephemeral=True)
            case = self.court_data.get(case_number)
            if not case:
                return await interaction.followup.send("❌ Case not found.", ephemeral=True)
            if not text:
                return await interaction.followup.send("❌ Provide `text` for the minute order announcement.", ephemeral=True)

            # Public announcement in the current channel
            msg = await interaction.channel.send(f"📝 A minute order has been issued {text.strip()}.")

            # Docket entry
            filings = case.setdefault("filings", [])
            entry = len(filings) + 1
            filings.append({
                "entry": entry,
                "document_type": "Minute Order",
                "author": interaction.user.name,
                "author_id": interaction.user.id,
                "timestamp": datetime.now(UTC).isoformat(),
                "message_id": msg.id,
                "channel_id": msg.channel.id,
                "content": text.strip()
            })

            save_json(COURT_FILE, self.court_data)
            return await interaction.followup.send(
                f"✅ Minute order announced and docketed as Entry {entry}.",
                ephemeral=True
            )

        await interaction.followup.send("❌ Unknown instruction.", ephemeral=True)
    
    async def _party_is_in_case(self, case: dict, party: int) -> bool:
        ids = [case.get("plaintiff"), case.get("defendant")] + case.get("additional_defendants", []) + case.get("additional_plaintiffs", [])
        return str(party) in map(str, ids)

    @court.command(name="substitute_counsel", description="Substitute counsel for a specific party.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(case_number="Case number", party="Party represented", new_counsel="New counsel user")
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def substitute_counsel(self, interaction: discord.Interaction, case_number: str, party: discord.Member, new_counsel: discord.Member):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        if not await self._party_is_in_case(case, party.id):
            return await interaction.followup.send("❌ That user is not a party in this case.", ephemeral=True)

        # Use your per-party counsel map (or per-side fields if you prefer)
        cofr = case.setdefault("counsel_of_record", {})
        prev = cofr.get(str(party.id))
        cofr[str(party.id)] = new_counsel.id

        # Docket entry
        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        filings.append({
            "entry": entry,
            "document_type": "Substitution of Counsel",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"{(await self.try_get_display_name(interaction.guild, party.id))}: {('from ' + (await self.try_get_display_name(interaction.guild, prev)) + ' ') if prev else ''}to {new_counsel.display_name}"
        })

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send("✅ Substitution recorded.", ephemeral=True)

    @court.command(name="withdraw_counsel", description="Withdraw as counsel for a specific party.")
    @app_commands.describe(case_number="Case number", party="Party represented")
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def withdraw_counsel(self, interaction: discord.Interaction, case_number: str, party: discord.Member):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        if not await self._party_is_in_case(case, party.id):
            return await interaction.followup.send("❌ That user is not a party in this case.", ephemeral=True)

        cofr = case.setdefault("counsel_of_record", {})
        current = cofr.get(str(party.id))
        if current != interaction.user.id and not any(r.id == FED_JUDICIARY_ROLE_ID for r in interaction.user.roles):
            return await interaction.followup.send("❌ Only current counsel or a judge may withdraw.", ephemeral=True)

        cofr.pop(str(party.id), None)

        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        filings.append({
            "entry": entry,
            "document_type": "Withdrawal of Counsel",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"{(await self.try_get_display_name(interaction.guild, party.id))}: {interaction.user.display_name} withdrawn"
        })

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send("✅ Withdrawal recorded.", ephemeral=True)

    @court.command(name="reporter_publish", description="Publish a docketed opinion to the appropriate Reporter.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(reporter_override=[
        app_commands.Choice(name="District (SPIDEYLAW)", value="district"),
        app_commands.Choice(name="Circuit (F.)", value="circuit"),
        app_commands.Choice(name="Supreme (S.R.)", value="supreme"),
    ])
    @app_commands.choices(paren_style=[
        app_commands.Choice(name="Long (e.g., D. Gen. Chat)", value="long"),
        app_commands.Choice(name="Short (e.g., D.G.C.)", value="short"),
    ])
    @app_commands.describe(
        case_number="Case number",
        entry="Docket entry number containing the opinion/order",
        reporter_override="Optional: force a specific reporter",
        paren_style="Optional: long/short parenthetical style",
        parenthetical_override="Optional: custom court name (ignored for S.R.)"
    )
    async def reporter_publish(
        self,
        interaction: discord.Interaction,
        case_number: str,
        entry: int,
        reporter_override: app_commands.Choice[str] | None = None,
        paren_style: app_commands.Choice[str] | None = None,
        parenthetical_override: str | None = None,
    ):
        case = self.court_data.get(case_number)
        if not case:
            await interaction.response.send_message("❌ Case not found.", ephemeral=True)
            return
        # Optional guard: only assigned judge may publish
        cid = case.get("judge_id")
        if cid and int(cid) != interaction.user.id:
            await interaction.response.send_message("❌ Only the assigned judge may publish this opinion.", ephemeral=True)
            return

        await interaction.response.send_modal(ReporterPublishModal(
            bot=self.bot,
            case_number=case_number,
            entry=entry,
            reporter_key=(reporter_override.value if reporter_override else None),
            paren_style=(paren_style.value if paren_style else DEFAULT_PAREN_STYLE),
            parenthetical_override=parenthetical_override
        ))


    @court.command(name="reporter_cite", description="Open a Reporter citation (SPIDEYLAW / F. / S.R.).")
    @app_commands.describe(citation="e.g., '1 S.R. 5' or '1 SPIDEYLAW 1, 5'")
    async def reporter_cite(self, interaction: discord.Interaction, citation: str):
        await interaction.response.defer(ephemeral=True)
        m = CITE_MULTI_RX.match(citation or "")
        if not m:
            return await interaction.followup.send("❌ Bad citation. Try `1 S.R. 5`, `1 F. 22`, or `1 SPIDEYLAW 100`.", ephemeral=True)

        vol = int(m.group(1))
        rep_key = self._abbr_to_reporter_key(m.group(2))
        primary_page = int(m.group(3))
        pin_page = (int(m.group(4)) if m.group(4) else None)

        rep_root = self.court_data.get(REPORTER_KEY) or {}
        bucket = rep_root.get(rep_key) or {}
        opinions = bucket.get("opinions", [])

        # If pin_page provided, primary_page is the opinion's first page; jump to pin_page within it
        if pin_page is not None:
            for op in opinions:
                if op.get("volume") == vol and op.get("first_page") == primary_page:
                    first = op.get("first_page")
                    total = op.get("pages", 0)
                    if not (first <= pin_page < first + total):
                        return await interaction.followup.send("❌ Pin page out of range for that opinion.", ephemeral=True)
                    idx = pin_page - first
                    thread_id = op.get("thread_id")
                    msg_id = (op.get("page_message_ids") or [None])[idx]
                    thread = self.bot.get_channel(int(thread_id)) if thread_id else None
                    if thread and msg_id:
                        url = f"https://discord.com/channels/{thread.guild.id}/{thread.id}/{msg_id}"
                        return await interaction.followup.send(f"🔗 {citation} → {url}", ephemeral=True)
                    if thread:
                        url = f"https://discord.com/channels/{thread.guild.id}/{thread.id}"
                        return await interaction.followup.send(f"🔗 {citation} → {url}", ephemeral=True)
            return await interaction.followup.send("❌ Opinion not found for that start page.", ephemeral=True)

        # Otherwise treat primary_page as a global page in the volume
        for op in opinions:
            if op.get("volume") != vol:
                continue
            first = op.get("first_page", 0)
            total = op.get("pages", 0)
            if first <= primary_page < first + total:
                idx = primary_page - first
                thread_id = op.get("thread_id")
                msg_id = (op.get("page_message_ids") or [None])[idx]
                thread = self.bot.get_channel(int(thread_id)) if thread_id else None
                if thread and msg_id:
                    url = f"https://discord.com/channels/{thread.guild.id}/{thread.id}/{msg_id}"
                    return await interaction.followup.send(f"🔗 {citation} → {url}", ephemeral=True)
                if thread:
                    url = f"https://discord.com/channels/{thread.guild.id}/{thread.id}"
                    return await interaction.followup.send(f"🔗 {citation} → {url}", ephemeral=True)

        await interaction.followup.send("❌ Citation not found in the Reporter.", ephemeral=True)
