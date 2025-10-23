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
import random
from dataclasses import dataclass, asdict
import time, uuid
import io, re, json
from typing import Optional




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
GOVERNMENT_ROLE_ID = 1302324304712695909

VENUE_CHANNEL_MAP = {
    "gen_chat": GEN_CHAT_DIST_CT_CHANNEL_ID,
    "swgoh": GEN_SWGOH_DIST_CT_CHANNEL_ID,
    "public_square": PUBLIC_SQUARE_DIST_CT_CHANNEL_ID,
    "first_circuit": FIRST_CIRCUIT_CHANNEL_ID,
    "ssc": SUPREME_COURT_CHANNEL_ID
}

VENUE_NAMES = {
    "gen_chat": "Commons District Court",
    "swgoh": "Gaming District Court",
    "public_square": "District of Parker District Court",
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
    "gen_chat":      {"long": "D. Commons", "short": "D.C."},
    "public_square": {"long": "D. Dist. Parker",  "short": "D.D.P."},
    "swgoh":         {"long": "D. Gaming",     "short": "D.G."},
}

GOV_DEFAULTS = {
    "country": "The Spidey Republic",
    # "state": "State of ???",
    # "city":  "City of ???",
}

DEFAULT_PAREN_STYLE = "long"

MENTION_RX = re.compile(r"<@!?(?P<id>\d+)>")

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

def _start_page_from_cite(cite: str) -> int | None:
    # e.g., "1 SPIDEYLAW 4 (D. Commons 2025)" → 4
    m = re.search(r"\b\d+\s+[A-Z][A-Z0-9.]+\s+(\d+)\b", cite)
    return int(m.group(1)) if m else None

TEXTY_EXTS = {".txt", ".md", ".markdown", ".yml", ".yaml", ".json", ".rtf", ".pdf", ".docx"}
MAX_ATTACH_BYTES = 8 * 1024 * 1024

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

@dataclass
class Party:
    id: int | None            # Discord user id if user, else None
    name: str                 # Display text (org/class name, or user display at time of entry)
    kind: str                 # "user" | "org" | "class" | "state" | "text"
    pid: str = ""             # stable internal party id (uuid4), set on creation
    attorneys: list[int] = None  # list of Discord user ids

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["attorneys"] is None: d["attorneys"] = []
        return d

def _now() -> int: return int(time.time())

def _uuid() -> str: return uuid.uuid4().hex

def _ext_of(name: str) -> str:
    n = (name or "").lower()
    return "." + n.rsplit(".", 1)[-1] if "." in n else ""

def _strip_rtf(x: str) -> str:
    # minimal (good for simple RTF)
    x = re.sub(r"\{\\\*[^{}]*\}", "", x)
    x = re.sub(r"\\[a-zA-Z]+\d* ?", "", x)
    x = x.replace("{", "").replace("}", "")
    return x.strip()

async def _read_attachment_text(att: discord.Attachment) -> str:
    """
    Extract text from a small-ish attachment.
    Supports: .txt/.md/.yml/.yaml/.json/.rtf/.pdf/.docx
    Scanned PDFs won't work (no OCR here).
    """
    ext = _ext_of(att.filename)
    if ext not in TEXTY_EXTS:
        raise ValueError("Unsupported file type. Use .txt, .md, .yml/.yaml, .json, .rtf, .pdf, or .docx.")
    if att.size and att.size > MAX_ATTACH_BYTES:
        raise ValueError(f"File too large ({att.size} bytes). Keep under {MAX_ATTACH_BYTES} bytes.")

    raw = await att.read()  # bytes

    # plain text-ish
    if ext in {".txt", ".md", ".markdown", ".yml", ".yaml", ".json", ".rtf"}:
        try:
            txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            txt = raw.decode("cp1252", errors="replace")
        if ext == ".json":
            try:
                obj = json.loads(txt)
                txt = json.dumps(obj, indent=2, ensure_ascii=False)
            except Exception:
                pass
        if ext == ".rtf":
            txt = _strip_rtf(txt)
        return txt.strip()

    # DOCX (optional)
    if ext == ".docx":
        try:
            import docx  # python-docx
        except Exception:
            raise ValueError("DOCX support requires the 'python-docx' package. Install it, or upload a .txt.")
        f = io.BytesIO(raw)
        doc = docx.Document(f)
        parts = [p.text for p in doc.paragraphs]
        for t in getattr(doc, "tables", []):
            for row in t.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts).strip()

    # PDF (optional)
    if ext == ".pdf":
        try:
            import PyPDF2
        except Exception:
            raise ValueError("PDF support requires 'PyPDF2'. Install it, or upload a .txt.")
        f = io.BytesIO(raw)
        try:
            reader = PyPDF2.PdfReader(f)
        except Exception as e:
            raise ValueError(f"Could not read PDF: {e}")
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
        txt = "\n".join(parts).strip()
        if not txt:
            raise ValueError("This PDF appears scanned (no embedded text). Use OCR or upload a .txt.")
        return txt

    return ""


class ComplaintFilingModal(discord.ui.Modal, title="File a Complaint"):
    def __init__(
        self,
        bot,
        venue: str,
        plaintiff: str | int | discord.Member | None,
        defendant: str | int | discord.Member,
        *,
        criminal: bool = False,
        government: str | None = None,
    ):
        super().__init__()
        self.bot = bot
        self.venue = venue
        self.plaintiff = plaintiff
        self.defendant = defendant
        self.criminal = bool(criminal)
        self.government = government

        self.statutes_at_issue = discord.ui.TextInput(
            label="Statutes at Issue (optional)",
            placeholder="Enter statutes at issue (semi-colon separated).",
            style=discord.TextStyle.short,
            max_length=200,
            required=False,
        )
        self.additional_defendants = discord.ui.TextInput(
            label="Additional Defendants (optional)",
            placeholder="Enter additional defendants (semi-colon separated).",
            style=discord.TextStyle.short,
            max_length=100,
            required=False,
        )
        self.complaint_text = discord.ui.TextInput(
            label="Complaint Text",
            placeholder="Enter the facts and legal basis for your complaint.",
            style=discord.TextStyle.paragraph,
            max_length=1800,
            required=True,
        )
        self.add_item(self.statutes_at_issue)
        self.add_item(self.additional_defendants)
        self.add_item(self.complaint_text)

    @staticmethod
    async def resolve_party_entry(guild: discord.Guild, entry):
        """Resolve to user id if possible; else keep text."""
        if isinstance(entry, discord.Member): return entry.id
        if isinstance(entry, int): return entry
        s = str(entry or "").strip()
        m = MENTION_RX.match(s)
        if m: return int(m.group("id"))
        name = s.lstrip("@")
        for member in guild.members:
            if member.name == name or member.display_name == name:
                return member.id
        return s  # text/org/class

    @staticmethod
    def format_party(guild: discord.Guild, party):
        if isinstance(party, int):
            member = guild.get_member(party)
            return member.mention if member else f"<@{party}>"
        return party  # string/org/class/etc.

    async def on_submit(self, interaction: discord.Interaction):
        venue_channel_id = VENUE_CHANNEL_MAP.get(self.venue)
        if not venue_channel_id:
            return await interaction.response.send_message("❌ Invalid venue selected.", ephemeral=True)


        # 1) Resolve parties FIRST
        pl_val = None
        if not self.criminal:
            pl_val = await self.resolve_party_entry(interaction.guild, self.plaintiff)
        df_val = await self.resolve_party_entry(interaction.guild, self.defendant)

        extras_raw = self.additional_defendants.value
        extras = [d.strip() for d in extras_raw.split(";") if d.strip()]
        extra_vals = [await self.resolve_party_entry(interaction.guild, d) for d in extras]

        # ... earlier in on_submit ...
        if self.criminal:
            gov_name = (self.government and GOV_DEFAULTS.get(self.government.lower(), self.government)) or GOV_DEFAULTS["country"]
            plaintiff_stored = gov_name
            counsel_pl = interaction.user.id  # auto-assume filer = prosecutor
            case_type = "criminal"
            is_criminal = True
        else:
            plaintiff_stored = pl_val
            counsel_pl = interaction.user.id  # filer = plaintiff’s counsel
            case_type = "civil"
            is_criminal = False


        # 2) Case number with proper type
        typ = "cr" if self.criminal else "cv"
        court_data = self.bot.get_cog("SpideyCourts").court_data
        case_number = f"1:{interaction.created_at.year % 100:02d}-{typ}-{len(court_data)+1:06d}-{JUDGE_INITS.get(self.venue, 'SS')}"

        # 3) Initial case dict (always include filings[0])
        judge_name = JUDGE_VENUES.get(self.venue, {}).get("name", "SS")
        judge_id   = JUDGE_VENUES.get(self.venue, {}).get("id", 684457913250480143)


        court_data[case_number] = {
            "plaintiff": plaintiff_stored,
            "defendant": df_val,
            "additional_plaintiffs": [],           # kept for legacy tools; real edits via clerk cmds
            "additional_defendants": extra_vals,
            "counsel_for_plaintiff": counsel_pl,
            "venue": self.venue,
            "judge": judge_name,
            "judge_id": judge_id,
            "case_type": case_type,
            "is_criminal": is_criminal,
            "filings": [{
                "entry": 1,
                "document_type": "Complaint" if not self.criminal else "Criminal Complaint",
                "author": interaction.user.name,
                "author_id": interaction.user.id,
                "content": (("**Statutes at issue:** " + self.statutes_at_issue.value + "\n\n") if self.statutes_at_issue.value.strip() else "") + self.complaint_text.value,
                "timestamp": interaction.created_at.isoformat(),
            }],
        }

        # Auto-seed counsel-of-record for the plaintiff/prosecution on filing
        cofr = court_data[case_number].setdefault("counsel_of_record", {})
        pid = court_data[case_number].get("plaintiff")
        if isinstance(pid, int):  # civil plaintiff is a user
            cofr[str(pid)] = interaction.user.id
        # (If criminal, plaintiff is a string like "The Spidey Republic", so we can’t key by user id.)


        # 4) Compose summary ONCE using formatted parties
        venue_channel = self.bot.get_channel(venue_channel_id)
        if self.criminal:
            prose_pl = plaintiff_stored  # string
            header = "📁 **New Criminal Complaint Filed**"
            lines = [
                f"**Case Number:** `{case_number}`",
                f"**Prosecution:** {prose_pl}",
                f"**Defendant:** {self.format_party(interaction.guild, df_val)}",
            ]
        else:
            header = "📁 **New Complaint Filed**"
            lines = [
                f"**Case Number:** `{case_number}`",
                f"**Plaintiff:** {self.format_party(interaction.guild, pl_val)}",
                f"**Defendant:** {self.format_party(interaction.guild, df_val)}",
            ]
        if extra_vals:
            lines.append("**Additional Defendants:** " + ", ".join(self.format_party(interaction.guild, v) for v in extra_vals))
        lines.append(f"Filed by: {interaction.user.mention}")

        summary = header + "\n" + "\n".join(lines)
        await venue_channel.send(summary)

        filing_msg = await venue_channel.send(f"**Complaint Document - {case_number}**\n\n{self.complaint_text.value}")
        court_data[case_number]["filings"][0]["message_id"] = filing_msg.id
        court_data[case_number]["filings"][0]["channel_id"] = filing_msg.channel.id

        save_json(COURT_FILE, court_data)
        await interaction.response.send_message(f"✅ Complaint filed under `{case_number}`.", ephemeral=True)

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

        self.summary = discord.ui.TextInput(
            label="Syllabus / Summary (optional)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1500,
            placeholder="(Supreme: Syllabus) (Others: summary)"
        )
        self.add_item(self.summary)

        # (Keep your keywords/tags field if you want)
        self.keywords = discord.ui.TextInput(
            label="Keywords (comma-separated)",
            style=discord.TextStyle.short,
            required=False,
            max_length=200
        )
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
        caption = await cog._caption_from_parties(guild, case)

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

        label = "Syllabus" if rep_key == "supreme" else "Summary"
        if str(self.summary.value or "").strip():
            starter += f"**{label} (not part of the opinion)**\n{self.summary.value.strip()}\n\n"

        if str(self.keywords.value or "").strip():
            starter += f"*Keywords:* {self.keywords.value.strip()}\n\n"

        starter += "*Opinion follows in paginated messages below.*"

        pages = cog._paginate_for_reporter(opinion, TARGET_CHARS_PER_PAGE, start_page=first_page)
        num_pages = len(pages)
        if num_pages == 0:
            return await interaction.followup.send("❌ Opinion text is empty.", ephemeral=True)

        # Create thread (works with Thread or ThreadWithMessage)
        created = await forum.create_thread(
            name=f"{caption} — {citation}",
            content=starter,
            allowed_mentions=discord.AllowedMentions.none()
        )
        thread = getattr(created, "thread", created)
        starter_msg = getattr(created, "message", None)

        page_message_ids = []
        try:
            for pg in pages:
                m = await thread.send(pg, allowed_mentions=discord.AllowedMentions.none())
                page_message_ids.append(m.id)
        except Exception as e:
            # abort and clean up — DO NOT advance pointers
            try:
                await thread.delete(reason=f"Reporter publish failed: {e}")
            except Exception:
                pass
            return await interaction.followup.send(f"❌ Failed while posting pages: {e}", ephemeral=True)

        # --- COMMIT ONLY AFTER SUCCESS ---
        rep_bucket["opinions"].append({
            "case_number": self.case_number,
            "entry": self.entry,
            "caption": caption,
            "year": year,
            "volume": vol,
            "first_page": first_page,
            "pages": num_pages,
            "thread_id": thread.id,
            "starter_message_id": (starter_msg.id if starter_msg else None),
            "page_message_ids": page_message_ids,
            "keywords": [k.strip() for k in (self.keywords.value or "").split(",") if k.strip()],
        })
        rep_bucket["current_page"] = first_page + num_pages  # advance pointer now that it's real

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

class DocketView(discord.ui.View):
    def __init__(self, pages: list[str], user_id: int):
        super().__init__(timeout=300)
        self.pages = pages
        self.index = 0
        self.user_id = user_id
        # disable prev on first render
        self.prev_button.disabled = True
        if len(self.pages) == 1:
            self.next_button.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the invoker can page
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the requester can use these controls.", ephemeral=True)
            return False
        return True

    def _content(self) -> str:
        footer = f"\n\n— Page {self.index+1}/{len(self.pages)} —"
        return self.pages[self.index] + footer

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        self.prev_button.disabled = (self.index == 0)
        self.next_button.disabled = (self.index >= len(self.pages)-1)
        await interaction.response.edit_message(content=self._content(), view=self, allowed_mentions=discord.AllowedMentions.none())

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages)-1:
            self.index += 1
        self.prev_button.disabled = (self.index == 0)
        self.next_button.disabled = (self.index >= len(self.pages)-1)
        await interaction.response.edit_message(content=self._content(), view=self, allowed_mentions=discord.AllowedMentions.none())

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="(closed)", view=self)
        self.stop()


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
        if not self.court_data: return
        channel = self.bot.get_channel(ONGOING_CASES_CHANNEL_ID)
        if not channel: return

        ongoing = []
        for case_number, data in self.court_data.items():
            if case_number.startswith("_"): continue
            if not isinstance(data, dict): continue
            if data.get("status") == "closed": continue
            if "plaintiff" not in data or "defendant" not in data or "filings" not in data: continue
            # NEW: normalize legacy -> parties so caption renders
            await self._normalize_case(channel.guild, data)
            ongoing.append((case_number, data))

        if not ongoing: return
        message = "**Ongoing Court Cases:**\n"
        for case_number, case_data in ongoing:
            latest = case_data['filings'][-1] if case_data.get('filings') else {}
            cap = await self._caption_from_parties(channel.guild, case_data)
            message += f"- `{cap}`, {case_number} (Most recent: {latest.get('document_type', 'Unknown')})\n"

        meta = self.court_data.setdefault("_meta", {})
        msg_id = meta.get("ongoing_cases_msg_id")
        try:
            if msg_id:
                existing = await channel.fetch_message(int(msg_id))
                await existing.edit(content=message, allowed_mentions=discord.AllowedMentions.none())
            else:
                new_msg = await channel.send(message, allowed_mentions=discord.AllowedMentions.none())
                meta["ongoing_cases_msg_id"] = new_msg.id
                save_json(COURT_FILE, self.court_data)
        except (discord.NotFound, discord.Forbidden):
            new_msg = await channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            meta["ongoing_cases_msg_id"] = new_msg.id
            save_json(COURT_FILE, self.court_data)
        
    @show_cases.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()

    # ---------- Long text posting ----------
    def _chunks(self, s: str, n: int):
        for i in range(0, len(s), n):
            yield s[i:i+n]

    async def _post_long_text(self, 
        channel: discord.abc.Messageable,
        title: str,
        body: str,
        color: discord.Color = discord.Color.dark_teal(),
        make_thread: bool = True,
        delay: float = 0.4,  # rate-limit cushion
    ):
        """
        Post an embed header + chunked text messages under it (optionally in a thread).
        Returns dict with ids.
        """
        head = await channel.send(
            embed=discord.Embed(title=title, color=color)
        )
        target = await head.create_thread(name=title) if make_thread else channel

        # We prefer embeds for readability, but descriptions cap at 4096.
        CHUNK = 3800  # leave headroom for formatting
        for i, part in enumerate(_chunks(body, CHUNK), start=1):
            e = discord.Embed(
                title=None if not make_thread else f"Part {i}",
                description=part,
                color=color
            )
            await target.send(embed=e)
            await asyncio.sleep(delay)

        return {
            "message_id": head.id,
            "channel_id": getattr(channel, "id", None),
            "thread_id": getattr(target, "id", None) if make_thread else None,
        }


    def _eligible_juror_members(
        self,
        guild: discord.Guild,
        pool_role: discord.Role,
        exclude_ids: set[int],
    ) -> list[discord.Member]:
        """Pool = role members minus bots, judiciary, excluded."""
        judiciary_role = guild.get_role(FED_JUDICIARY_ROLE_ID)
        out = []
        for m in pool_role.members:
            if m.bot:
                continue
            if m.id in exclude_ids:
                continue
            if judiciary_role and judiciary_role in m.roles:
                continue
            out.append(m)
        return out

    

    def _short_date(self, iso: str) -> str:
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%m/%d/%y")
        except Exception:
            return iso[:10]

    def _entry_link(self, doc: dict) -> str | None:
        ch_id = doc.get("channel_id")
        msg_id = doc.get("message_id")
        if not ch_id or not msg_id:
            return None
        # Prefer thread if present
        thread_id = doc.get("thread_id")
        channel_id = thread_id or ch_id
        guild_id = getattr(self.bot.guilds[0], "id", 0) if self.bot.guilds else 0
        return f"https://discord.com/channels/1287645024309477460/{channel_id}/{msg_id}"

    def _format_docket_lines(self, case_number: str, case: dict, viewer: discord.Member) -> list[str]:
        """Build per-entry lines (newest first). Keeps exhibits under their parent."""
        lines = []
        filings = list(case.get("filings", []))
        filings.sort(key=lambda d: d.get("entry", 0), reverse=True)

        # (Optional sealed visibility—comment out if you don't use sealing)
        judge_role_id = FED_JUDICIARY_ROLE_ID
        is_judge = any(r.id == judge_role_id for r in getattr(viewer, "roles", []))
        party_ids = self._collect_party_ids(case)

        for doc in filings:
            # Sealed logic (hide content for non-privileged)
            sealed = doc.get("sealed")
            can_see = is_judge or (viewer.id in party_ids) or (viewer.id == doc.get("author_id"))
            ts = self._short_date(doc.get("timestamp", ""))

            if sealed and not can_see:
                lines.append(f"[{doc.get('entry')}] [SEALED] — filed {ts}")
                continue

            author = doc.get("author") or "Unknown"
            url = self._entry_link(doc)
            if url:
                document = "[" + doc.get("document_type", "Document") + "](" + url + ")"
            else:
                document = doc.get("document_type", "Document")
            head = f"[{doc.get('entry')}] {document} by {author} on {ts}"
            # Related docs tag (single-line, compact)
            if doc.get("related_docs"):
                head += f" (Related to: Entry {', '.join(str(x) for x in doc['related_docs'])})"

            
            

            lines.append(head)

            # Exhibits (keep under parent, not reversed)
            for ex in doc.get("exhibits", []):
                ex_desc = ex.get("text", "")
                ex_num = ex.get("number") or ex.get("exhibit_number") or "1"
                lines.append(f"    ↳ Exhibit {ex_num}: {ex_desc}")

        return lines

    def _build_docket_pages(self, header: str, lines: list[str], max_chars: int = 1900) -> list[str]:
        """Pack lines into pages under the limit (header repeated each page)."""
        pages, buf = [], ""
        for ln in lines:
            piece = (ln + "\n")
            # new page if adding would overflow
            if len(header) + len(buf) + len(piece) > max_chars:
                pages.append(header + buf.rstrip())
                buf = ""
            buf += piece
        if buf.strip():
            pages.append(header + buf.rstrip())
        if not pages:
            pages = [header + "_No filings yet._"]
        return pages


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

    def _paginate_for_reporter(self, text: str, max_chars: int = TARGET_CHARS_PER_PAGE, start_page: int = 1):
        """Split opinion text into fake 'pages' and prefix each with [*n]."""
        chunks, page, buf = [], start_page, ""
        paras = [p.strip() for p in (text or "").split("\n\n")]
        for para in paras:
            if not para:
                continue
            parts = textwrap.wrap(para, width=max_chars, replace_whitespace=False, drop_whitespace=False)
            for part in parts:
                if len(buf) + len(part) + 2 > max_chars:
                    chunks.append(f"`[*{page}]`\n{buf.strip()}")
                    page += 1
                    buf = part + "\n\n"
                else:
                    buf += part + "\n\n"
        if buf.strip():
            chunks.append(f"`[*{page}]`\n{buf.strip()}")
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
    
   

    def _coerce_user_id(self, val) -> int | None:
        """Return numeric user id if extractable (int, <@id>, '123'), else None."""
        if val is None:
            return None
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            s = val.strip()
            if s.isdigit():
                return int(s)
            m = MENTION_RX.match(s)
            if m:
                return int(m.group("id"))
        return None

    def _collect_party_ids(self, case: dict) -> set[int]:
        """Collect all numeric IDs for sealing/visibility checks."""
        ids: set[int] = set()
        for key in ("plaintiff", "defendant"):
            pid = self._coerce_user_id(case.get(key))
            if pid:
                ids.add(pid)
        for key in ("additional_plaintiffs", "additional_defendants"):
            for v in (case.get(key) or []):
                pid = self._coerce_user_id(v)
                if pid:
                    ids.add(pid)
        # optional: include counsel-of-record values if present
        cor = case.get("counsel_of_record") or {}
        if isinstance(cor, dict):
            for v in cor.values():
                pid = self._coerce_user_id(v)
                if pid:
                    ids.add(pid)
        return ids



    async def _party_label(self, guild: discord.Guild, value) -> str:
        """
        Return a display-ready label for a party that may be:
        - int / numeric str → Discord user id
        - raw string → org/class text
        """
        # Try to coerce discord user id first
        def _maybe_int(x):
            try:
                return int(str(x))
            except Exception:
                return None

        pid = _maybe_int(value)
        if pid:
            return await self.try_get_display_name(guild, pid)
        return str(value or "Unknown")

    async def _caption(self, guild: discord.Guild, case: dict) -> str:
        """
        Compute the caption using optional overrides:
        case["caption"] = {"style": "v"|"in_re", "left": "...", "right": "...?"}
        """
        cap = case.get("caption") or {}
        style = (cap.get("style") or case.get("caption_style") or "v").lower()

        left = cap.get("left")
        right = cap.get("right")

        if not left:
            left = await self._party_label(guild, case.get("plaintiff"))

        if style == "in_re":
            return f"In re {left}"

        if not right:
            right = await self._party_label(guild, case.get("defendant"))

        return f"{left} v. {right}"
    
    async def _normalize_case(self, guild: discord.Guild, case: dict) -> None:
        # 1) If new structure is missing, build from legacy fields
        parties = case.setdefault("parties", {})
        if "plaintiffs" not in parties or "defendants" not in parties:
            plaintiffs = []
            defendants = []
            # Legacy singletons
            legacy_pl = case.get("plaintiff")
            legacy_df = case.get("defendant")
            # Legacy lists
            legacy_pls = case.get("additional_plaintiffs", []) or []
            legacy_dfs = case.get("additional_defendants", []) or []

            async def _mk_party(x, default_kind="org"):
                # @mention / id ⇒ user; else text ⇒ org/class/text
                uid = await self._maybe_user_id(x)
                if uid:
                    disp = await self.try_get_display_name(guild, uid)
                    return Party(id=uid, name=disp, kind="user", pid=_uuid()).to_dict()
                s = str(x).strip()
                kind = default_kind
                low = s.lower()
                if low.startswith("class:"):
                    s = s.split(":",1)[1].strip(); kind="class"
                elif low.startswith("org:"):
                    s = s.split(":",1)[1].strip(); kind="org"
                elif low.startswith("state:"):
                    s = s.split(":",1)[1].strip(); kind="state"
                return Party(id=None, name=s, kind=kind, pid=_uuid()).to_dict()

            if legacy_pl: plaintiffs.append(await _mk_party(legacy_pl))
            for x in legacy_pls: plaintiffs.append(await _mk_party(x))
            if legacy_df: defendants.append(await _mk_party(legacy_df))
            for x in legacy_dfs: defendants.append(await _mk_party(x))

            parties["plaintiffs"] = plaintiffs or []
            parties["defendants"] = defendants or []

        # Ensure attorneys array + pid exists
        for side in ("plaintiffs", "defendants"):
            clean = []
            for p in parties.get(side, []):
                p.setdefault("pid", _uuid())
                p.setdefault("attorneys", [])
                clean.append(p)
            parties[side] = clean


    async def _maybe_user_id(self, value) -> int | None:
        try:
            s = str(value).strip()
            if s.startswith("<@") and s.endswith(">"):
                return int("".join(c for c in s if c.isdigit()))
            return int(s)
        except Exception:
            return None

    async def _party_dict_label(self, guild: discord.Guild, p: dict) -> str:
        # Refresh label for users to current display; keep org/class as saved
        if p.get("kind") == "user" and p.get("id"):
            disp = await self.try_get_display_name(guild, int(p["id"]))
            if disp and disp != p.get("name"):
                p["name"] = disp
        return p.get("name") or "Unknown"

    async def _caption_from_parties(self, guild: discord.Guild, case: dict) -> str:
        cap = (case.get("caption") or {}).copy()
        style = (cap.get("style") or "v").lower()
        parties = case.get("parties", {})
        pls = parties.get("plaintiffs", [])
        dfs = parties.get("defendants", [])

        if style == "in_re":
            left = cap.get("left")
            if not left:
                left = await self._party_dict_label(guild, pls[0]) if pls else "Matter"
            return f"In re {left}"

        # "v." style
        left = cap.get("left") or (await self._party_dict_label(guild, pls[0]) if pls else "Unknown")
        right = cap.get("right") or (await self._party_dict_label(guild, dfs[0]) if dfs else "Unknown")
        return f"{left} v. {right}"


    
    court = app_commands.Group(name="court", description="Court related commands")

    def is_judge(self, interaction: discord.Interaction) -> bool:
        return any(role.id == FED_JUDICIARY_ROLE_ID for role in interaction.user.roles)


    
    @court.command(name="file_complaint", description="File a new complaint")
    @app_commands.describe(
        plaintiff="Plaintiff (ignored if criminal=True)",
        plaintiff_user="Plaintiff is a discord member",
        defendant="Defendant",
        defendant_user="Defendant is a discord member",
        venue="Venue for the complaint",
        criminal="Is this a criminal complaint?",
        government="Government name or level (e.g. 'country' to use default)"
    )
    @app_commands.choices(
        venue=[
            app_commands.Choice(name="Commons District Court", value="gen_chat"),
            app_commands.Choice(name="Gaming District Court", value="swgoh"),
            app_commands.Choice(name="District of Parker District Court", value="public_square"),
            app_commands.Choice(name="First Circuit", value="first_circuit"),
            app_commands.Choice(name="Supreme Court", value="ssc"),
        ]
    )
    async def file_complaint(
        self,
        interaction: discord.Interaction,
        venue: str,
        plaintiff: str | None = None,
        defendant: str | None = None,
        plaintiff_user: discord.Member | None = None,
        defendant_user: discord.Member | None = None,
        criminal: bool = False,
        government: str | None = None,
    ):
        # basic validation (civil must have distinct sides)
        if not criminal:
            if (plaintiff is None and plaintiff_user is None):
                return await interaction.response.send_message("❌ Civil filing requires distinct plaintiff and defendant.", ephemeral=True)
        if defendant is None and defendant_user is None:
            return await interaction.response.send_message("❌ Defendant is required.", ephemeral=True)

        # merge text+member into one display string per side
        if plaintiff_user:
            plaintiff = plaintiff_user.display_name if not plaintiff else f"{plaintiff_user.display_name} and {plaintiff}"
        if defendant_user:
            defendant = defendant_user.display_name if not defendant else f"{defendant_user.display_name} and {defendant}"

        await interaction.response.send_modal(
            ComplaintFilingModal(
                self.bot, venue, plaintiff, defendant, criminal=criminal, government=government
            )
        )
    
    def _coerce_user_id(self, value) -> int | None:
        """Return an int user id if value looks like one (raw int/str/mention), else None."""
        if value is None:
            return None
        try:
            s = str(value).strip()
            if s.startswith("<@") and s.endswith(">"):
                # <@123> or <@!123>
                digits = "".join(ch for ch in s if ch.isdigit())
                return int(digits) if digits else None
            return int(s)
        except Exception:
            return None


    # put this near the top of class SpideyCourts
    async def case_autocomplete(self, interaction: discord.Interaction, current: str):
        """
        Ultra-fast autocomplete:
        - zero awaits in the loop (no guild fetches, no normalization)
        - derives a caption from stored fields only
        - searches case number, caption text, visible party names, and raw COR IDs
        """
        q = (current or "").lower()
        out = []
        MAX_CHOICES = 25

        def name_from_value(v):
            """Fast, non-mention label for a party value."""
            if v is None:
                return "Unknown"
            s = str(v).strip()
            # If it's a user id, try guild cache for display_name; never return a mention
            if s.isdigit():
                mem = interaction.guild.get_member(int(s))
                if mem:
                    return mem.display_name  # cached, instant
                return f"User {s}"  # fallback when not in cache / no intents
            # If it's already a saved string (org/class/state), keep it
            return s


        def fast_caption(case: dict) -> str:
            cap = (case.get("caption") or {}).copy()
            style = (cap.get("style") or "v").lower()

            # Prefer prebuilt party names if present (they're already strings)
            parties = case.get("parties") or {}
            pls = parties.get("plaintiffs") or []
            dfs = parties.get("defendants") or []

            if style == "in_re":
                left = cap.get("left") or (pls[0].get("name") if pls else None) or name_from_value(case.get("plaintiff"))
                return f"In re {left or 'Matter'}"

            left = cap.get("left") or (pls[0].get("name") if pls else None) or name_from_value(case.get("plaintiff"))
            right = cap.get("right") or (dfs[0].get("name") if dfs else None) or name_from_value(case.get("defendant"))
            return f"{left or 'Unknown'} v. {right or 'Unknown'}"

        for case_number, case in self.court_data.items():
            if not isinstance(case, dict) or case_number.startswith("_"):
                continue

            cap = fast_caption(case)

            # Build a tiny haystack (all local strings; no awaits)
            hay = [case_number.lower(), cap.lower()]

            # Party names if already stored
            parties = case.get("parties") or {}
            for side in ("plaintiffs", "defendants"):
                for p in parties.get(side, []) or []:
                    n = (p.get("name") or "").lower()
                    if n: hay.append(n)

            # Raw counsel-of-record IDs (we skip display lookups to stay fast)
            for _, lawyer_id in (case.get("counsel_of_record") or {}).items():
                s = str(lawyer_id)
                if s: hay.append(s.lower())

            if not q or any(q in chunk for chunk in hay):
                out.append(app_commands.Choice(name=f"{cap}, {case_number}", value=case_number))

    
        out.reverse()  # prefer newer cases if over limit
        out = out[:MAX_CHOICES] # cut to max after reversing

        return out



    
    @court.command(name="view_docket", description="View the docket for a case (paginated).")
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.describe(case_number="Case number")
    async def view_docket(self, interaction: discord.Interaction, case_number: str):
        await interaction.response.defer(ephemeral=False)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        # Header: caption, counsel, venue, judge (names)
        guild = interaction.guild
        await self._normalize_case(guild, case)
        venue_name = VENUE_NAMES.get(case.get("venue"), case.get("venue"))
        judge = await self.try_get_display_name(guild, case.get("judge_id")) or case.get("judge") or "Unknown"

        counsel_pl = None
        counsel_df = None
        cor = case.get("counsel_of_record", {})
        pl_id = self._coerce_user_id(case.get("plaintiff"))
        df_id = self._coerce_user_id(case.get("defendant"))
        if pl_id and str(pl_id) in cor:
            counsel_pl = await self.try_get_display_name(guild, int(cor[str(pl_id)]))
        if df_id and str(df_id) in cor:
            counsel_df = await self.try_get_display_name(guild, int(cor[str(df_id)]))

        # Fallbacks to legacy fields so new filings show counsel immediately
        if not counsel_pl:
            legacy_pl = self._coerce_user_id(case.get("counsel_for_plaintiff"))
            if legacy_pl:
                counsel_pl = await self.try_get_display_name(guild, legacy_pl)

        if not counsel_df:
            legacy_df = self._coerce_user_id(case.get("counsel_for_defendant"))
            if legacy_df:
                counsel_df = await self.try_get_display_name(guild, legacy_df)

        is_criminal = case.get("is_criminal", False)


        caption = await self._caption_from_parties(guild, case)

        header = (
            f"**Docket for Case {caption}, {case_number}**\n\n"
            f"Counsel for {'Plaintiff' if not is_criminal else 'Prosecution'}: {counsel_pl or '<@Unknown>'}\n"
            f"Counsel for Defendant: {counsel_df or '<@Unknown>'}\n"
            f"Venue: {venue_name}\n"
            f"Judge: {judge}\n"
        )
        header += "\n"  # spacer

        # Lines & pages
        lines = self._format_docket_lines(case_number, case, interaction.user)
        pages = self._build_docket_pages(header, lines, max_chars=1900)

        view = DocketView(pages=pages, user_id=interaction.user.id)
        await interaction.followup.send(
            content=view._content(),
            view=view,
            allowed_mentions=discord.AllowedMentions.none()
        )


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
        file="Upload .pdf/.docx/.txt/etc. to bypass modal for long orders",
        summary="(Optional) One-line docket summary"
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
        file: discord.Attachment | None = None,
        summary: str | None = None,
    ):
        # guard: case + assigned judge check (unchanged)
        case = self.court_data.get(case_number)
        if not case:
            await interaction.response.send_message("❌ Case not found.", ephemeral=True)
            return
        cid = case.get("judge_id")
        if cid and int(cid) != interaction.user.id:
            await interaction.response.send_message("❌ Only the assigned judge may issue orders in this case.", ephemeral=True)
            return

        # If no file, keep your modal path EXACTLY
        if file is None:
            return await interaction.response.send_modal(
                OrderModal(
                    bot=self.bot,
                    case_number=case_number,
                    order_type=order_type.value,
                    related_entry=related_entry,
                    outcome=(outcome.value if outcome else None),
                )
            )

        # File path: extract text, then post using your existing long/short logic
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            content = await _read_attachment_text(file)
        except Exception as e:
            return await interaction.followup.send(f"❌ Couldn’t read the file: {e}", ephemeral=True)

        if not content:
            return await interaction.followup.send("❌ The uploaded file contained no extractable text.", ephemeral=True)

        # venue channel (same as modal)
        venue_key = case.get("venue")
        ch_id = VENUE_CHANNEL_MAP.get(venue_key)
        venue_ch = self.bot.get_channel(ch_id) if ch_id else None
        if not venue_ch:
            return await interaction.followup.send("❌ Venue channel not found.", ephemeral=True)

        title_head = f"{order_type.value} — {case_number}"

        try:
            if len(content) <= 1800:
                msg = await venue_ch.send(
                    f"**{title_head}**\n" + (f"*{summary}*\n\n" if summary else "\n") + content,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                thread_id = None
            else:
                # reuse your *_post_long_filing* helper (keeps behavior consistent with modal)
                msg, thread = await self._post_long_filing(
                    court_channel=venue_ch,
                    title=title_head,
                    case_number=case_number,
                    author=interaction.user,
                    content=(f"{summary}\n\n{content}" if summary else content),
                )
                thread_id = thread.id
        except Exception as e:
            return await interaction.followup.send(f"❌ Failed to post the order: {e}", ephemeral=True)

        # Docket entry — mirror your modal schema
        filings = case.setdefault("filings", [])
        entry_no = len(filings) + 1
        doc = {
            "entry": entry_no,
            "document_type": order_type.value,
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": msg.id,
            "channel_id": msg.channel.id,
            "content": (f"Outcome: {outcome.value}" if outcome else None),
        }
        if thread_id:
            doc["thread_id"] = thread_id
        if related_entry:
            doc["related_docs"] = [related_entry]

        filings.append(doc)

        # Resolve the related motion, if any (same behavior as modal)
        if related_entry:
            rel = next((d for d in filings if d.get("entry") == related_entry), None)
            if rel:
                rel["resolved"] = True
                if outcome:
                    rel["ruling_outcome"] = outcome.value

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ {order_type.value} docketed as Entry {entry_no}.", ephemeral=True)




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
            cap = await self._caption_from_parties(interaction.guild, case)
            await interaction.channel.send(
                f"🗂️ Calling case `{case_number}`: **{cap}**.\n"
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

    @court.command(name="counsel", description="Substitute or withdraw as counsel for a specific party.")
    @app_commands.choices(action=[
        app_commands.Choice(name="Substitute", value="substitute"),
        app_commands.Choice(name="Withdraw", value="withdraw"),
    ])
    @app_commands.describe(
        case_number="Case number",
        action="Choose substitute or withdraw",
        party="Party represented (user)",
        new_counsel="New counsel user (required for Substitute)"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    async def counsel(
        self,
        interaction: discord.Interaction,
        case_number: str,
        action: app_commands.Choice[str],
        party: discord.Member,
        new_counsel: discord.Member | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        if not await self._party_is_in_case(case, party.id):
            return await interaction.followup.send("❌ That user is not a party in this case.", ephemeral=True)

        filings = case.setdefault("filings", [])
        entry = len(filings) + 1

        if action.value == "substitute":
            if new_counsel is None:
                return await interaction.followup.send("❌ For Substitute, provide `new_counsel`.", ephemeral=True)
            cofr = case.setdefault("counsel_of_record", {})
            prev = cofr.get(str(party.id))
            cofr[str(party.id)] = new_counsel.id
            filings.append({
                "entry": entry,
                "document_type": "Substitution of Counsel",
                "author": interaction.user.name,
                "author_id": interaction.user.id,
                "timestamp": datetime.now(UTC).isoformat(),
                "content": f"{(await self.try_get_display_name(interaction.guild, party.id))}: "
                        f"{('from ' + (await self.try_get_display_name(interaction.guild, prev)) + ' ') if prev else ''}"
                        f"to {new_counsel.display_name}"
            })
            save_json(COURT_FILE, self.court_data)
            return await interaction.followup.send("✅ Substitution recorded.", ephemeral=True)

        if action.value == "withdraw":
            cofr = case.get("counsel_of_record", {})
            if str(party.id) not in cofr:
                return await interaction.followup.send("❌ No counsel of record to withdraw.", ephemeral=True)
            prev = cofr.pop(str(party.id), None)
            filings.append({
                "entry": entry,
                "document_type": "Withdrawal of Counsel",
                "author": interaction.user.name,
                "author_id": interaction.user.id,
                "timestamp": datetime.now(UTC).isoformat(),
                "content": f"{(await self.try_get_display_name(interaction.guild, party.id))}: "
                        f"withdrew { (await self.try_get_display_name(interaction.guild, prev)) if prev else 'counsel' }"
            })
            save_json(COURT_FILE, self.court_data)
            return await interaction.followup.send("✅ Withdrawal recorded.", ephemeral=True)

        return await interaction.followup.send("❌ Unknown action.", ephemeral=True)


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

    @court.command(name="reporter_preview", description="Preview citation and page count before publishing.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(reporter_override=[
        app_commands.Choice(name="District (SPIDEYLAW)", value="district"),
        app_commands.Choice(name="Circuit (F.)", value="circuit"),
        app_commands.Choice(name="Supreme (S.R.)", value="supreme"),
    ])
    async def reporter_preview(self, interaction: discord.Interaction, case_number: str, entry: int, reporter_override: app_commands.Choice[str] | None = None):
        await interaction.response.defer(ephemeral=True)
        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        rep_key = reporter_override.value if reporter_override else self._get_reporter_for_case(case)
        rep_root = self._ensure_reporter(); bucket = rep_root[rep_key]
        opinion = await self._gather_opinion_text_from_docket(case, entry)
        if not opinion:
            return await interaction.followup.send("❌ Couldn’t locate opinion text.", ephemeral=True)
        pages = self._paginate_for_reporter(opinion, TARGET_CHARS_PER_PAGE)
        num = len(pages)
        vol, first_page, year = bucket["current_volume"], bucket["current_page"], datetime.now(UTC).year
        abbr = REPORTERS[rep_key]["abbr"]
        paren = self._court_parenthetical(case, rep_key)
        cite = self._make_citation(abbr, vol, first_page, year, court_paren=paren)
        await interaction.followup.send(f"📘 **Preview**: will publish as `{cite}` and use **{num} page(s)** (ending at p. {first_page+num-1}).", ephemeral=True)


    @court.command(name="reporter_retract", description="Retract a published opinion (last-only to preserve page numbering).")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        citation="e.g., '1 F. 12' or '1 S.R. 1' (preferred)",
        thread_id="Alternative: the reporter thread ID"
    )
    async def reporter_retract(self, interaction: discord.Interaction, citation: str | None = None, thread_id: str | None = None):
        await interaction.response.defer(ephemeral=True)

        rep_root = self._ensure_reporter()
        target_bucket = None
        idx = None
        op = None

        # Find by citation if provided
        if citation:
            m = CITE_MULTI_RX.match(citation or "")
            if not m:
                return await interaction.followup.send("❌ Bad citation. Try `1 S.R. 1` or `1 F. 22` or `1 SPIDEYLAW 100`.", ephemeral=True)
            vol = int(m.group(1))
            rep_key = self._abbr_to_reporter_key(m.group(2))
            first_page = int(m.group(3))
            if not rep_key:
                return await interaction.followup.send("❌ Unknown reporter abbr.", ephemeral=True)
            bucket = rep_root.get(rep_key) or {}
            opinions = bucket.get("opinions", [])
            for i, o in enumerate(opinions):
                if o.get("volume") == vol and o.get("first_page") == first_page:
                    target_bucket, idx, op = bucket, i, o
                    break
            if not op:
                return await interaction.followup.send("❌ Citation not found in the reporter.", ephemeral=True)

        # Or find by thread id
        elif thread_id:
            for key, bucket in rep_root.items():
                if key not in ("district", "circuit", "supreme"):  # skip non-buckets
                    continue
                opinions = bucket.get("opinions", [])
                for i, o in enumerate(opinions):
                    if str(o.get("thread_id")) == str(thread_id):
                        target_bucket, idx, op = bucket, i, o
                        break
                if op:
                    break
            if not op:
                return await interaction.followup.send("❌ Thread not found in any reporter.", ephemeral=True)
        else:
            return await interaction.followup.send("Provide either `citation` or `thread_id`.", ephemeral=True)

        # Only allow retracting the last published opinion to protect page numbering
        if idx != len(target_bucket["opinions"]) - 1:
            return await interaction.followup.send("❌ Can only retract the most recent opinion in that reporter (to preserve citations).", ephemeral=True)

        # Delete the forum thread
        thread = self.bot.get_channel(int(op.get("thread_id")))
        if thread:
            try:
                await thread.delete(reason="Reporter retract")
            except Exception:
                pass

        # Roll back the pointer and remove the opinion
        start = op.get("first_page", target_bucket["current_page"])
        num = op.get("pages", 0)
        target_bucket["current_page"] = start
        target_bucket["opinions"].pop()

        self.court_data[REPORTER_KEY] = rep_root
        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ Retracted. Page pointer reset to **p. {start}**.", ephemeral=True)

    @court.command(name="jury_select", description="Summon a random jury from the government pool.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.describe(
        case_number="Case number (e.g., 1:25-cv-000001-SS)",
        size="Number of jurors to summon (default 12)",
        alternates="Number of alternates (default 2)",
        replace="Replace existing panel if one already exists",
        pool_role="Override the default pool (defaults to GOVERNMENT_ROLE_ID)"
    )
    async def jury_select(
        self,
        interaction: discord.Interaction,
        case_number: str,
        size: int = 12,
        alternates: int = 2,
        replace: bool = False,
        pool_role: discord.Role | None = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("❌ Must be used in a guild.", ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        # Only the assigned judge may run this (optional but recommended)
        cid = case.get("judge_id")
        if cid and int(cid) != interaction.user.id:
            return await interaction.followup.send("❌ Only the assigned judge may select jurors.", ephemeral=True)

        # Decide pool role
        role = pool_role or guild.get_role(GOVERNMENT_ROLE_ID)
        if not role:
            return await interaction.followup.send("❌ Government role not found.", ephemeral=True)

        # Build exclusions: parties, counsel, judge, bot, invoker
        exclude_ids = self._collect_party_ids(case)
        if cid:
            exclude_ids.add(int(cid))
        exclude_ids.add(self.bot.user.id)
        exclude_ids.add(interaction.user.id)

        # Candidates
        candidates = self._eligible_juror_members(guild, role, exclude_ids)
        needed = max(0, size) + max(0, alternates)
        if not candidates:
            return await interaction.followup.send("❌ No eligible members in the pool.", ephemeral=True)

        if len(candidates) < needed:
            # don’t fail; just trim the target numbers
            if len(candidates) <= 0:
                return await interaction.followup.send("❌ No eligible members after exclusions.", ephemeral=True)
            # shrink alternates first, then panel
            short = needed - len(candidates)
            take_alts = max(0, alternates - short)
            # if still short, reduce size
            remaining_short = max(0, short - alternates)
            take_size = max(1, size - remaining_short)  # at least 1 juror
            size, alternates = take_size, take_alts

        # Respect existing panel unless replace=True
        jury = case.setdefault("jury", {})
        if jury.get("panel") and not replace:
            return await interaction.followup.send(
                "⚠️ Panel already exists. Pass `replace=True` to overwrite.", ephemeral=True
            )

        picks = random.sample(candidates, k=size + alternates)
        panel_members = picks[:size]
        alt_members = picks[size:]

        # Save jury info
        jury["panel"] = [m.id for m in panel_members]
        jury["alternates"] = [m.id for m in alt_members]
        jury["pool_role_id"] = role.id
        jury["summoned_at"] = datetime.now(UTC).isoformat()
        jury.setdefault("summons_log", [])
        jury.setdefault("responses", {})  # future: accept/decline tracking
        case["jury"] = jury
        save_json(COURT_FILE, self.court_data)

        # Notify each pick: DM first; fallback to courthouse steps mention
        dm_ok = 0
        public_ok = 0
        steps_ch = self.bot.get_channel(COURT_STEPS_CHANNEL_ID)
        for m in panel_members + alt_members:
            method = "dm"
            channel_id = None
            message_id = None
            try:
                dm = await m.send(
                    f"📨 **Jury Summons**\nYou are summoned for jury service in **{case_number}**.\n"
                    f"Venue: {VENUE_NAMES.get(case.get('venue'), case.get('venue'))}\n"
                    f"Presiding Judge: {await self.try_get_display_name(guild, case.get('judge_id')) or 'Unknown'}\n\n"
                    f"Please be available for voir dire and further instructions.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                dm_ok += 1
                channel_id = dm.channel.id
            except Exception:
                method = "public"
                if isinstance(steps_ch, discord.TextChannel):
                    msg = await steps_ch.send(
                        f"{m.mention} — You are summoned for jury service in **{case_number}**. "
                        f"Please see the court channels for details.",
                        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
                    )
                    public_ok += 1
                    channel_id = steps_ch.id
                    message_id = msg.id

            jury["summons_log"].append({
                "user_id": m.id,
                "method": method,
                "channel_id": channel_id,
                "message_id": message_id,
                "timestamp": datetime.now(UTC).isoformat(),
            })

        # Optional: docket entry
        filings = case.setdefault("filings", [])
        filings.append({
            "entry": len(filings) + 1,
            "document_type": "Jury Summons Issued",
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"Summoned {len(panel_members)} jurors and {len(alt_members)} alternates from @{role.name}.",
        })
        save_json(COURT_FILE, self.court_data)

        # Summarize
        def fmt_list(members: list[discord.Member]) -> str:
            return ", ".join([m.display_name for m in members]) or "—"

        await interaction.followup.send(
            f"✅ **Jury summoned** for {case_number}\n"
            f"Jurors ({len(panel_members)}): {fmt_list(panel_members)}\n"
            f"Alternates ({len(alt_members)}): {fmt_list(alt_members)}\n"
            f"DMs delivered: {dm_ok} · Public fallbacks: {public_ok}",
            ephemeral=True
        )

    @court.command(name="set_caption", description="Set or clear a custom case caption (class, org, In re, etc.)")
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.choices(style=[
        app_commands.Choice(name="v.", value="v"),
        app_commands.Choice(name="In re", value="in_re"),
    ])
    @app_commands.describe(
        case_number="Case number",
        style="Caption style",
        left="Left side text (e.g., class name, @user, org)",
        right="Right side text (omit for In re)",
        reset="Clear custom caption (revert to default)"
    )
    async def set_caption(
        self,
        interaction: discord.Interaction,
        case_number: str,
        style: app_commands.Choice[str],
        left: str,
        right: str | None = None,
        reset: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)
        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        if reset:
            case.pop("caption", None)
            save_json(COURT_FILE, self.court_data)
            return await interaction.followup.send("✅ Caption reset to default.", ephemeral=True)

        if style.value == "v" and not right:
            return await interaction.followup.send("❌ For the “v.” style, please provide `right`.", ephemeral=True)

        case["caption"] = {"style": style.value, "left": left.strip(), "right": (right.strip() if right else None)}
        save_json(COURT_FILE, self.court_data)
        cap = await self._caption(interaction.guild, case)
        await interaction.followup.send(f"✅ Caption set to: **{cap}**", ephemeral=True)

    
    @court.command(name="parties", description="View parties and attorneys for a case")
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def parties_cmd(self, interaction: discord.Interaction, case_number: str):
        case = self.court_data.get(case_number)
        if not case: return await interaction.response.send_message("❌ Case not found.", ephemeral=True)
        await self._normalize_case(interaction.guild, case)
        cap = await self._caption_from_parties(interaction.guild, case)

        def _fmt_side(side):
            rows = []
            for p in case["parties"].get(side, []):
                attys = [f"<@{aid}>" for aid in (p.get("attorneys") or [])]
                rows.append(f"- **{p['name']}** *(kind: {p['kind']})*  " + (f"Attorneys: {', '.join(attys)}" if attys else ""))
            return "\n".join(rows) or "_(none)_"

        msg = (
            f"**{cap}** — `{case_number}`\n\n"
            f"**Plaintiffs**\n{_fmt_side('plaintiffs')}\n\n"
            f"**Defendants**\n{_fmt_side('defendants')}"
        )
        await interaction.response.send_message(msg, ephemeral=True)

    @court.command(name="party", description="Manage parties (add / remove / replace)")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
        app_commands.Choice(name="Replace", value="replace"),
    ])
    @app_commands.choices(side=[
        app_commands.Choice(name="Plaintiff", value="plaintiffs"),
        app_commands.Choice(name="Defendant", value="defendants"),
    ])
    @app_commands.describe(
        case_number="Case number",
        action="Choose add, remove, or replace",
        side="Which side to modify",
        party="@user or 'org:/class:/state:' (for Add)",
        party_name="Exact saved party name (for Remove)",
        old_name="Exact saved party name (for Replace)",
        new_party="@user or 'org:/class:/state:' (for Replace)",
        reason="Short clerk/judge note"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    async def party(
        self,
        interaction: discord.Interaction,
        case_number: str,
        action: app_commands.Choice[str],
        side: app_commands.Choice[str],
        party: str | None = None,
        party_name: str | None = None,
        old_name: str | None = None,
        new_party: str | None = None,
        reason: str | None = None,
    ):
        case = self.court_data.get(case_number)
        if not case:
            return await interaction.response.send_message("❌ Case not found.", ephemeral=True)
        await self._normalize_case(interaction.guild, case)

        # ADD
        if action.value == "add":
            if not party or not reason:
                return await interaction.response.send_message("❌ For Add, provide `party` and `reason`.", ephemeral=True)
            uid = await self._maybe_user_id(party)
            if uid:
                name = await self.try_get_display_name(interaction.guild, uid)
                p = Party(id=uid, name=name, kind="user", pid=_uuid(), attorneys=[]).to_dict()
            else:
                s = party.strip()
                kind, name = "org", s
                low = s.lower()
                if low.startswith("class:"): kind, name = "class", s.split(":",1)[1].strip()
                elif low.startswith("org:"):  kind, name = "org",   s.split(":",1)[1].strip()
                elif low.startswith("state:"):kind, name = "state", s.split(":",1)[1].strip()
                p = Party(id=None, name=name, kind=kind, pid=_uuid(), attorneys=[]).to_dict()

            old_caption = await self._caption_from_parties(interaction.guild, case)
            case["parties"][side.value].append(p)
            new_caption = await self._caption_from_parties(interaction.guild, case)
            self._docket_clerk_notice(case, f"Party added to **{side.name}**: {p['name']}. Reason: {reason}", old_caption, new_caption)
            save_json(COURT_FILE, self.court_data)
            return await interaction.response.send_message(f"✅ Added **{p['name']}** to **{side.name}**.", ephemeral=True)

        # REMOVE
        if action.value == "remove":
            if not party_name or not reason:
                return await interaction.response.send_message("❌ For Remove, provide `party_name` and `reason`.", ephemeral=True)
            lst = case["parties"][side.value]
            idx = next((i for i,p in enumerate(lst) if p["name"] == party_name), None)
            if idx is None:
                return await interaction.response.send_message("❌ Party not found (use /court parties).", ephemeral=True)
            removed = lst.pop(idx)
            old_caption = await self._caption_from_parties(interaction.guild, case)
            new_caption = await self._caption_from_parties(interaction.guild, case)
            self._docket_clerk_notice(case, f"Party removed from **{side.name}**: {removed['name']}. Reason: {reason}", old_caption, new_caption)
            save_json(COURT_FILE, self.court_data)
            return await interaction.response.send_message(f"🗑️ Removed **{removed['name']}** from **{side.name}**.", ephemeral=True)

        # REPLACE
        if action.value == "replace":
            if not old_name or not new_party or not reason:
                return await interaction.response.send_message("❌ For Replace, provide `old_name`, `new_party`, and `reason`.", ephemeral=True)
            lst = case["parties"][side.value]
            idx = next((i for i,p in enumerate(lst) if p["name"] == old_name), None)
            if idx is None:
                return await interaction.response.send_message("❌ Party not found.", ephemeral=True)
            old_p = lst[idx]

            uid = await self._maybe_user_id(new_party)
            if uid:
                name = await self.try_get_display_name(interaction.guild, uid)
                new_p = Party(id=uid, name=name, kind="user", pid=_uuid(), attorneys=[]).to_dict()
            else:
                s = new_party.strip()
                kind, name = "org", s
                low = s.lower()
                if low.startswith("class:"): kind, name = "class", s.split(":",1)[1].strip()
                elif low.startswith("org:"):  kind, name = "org",   s.split(":",1)[1].strip()
                elif low.startswith("state:"):kind, name = "state", s.split(":",1)[1].strip()
                new_p = Party(id=None, name=name, kind=kind, pid=_uuid(), attorneys=[]).to_dict()

            old_caption = await self._caption_from_parties(interaction.guild, case)
            lst[idx] = new_p
            new_caption = await self._caption_from_parties(interaction.guild, case)
            self._docket_clerk_notice(case, f"Party replaced on **{side.name}**: {old_p['name']} → {new_p['name']}. Reason: {reason}", old_caption, new_caption)
            save_json(COURT_FILE, self.court_data)
            return await interaction.response.send_message(f"🔁 Replaced **{old_p['name']}** with **{new_p['name']}** on **{side.name}**.", ephemeral=True)

        return await interaction.response.send_message("❌ Unknown action.", ephemeral=True)


    @court.command(name="set_attorney", description="Clerk: add an attorney to a party")
    @app_commands.choices(side=[
        app_commands.Choice(name="Plaintiff", value="plaintiffs"),
        app_commands.Choice(name="Defendant", value="defendants"),
    ])
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    async def set_attorney(self, interaction: discord.Interaction, case_number: str, side: app_commands.Choice[str], party_name: str, attorney: discord.Member):
        case = self.court_data.get(case_number)
        if not case: return await interaction.response.send_message("❌ Case not found.", ephemeral=True)
        await self._normalize_case(interaction.guild, case)

        p = self._find_party(case, side.value, party_name)
        if not p: return await interaction.response.send_message("❌ Party not found.", ephemeral=True)

        p.setdefault("attorneys", [])
        if attorney.id not in p["attorneys"]:
            p["attorneys"].append(attorney.id)

        self._docket_clerk_notice(case, f"Attorney <@{attorney.id}> added for **{party_name}** ({side.name}).", await self._caption_from_parties(interaction.guild, case), await self._caption_from_parties(interaction.guild, case))
        save_json(COURT_FILE, self.court_data)
        await interaction.response.send_message(f"✅ Added <@{attorney.id}> for **{party_name}**.", ephemeral=True)

    @court.command(name="remove_attorney", description="Clerk: remove an attorney from a party")
    @app_commands.choices(side=[
        app_commands.Choice(name="Plaintiff", value="plaintiffs"),
        app_commands.Choice(name="Defendant", value="defendants"),
    ])
    @app_commands.autocomplete(case_number=case_autocomplete)
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    async def remove_attorney(self, interaction: discord.Interaction, case_number: str, side: app_commands.Choice[str], party_name: str, attorney: discord.Member):
        case = self.court_data.get(case_number)
        if not case: return await interaction.response.send_message("❌ Case not found.", ephemeral=True)
        await self._normalize_case(interaction.guild, case)

        p = self._find_party(case, side.value, party_name)
        if not p: return await interaction.response.send_message("❌ Party not found.", ephemeral=True)
        try:
            p["attorneys"].remove(attorney.id)
        except ValueError:
            return await interaction.response.send_message("ℹ️ That attorney isn’t listed for this party.", ephemeral=True)

        self._docket_clerk_notice(case, f"Attorney <@{attorney.id}> removed for **{party_name}** ({side.name}).", await self._caption_from_parties(interaction.guild, case), await self._caption_from_parties(interaction.guild, case))
        save_json(COURT_FILE, self.court_data)
        await interaction.response.send_message(f"🗑️ Removed <@{attorney.id}> for **{party_name}**.", ephemeral=True)

    def _docket_clerk_notice(self, case: dict, body: str, old_caption: str, new_caption: str):
        entry = {
            "entry": len(case.setdefault("filings", [])) + 1,
            "document_type": "Clerk Notice",
            "author": "Clerk",
            "author_id": 0,
            "timestamp": datetime.now(UTC).isoformat(),
            "content": f"{body}\n\n**Old caption:** {old_caption}\n**New caption:** {new_caption}",
        }
        case["filings"].append(entry)