from __future__ import annotations
import discord
from redbot.core import commands
from discord import app_commands
import json
import os
import re
import asyncio
import random
import datetime
from datetime import datetime, timezone
import math
import difflib
from zoneinfo import ZoneInfo


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FED_REGISTRY_FILE = os.path.join(BASE_DIR, "federal_registry.json")
SENATORS = 1327053499405701142
REPRESENTATIVES = 1327053334036742215
SENATE = 1302330234422562887
HOUSE = 1302330037365772380
SPEAKER_OF_THE_HOUSE = 1417354264795418664
SENATE_MAJORITY_LEADER = 1417354436472344586
SPIDEY_HOUSE = 1302330503399084144

CITIZENSHIP = {
    "commons": 1415927703340716102,
    "gaming": 1415928304757637175,
    "dp": 1415928367730921482,
    "crazy_times": 1415928481505738792,
    "user_themed": 1415928541740142672
}
CITIZENSHIP_IDS = set(CITIZENSHIP.values())

CATEGORIES = {
    "commons": {
        "name": "Commons",
        "description": "The general use category for the server.",
        "role_id": CITIZENSHIP["commons"],
    },
    "gaming": {
        "name": "Gaming",
        "description": "The gaming category for the server.",
        "role_id": CITIZENSHIP["gaming"],
    },
    "dp": {
        "name": "Spideyton, District of Parker",
        "description": "The location of the federal government!",
        "role_id": CITIZENSHIP["dp"],
    },
    "crazy_times": {
        "name": "Crazy Times",
        "description": "A category for all things wild and wacky.",
        "role_id": CITIZENSHIP["crazy_times"],
    },
    "user_themed": {
        "name": "User Themed",
        "description": "A category for user-created channels.",
        "role_id": CITIZENSHIP["user_themed"],
    }
}

VOTE_OPTIONS = ("Yea", "Nay", "Present")

def load_federal_registry():
    """Load the federal registry from a JSON file."""
    if not os.path.exists(FED_REGISTRY_FILE):
        return {}
    with open(FED_REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_federal_registry(data):
    """Save the federal registry to a JSON file."""
    with open(FED_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

SECTION_RE = re.compile(
    r'^[\*\s_]*[§&]\s*([0-9A-Za-z\-\.]+)\s*\.?\s*(.*?)\s*[\*\s_]*$',
    re.M
)

_TITLE_LINE = re.compile(
    r"""^\s*                    # leading ws
        (?:Title)\s+            # Title
        (?:[IVXLCDM]+|\d+)      # roman or digits
        (?:\s*[-—:.]\s*.*)?     # optional delimiter + trailing words
        \s*$                    # end
    """,
    re.IGNORECASE | re.VERBOSE,
)
_SECTION_LINE = re.compile(
    r"""^\s*
        (?:Sec(?:tion)?\.?|§+)  # Section markers
        \s*\d+[A-Za-z\-]*\.?    # number like 1, 101, 105A, §101.
        (?:\s*[-—:.]\s*.*)?     # optional delimiter + trailing words
        \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def _bold_headings_preserve(raw_text: str, chunk_size: int = 3800) -> list[str]:
    """
    Bold only heading lines (Title/Section/§) while preserving the line EXACTLY.
    Returns safe-sized chunks for embed descriptions.
    """
    chunks: list[str] = []
    acc = ""

    def flush():
        nonlocal acc
        if acc:
            chunks.append(acc)
        acc = ""

    for line in (raw_text or "").splitlines():
        s = line.rstrip("\r\n")
        if _TITLE_LINE.match(s) or _SECTION_LINE.match(s):
            s = f"**{s.strip()}**"   # wrap whole line, don't alter punctuation or spacing
        # keep blank lines and non-heading lines as-is
        if len(acc) + len(s) + 1 > chunk_size:
            flush()
        acc += s + "\n"
    flush()
    return chunks



def parse_sections_from_text(text: str):
    """
    Parse a chapter body into a list of section dicts:
      [{"number": "§ 1331", "short": "Subject Matter Jurisdiction", "text": "..."}]
    Accepts § or & at the start; tolerates bold/italics and trailing dots.
    """
    matches = list(SECTION_RE.finditer(text or ""))
    out = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        raw_num = (m.group(1) or "").strip()
        heading = (m.group(2) or "").strip().rstrip(".")
        body = (text[start:end] or "").strip()
        if raw_num:
            out.append({"number": f"§ {raw_num}", "short": heading, "text": body})
    return out

def norm_sec_key(raw_display_num: str) -> str:
    """
    Normalize '§ 1331', '1331.', '28 USC § 1331' => '§ 1331'
    Used as the chapter-internal key so we don't silently duplicate.
    """
    digits = ''.join(ch for ch in (raw_display_num or "") if ch.isdigit())
    return f"§ {digits}" if digits else (raw_display_num or "").strip()

def normalize_text(t: str) -> str:
    """Whitespace-stable comparison to detect unchanged conflicts."""
    if not t:
        return ""
    return "\n".join(line.rstrip() for line in t.strip().splitlines())

def infer_chapter_from_section_digits(sec_digits: str) -> int:
    """
    '301' -> 3, '1331' -> 13, '2201' -> 22, '22-01' -> 22
    Heuristic: all but last two digits.
    """
    d = ''.join(ch for ch in (sec_digits or "") if ch.isdigit())
    if not d:
        return 1
    if len(d) <= 2:
        return 1
    return int(d[:-2])

def section_chapter_mismatch(sec_display_num: str, chapter_num: int) -> bool:
    d = ''.join(ch for ch in (sec_display_num or "") if ch.isdigit())
    inferred = infer_chapter_from_section_digits(d)
    return inferred != chapter_num

def to_roman(n: int) -> str:
    vals = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"),  (90, "XC"),  (50, "L"),  (40, "XL"),
        (10, "X"),   (9, "IX"),   (5, "V"),   (4, "IV"), (1, "I"),
    ]
    out, x = [], n
    for v, s in vals:
        while x >= v:
            out.append(s); x -= v
    return "".join(out) if out else "I"

def fmt_article(n: int) -> str:
    # IRL: roman (I), Court: arabic (1)
    return f"Article {to_roman(n)}"

def fmt_amendment(n: int, style: str) -> str:
    # IRL: arabic (14), Court: roman (XIV)
    return f"Amendment {n if style == 'irl' else to_roman(n)}"

def ensure_constitution_schema(reg: dict) -> None:
    """
    Backfill headings + sections containers without disturbing existing text.
    Call once before any constitution commands run (e.g., Cog __init__).
    """
    const = reg.setdefault("constitution", {})
    for bucket in ("articles", "amendments"):
        b = const.setdefault(bucket, {})
        for _, node in list(b.items()):
            if not isinstance(node, dict):
                continue
            node.setdefault("heading", "")
            secs = node.setdefault("sections", {})
            # If single-body (no sections), 'sections' will be {"text": "..."}; leave as-is.
            if isinstance(secs, dict) and "text" in secs and len(secs) == 1:
                continue
            for _, s in list(secs.items()):
                if isinstance(s, dict):
                    s.setdefault("heading", "")

def ensure_bills_schema(reg: dict) -> dict:
    """
    Ensure the bills container exists.
    Shape:
    {
      "bills": {
        "sequence": {"Senate": 0, "House": 0},
        "items": { "S-0001": {...}, ... }
      }
    }
    """
    b = reg.setdefault("bills", {})
    b.setdefault("sequence", {"Senate": 0, "House": 0})
    b.setdefault("items", {})
    return b

def next_bill_id(reg: dict, chamber: str) -> str:
    """
    Returns a simple ID like 'S-0001' or 'H-0007'.
    Type/joint are stored as fields on the bill (keeps IDs simple).
    """
    b = ensure_bills_schema(reg)
    seq = b["sequence"].get(chamber, 0) + 1
    b["sequence"][chamber] = seq
    prefix = "S" if chamber == "Senate" else "H"
    return f"{prefix}-{seq:04d}"

def chamber_channel_id(chamber: str) -> int:
    return SENATE if chamber == "Senate" else HOUSE

def chamber_role_id(chamber: str) -> int:
    return SENATORS if chamber == "Senate" else REPRESENTATIVES

def quorum_required(n_eligible: int) -> int:
    # majority of eligible members
    return (n_eligible // 2) + 1

async def resolve_eligible_members(guild: discord.Guild, channel: discord.abc.GuildChannel, chamber: str) -> list[discord.Member]:
    """
    Eligible = members who can see the chamber channel AND hold the chamber role, excluding bots.
    This is better than raw role count because it honors channel perms.
    """
    role = guild.get_role(chamber_role_id(chamber))
    if not role:
        return []
    # Members that can view the channel and have the right role
    # channel.members is usually populated with members who can see it (requires intents.members)
    candidates = getattr(channel, "members", []) or guild.members  # fallback to guild.members
    return [m for m in candidates if (not m.bot) and (role in m.roles)]

def _poll_question_for(bill: dict) -> str:
    kind = "Bill" if bill["type"] == "bill" else "Resolution"
    joint = " Joint" if bill.get("joint") else ""
    return f"Shall the {bill['chamber']}{joint} {kind} {bill['id']} — “{bill.get('title','')}” — pass?"

def _tally_from_message(msg: discord.Message):
    p = getattr(msg, "poll", None)
    if not p:
        return 0, 0, 0, 0
    counts = {ans.text: getattr(ans, "vote_count", 0) for ans in p.answers}
    yea = counts.get("Yea", 0)
    nay = counts.get("Nay", 0)
    present = counts.get("Present", 0)
    total = yea + nay + present
    return yea, nay, present, total

def _decide(yea: int, nay: int, present: int, threshold: str) -> str:
    # exclude 'Present' from the denominator (typical parliamentary practice)
    votes = yea + nay
    if votes == 0:
        return "NO_QUORUM"
    if threshold == "simple":
        return "PASSED" if yea > nay else "FAILED"
    if threshold == "two_thirds":
        return "PASSED" if yea >= math.ceil((2/3) * votes) else "FAILED"
    if threshold == "three_fifths":
        return "PASSED" if yea >= math.ceil((3/5) * votes) else "FAILED"
    return "FAILED"

# --- Helpers (near your other registry helpers) ---
def ensure_eo_schema(reg: dict) -> dict:
    """
    {
      "executive_orders": {
        "sequence": {"2025": 0, ...},
        "items": {"EO-2025-0001": {...}, ...}
      }
    }
    """
    eo = reg.setdefault("executive_orders", {})
    eo.setdefault("sequence", {})
    eo.setdefault("items", {})
    return eo

def next_eo_id(reg: dict) -> str:
    from datetime import datetime
    eo = ensure_eo_schema(reg)
    yr = str(datetime.utcnow().year)
    seq = eo["sequence"].get(yr, 0) + 1
    eo["sequence"][yr] = seq
    return f"EO-{yr}-{seq:04d}"

TITLE_RE = re.compile(r'^\s*(?:Title|TITLE)\s+([IVXLCDM]+|\d+)\s*[-—:.\)]?\s*(.*)$', re.I)
SEC_RE   = re.compile(r'^\s*(?:Sec\.|Section)\s+(\d+)\s*[-—:.\)]?\s*(.*)$', re.I)

ROMANS = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
def _roman_to_int(s: str) -> int:
    s = s.upper().strip()
    total = 0
    prev = 0
    for ch in reversed(s):
        val = ROMANS.get(ch, 0)
        total = total - val if val < prev else total + val
        prev = val
    return total or int(s)  # fall back to digits

def parse_bill_structure(text: str) -> dict:
    """
    Parse:
      Title I Title of Title
      Sec. 1 Title of Sec.
      body...
      Sec. 2 Title...
      body...
      Title II ...
    Returns {"version":1,"titles":[{"n":1,"heading":"...","preface": "", "sections":[{"n":1,"heading":"...","body":"..."}]}]}
    """
    lines = (text or "").splitlines()
    struct = {"version": 1, "titles": []}
    cur_title = None
    cur_sec = None

    def start_title(n:int, heading:str):
        nonlocal cur_title, cur_sec
        cur_title = {"n": n, "heading": heading.strip(), "preface": "", "sections": []}
        struct["titles"].append(cur_title)
        cur_sec = None

    def start_sec(n:int, heading:str):
        nonlocal cur_title, cur_sec
        if not cur_title:
            start_title(1, "")
        cur_sec = {"n": n, "heading": heading.strip(), "body": ""}
        cur_title["sections"].append(cur_sec)

    for raw in lines:
        mT = TITLE_RE.match(raw)
        if mT:
            n = _roman_to_int(mT.group(1))
            start_title(n, mT.group(2) or "")
            continue
        mS = SEC_RE.match(raw)
        if mS:
            n = int(mS.group(1))
            start_sec(n, mS.group(2) or "")
            continue
        # body/preface
        if cur_sec:
            cur_sec["body"] += (raw + "\n")
        elif cur_title:
            cur_title["preface"] += (raw + "\n")

    # strip trailing whitespace
    for t in struct["titles"]:
        t["preface"] = t["preface"].strip()
        for s in t["sections"]:
            s["body"] = s["body"].strip()
    return struct

def index_sections(struct: dict) -> list[tuple[str, dict, dict]]:
    """
    Returns [(id, title_node, section_node)], id like 'T1.S2' (always numeric).
    """
    out = []
    for t in sorted(struct.get("titles", []), key=lambda x: x.get("n", 0)):
        for s in sorted(t.get("sections", []), key=lambda x: x.get("n", 0)):
            out.append((f"T{t['n']}.S{s['n']}", t, s))
    return out

def get_section(struct: dict, target_id: str):
    for tid, t, s in index_sections(struct):
        if tid == target_id:
            return t, s
    return None, None

def unified_diff(old: str, new: str, ctx: int = 3) -> str:
    a = (old or "").splitlines()
    b = (new or "").splitlines()
    return "\n".join(difflib.unified_diff(a, b, lineterm="", n=ctx))

def _sorted_num_keys_str(d: dict[str, any]) -> list[str]:
    # sort string keys that are numerals: {"1":..., "10":..., "2":...} -> ["1","2","10"]
    return sorted((k for k in d.keys() if str(k).isdigit()), key=lambda k: int(k))

def _sec_digits(k: str) -> int:
    return int("".join(ch for ch in (k or "") if ch.isdigit()) or 0)

def normalize_registry_order(reg: dict) -> None:
    # --- Constitution: articles/amendments -> sections ---
    const = reg.get("constitution", {})
    for bucket in ("articles", "amendments"):
        b = const.get(bucket, {})
        # rebuild top level numerically
        ordered_nums = _sorted_num_keys_str(b)
        rebuilt_b = {}
        for num in ordered_nums:
            node = b[num]
            secs = node.get("sections")
            if isinstance(secs, dict) and not ("text" in secs and len(secs) == 1):
                # multi-section: sort section keys numerically
                skeys = sorted((k for k in secs.keys() if str(k).isdigit()), key=lambda k: int(k))
                node["sections"] = {k: secs[k] for k in skeys}
            rebuilt_b[num] = node
        const[bucket] = rebuilt_b

    # --- Code: titles -> chapters -> sections ---
    code = reg.get("spidey_republic_code", {})
    if isinstance(code, dict):
        # titles
        ordered_titles = _sorted_num_keys_str(code)
        rebuilt_titles = {}
        for t in ordered_titles:
            tnode = code[t]
            chaps = tnode.get("chapters", {})
            # chapters
            ordered_chaps = _sorted_num_keys_str(chaps)
            rebuilt_chaps = {}
            for c in ordered_chaps:
                cnode = chaps[c]
                secs = cnode.get("sections", {})
                # sections like "§ 1291": sort by digits
                rebuilt_secs = {k: secs[k] for k in sorted(secs.keys(), key=_sec_digits)}
                cnode["sections"] = rebuilt_secs
                rebuilt_chaps[c] = cnode
            tnode["chapters"] = rebuilt_chaps
            rebuilt_titles[t] = tnode
        reg["spidey_republic_code"] = rebuilt_titles

def _get_committees_root(reg: dict) -> dict:
    # Default skeleton
    return reg.setdefault("committees", {"senate": {}, "house": {}, "joint": {}})

def _format_member_mention(guild: discord.Guild, user_id: int) -> str:
    m = guild.get_member(user_id) if guild else None
    return m.mention if m else f"<@{user_id}>"

def _next_hearing_info(node: dict) -> tuple[str, datetime | None]:
    """
    Return (title, dt) for the next upcoming hearing, or ("", None).
    Assumes optional structure:
      node["hearings"] = [{"title": str, "when": ISO8601, "status": "scheduled|cancelled|done"}]
    """
    hearings = node.get("hearings", []) or []
    best = None
    now = datetime.now(timezone.utc)
    for h in hearings:
        try:
            dt = datetime.fromisoformat(h.get("when", "").replace("Z", "+00:00"))
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > now and (best is None or dt < best[1]):
            best = (h.get("title", "") or "", dt)
    return best or ("", None)

def _get_committees_root(reg: dict) -> dict:
    return reg.setdefault("committees", {"senate": {}, "house": {}, "joint": {}})

def _resolve_committee_node(reg: dict, chamber: str, encoded: str) -> tuple[dict | None, dict | None]:
    """
    Returns (parent_node, node). For subcommittees, parent_node is the parent; for top-level, parent_node is None.
    `encoded` is either 'parent' or 'parent::child' (what our autocomplete returns).
    """
    bucket = _get_committees_root(reg).get(chamber, {})
    if "::" in encoded:
        parent_key, sub_key = encoded.split("::", 1)
        parent = bucket.get(parent_key)
        node = (parent.get("sub_committees") or {}).get(sub_key) if parent else None
        return parent, node
    else:
        return None, bucket.get(encoded)

def _user_is_committee_chair(guild: discord.Guild | None, user: discord.Member, node: dict) -> bool:
    return bool(node and user and node.get("chair_id") == user.id)

def _user_has_leadership_override(user: discord.Member) -> bool:
    # Optional override: ML/Speaker/Admin can schedule too.
    user_role_ids = {r.id for r in getattr(user, "roles", [])}
    if user.guild_permissions.administrator:
        return True
    return (SENATE_MAJORITY_LEADER in user_role_ids) or (SPEAKER_OF_THE_HOUSE in user_role_ids)

_TIME_PATTERNS = [
    # HH:MM with optional am/pm
    r"^\s*(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ampm>[ap]m)?\s*$",
    # HH with optional am/pm (assume :00)
    r"^\s*(?P<h>\d{1,2})\s*(?P<ampm>[ap]m)\s*$",
]

def _parse_time_hm(s: str) -> tuple[int, int] | None:
    s = (s or "").strip().lower()
    for pat in _TIME_PATTERNS:
        m = re.match(pat, s)
        if not m:
            continue
        h = int(m.group("h"))
        mnt = int(m.group("m")) if m.groupdict().get("m") else 0
        ampm = m.groupdict().get("ampm")
        if ampm:
            if h == 12:
                h = 0
            if ampm == "pm":
                h += 12
        if 0 <= h <= 23 and 0 <= mnt <= 59:
            return h, mnt
    # Also accept strict 24h HH:MM via datetime.strptime
    try:
        dt = datetime.strptime(s, "%H:%M")
        return dt.hour, dt.minute
    except Exception:
        return None

_TZ_CHOICES = [
    app_commands.Choice(name="Pacific (PT)", value="America/Los_Angeles"),
    app_commands.Choice(name="Mountain (MT)", value="America/Denver"),
    app_commands.Choice(name="Central (CT)", value="America/Chicago"),
    app_commands.Choice(name="Eastern (ET)", value="America/New_York"),
    app_commands.Choice(name="UTC", value="UTC"),
    app_commands.Choice(name="UK (London)", value="Europe/London"),
]

def _build_aware_dt(date_str: str, time_str: str, tz_value: str) -> datetime | None:
    # date: YYYY-MM-DD
    try:
        y, m, d = map(int, date_str.split("-"))
    except Exception:
        return None
    hm = _parse_time_hm(time_str)
    if not hm:
        return None
    h, mi = hm
    try:
        tz = ZoneInfo(tz_value)
    except Exception:
        tz = timezone.utc
    return datetime(y, m, d, h, mi, tzinfo=tz)

def _is_chamber_leader(user: discord.Member, chamber: str) -> bool:
    ids = {r.id for r in getattr(user, "roles", [])}
    if user.guild_permissions.administrator:
        return True
    if chamber == "senate":
        return SENATE_MAJORITY_LEADER in ids
    if chamber == "house":
        return SPEAKER_OF_THE_HOUSE in ids
    if chamber == "joint":
        # allow either leader to manage joint committees
        return (SENATE_MAJORITY_LEADER in ids) or (SPEAKER_OF_THE_HOUSE in ids)
    return False

def _add_member(node: dict, member_id: int) -> bool:
    members = set(node.get("members") or [])
    before = len(members)
    members.add(member_id)
    node["members"] = sorted(members)
    return len(members) > before


def other_chamber(ch: str) -> str:
    return "House" if ch == "Senate" else "Senate"

def chamber_role_id(ch: str) -> int:
    return SENATORS if ch == "Senate" else REPRESENTATIVES

def is_in_chamber(user: discord.Member, chamber: str) -> bool:
    return chamber_role_id(chamber) in {r.id for r in getattr(user, "roles", [])} or user.guild_permissions.administrator

def is_leadership(user: discord.Member) -> bool:
    ids = {r.id for r in getattr(user, "roles", [])}
    return user.guild_permissions.administrator or (SENATE_MAJORITY_LEADER in ids) or (SPEAKER_OF_THE_HOUSE in ids)

def mark_history(bill: dict, action: str, by: int):
    bill.setdefault("history", []).append({"at": discord.utils.utcnow().isoformat(), "by": by, "action": action})

async def _fetch_vote_counts(interaction: discord.Interaction, b: dict) -> tuple[int,int,int,int]:
    chan = interaction.client.get_channel(b["vote"]["channel_id"])
    msg = await chan.fetch_message(b["vote"]["message_id"])
    return _tally_from_message(msg)
    
class ConstitutionUploadModal(discord.ui.Modal, title="Upload Constitution Text"):
    def __init__(self, *, kind: str, number: int, target_node: dict, top_heading: str | None = None):
        """
        kind: 'article' | 'amendment'
        number: which Article/Amendment (Arabic)
        target_node: dict to mutate (has/gets {'heading': str, 'sections': {...}})
        top_heading: optional heading passed from the slash command
        """
        super().__init__()
        self.kind = kind
        self.number = number
        self.target = target_node
        self.top_heading = (top_heading or "").strip()

        # 3 inputs max in the modal
        self.section = discord.ui.TextInput(
            label="Section number (optional)",
            required=False, style=discord.TextStyle.short, placeholder="e.g., 1"
        )
        self.section_heading = discord.ui.TextInput(
            label="Section heading (optional)",
            required=False, style=discord.TextStyle.short, placeholder="e.g., Vesting"
        )
        self.body = discord.ui.TextInput(
            label="Text", required=True, style=discord.TextStyle.paragraph,
            placeholder="Paste the constitutional text here"
        )

        self.add_item(self.section)
        self.add_item(self.section_heading)
        self.add_item(self.body)

    async def on_submit(self, interaction: discord.Interaction):
        node = self.target
        node.setdefault("heading", "")
        sections = node.setdefault("sections", {})

        # Apply top-level heading if provided
        if self.top_heading:
            node["heading"] = self.top_heading

        sec_raw = (self.section.value or "").strip()
        sec_key = str(int(sec_raw)) if sec_raw.isdigit() else sec_raw

        if not sec_key:
            # Single-body Article/Amendment (no per-section granularity)
            sections.clear()
            sections["text"] = str(self.body.value)
            label = "Article" if self.kind == "article" else "Amendment"
            await interaction.response.send_message(
                f"✅ Uploaded {label} {self.number} (no sections).",
                ephemeral=True
            )
        else:
            # If previously single-body, convert to multi-section
            if "text" in sections and len(sections) == 1:
                body0 = sections["text"]
                sections.clear()
                sections["1"] = {"heading": "", "text": body0}
            s = sections.setdefault(sec_key, {"heading": "", "text": ""})
            if self.section_heading.value:
                s["heading"] = self.section_heading.value.strip()
            s["text"] = str(self.body.value)

            label = "Article" if self.kind == "article" else "Amendment"
            await interaction.response.send_message(
                f"✅ Uploaded {label} {self.number}, Section {sec_key}.",
                ephemeral=True
            )

        # Persist (uses your existing saver)
        save_federal_registry(interaction.client.get_cog("SpideyGov").federal_registry)


class ConstitutionSetHeadingModal(discord.ui.Modal, title="Set Constitution Heading"):
    def __init__(self, *, path_label: str, node: dict):
        super().__init__()
        self.node = node
        self.heading = discord.ui.TextInput(
            label=f"Heading for {path_label}",
            required=True, style=discord.TextStyle.short, max_length=100
        )
        self.add_item(self.heading)

    async def on_submit(self, interaction: discord.Interaction):
        # Node may be article/amendment (has 'heading') OR a section node
        if "text" in self.node and len(self.node) == 1:
            # this would be a single-body container; not applicable here
            pass
        elif "heading" in self.node:
            self.node["heading"] = self.heading.value.strip()

        save_federal_registry(interaction.client.get_cog("SpideyGov").federal_registry)
        await interaction.response.send_message("✅ Heading updated.", ephemeral=True)

class LegislativeProposalModal(discord.ui.Modal, title="Legislative Proposal"):
    def __init__(self, title: str, type: str, sponsor: discord.Member,
                 joint: bool=False, chamber: str | None=None,
                 codification: bool=False, repealing: bool=False,
                 committee: str|None=None, co_sponsors: str|None=None,
                 code_title: str|None=None, sections: str|None=None):
        super().__init__(timeout=None)
        self.title_val = title
        self.type_val = type
        self.sponsor_val = sponsor
        self.joint_val = joint
        self.chamber_val = chamber
        self.codification_val = codification
        self.repealing_val = repealing
        self.committee_val = committee
        self.co_sponsors_val = co_sponsors
        self.code_title_val = code_title
        self.sections_val = sections
        self.summary = discord.ui.TextInput(label="Summary", style=discord.TextStyle.paragraph, required=True)
        self.purpose = discord.ui.TextInput(label="Purpose Statement", style=discord.TextStyle.paragraph, required=True)
        self.text    = discord.ui.TextInput(label="Full Text", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.summary)
        self.add_item(self.purpose)
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        reg = interaction.client.get_cog("SpideyGov").federal_registry
        bills = ensure_bills_schema(reg)

        bill_id = next_bill_id(reg, self.chamber_val)

        # normalize co-sponsors to a simple list of strings for now
        co_list = []
        if self.co_sponsors_val:
            co_list = [p.strip() for p in str(self.co_sponsors_val).split(",") if p.strip()]

        struct = parse_bill_structure(str(self.text.value))
        # If no sections parsed (fallback), keep raw only; else store structure too.
        has_sections = any(t.get("sections") for t in struct.get("titles", []))


        bill = {
            "id": bill_id,
            "title": self.title_val,
            "type": self.type_val,               # "bill" | "resolution"
            "joint": bool(self.joint_val),
            "chamber": self.chamber_val,         # "Senate" | "House"
            "sponsor_id": self.sponsor_val.id,
            "co_sponsors": co_list,
            "committee": self.committee_val or "",
            "codification": bool(self.codification_val),
            "repealing": bool(self.repealing_val),
            "code_title": self.code_title_val or "",
            "sections": self.sections_val or "", # raw string ("13-31" etc.), you can parse later
            "summary": str(self.summary.value),
            "purpose": str(self.purpose.value),
            "text": str(self.text.value),
            "structure": struct if has_sections else None,
            "amendments": {}, 
            "status": "DRAFT",                   # DRAFT → INTRODUCED → (IN_COMMITTEE) → FLOOR → PASSED/FAILED → ENACTED
            "created_at": discord.utils.utcnow().isoformat(),
            "message_id": None,
            "thread_id": None,
        }
        bills["items"][bill_id] = bill
        save_federal_registry(reg)

        # Nice label for humans
        kind = "Bill" if self.type_val == "bill" else "Resolution"
        joint_prefix = "Joint " if self.joint_val else ""
        await interaction.response.send_message(
            f"✅ Saved draft {joint_prefix}{kind} **{bill_id}** — “{self.title_val}”.",
            ephemeral=True
        )


class CodeChapterUploadModal(discord.ui.Modal, title="Upload Chapter Body"):
    """
    Paste the chapter BODY (no 'Chapter X — Title' header).
    We parse sections, preview, and then confirm how to merge.
    """
    def __init__(self, *, cog: SpideyGov, title_key: str, chapter_key: str, chapter_dict: dict):
        super().__init__()
        self.cog = cog
        self.title_key = title_key
        self.chapter_key = chapter_key
        self.chapter = chapter_dict  # dict with "sections" etc.

        self.body = discord.ui.TextInput(
            label="Chapter Body",
            placeholder="Paste everything below the 'Chapter X — ...' header",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.body)

    async def on_submit(self, interaction: discord.Interaction):
        # 1) Parse sections
        sections = parse_sections_from_text(self.body.value)
        if not sections:
            return await interaction.response.send_message(
                "No sections detected. Make sure each section starts with § (or &) followed by its number, e.g., '§ 1331 ...'.",
                ephemeral=True
            )

        # 2) Compute new/conflict/unchanged; detect out-of-chapter
        chapter_num = int(self.chapter_key)
        existing = self.chapter.get("sections", {})
        existing_keys = set(existing.keys())

        new_keys, conflict_keys, unchanged_keys, mismatch_keys = [], [], [], []
        normalized = []  # list[(key, section_dict)]

        for s in sections:
            key = norm_sec_key(s["number"])
            normalized.append((key, s))

            if section_chapter_mismatch(s["number"], chapter_num):
                mismatch_keys.append(key)

            if key in existing_keys:
                prev_text = existing[key].get("text", "")
                if normalize_text(prev_text) == normalize_text(s.get("text", "")):
                    unchanged_keys.append(key)
                else:
                    conflict_keys.append(key)
            else:
                new_keys.append(key)

        # 3) Build preview embed
        total = len(sections)
        embed = discord.Embed(
            title=f"Preview — Title {self.title_key}, Chapter {self.chapter_key}",
            description="Review detected sections and choose how to apply changes.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Detected sections", value=str(total))
        embed.add_field(name="New", value=str(len(new_keys)))
        embed.add_field(name="Conflicts (different text)", value=str(len(conflict_keys)))
        embed.add_field(name="Unchanged (identical text)", value=str(len(unchanged_keys)))

        if mismatch_keys:
            mm = "\n".join(mismatch_keys[:10]) + ("\n… more" if len(mismatch_keys) > 10 else "")
            embed.add_field(
                name="Possible out-of-chapter sections ⚠️",
                value=f"These don't look like Chapter {chapter_num}:\n{mm}",
                inline=False
            )

        if conflict_keys:
            cf = "\n".join(conflict_keys[:10]) + ("\n… more" if len(conflict_keys) > 10 else "")
            embed.add_field(
                name="Conflicting keys",
                value=cf,
                inline=False
            )

        # 4) Show confirm view
        view = ChapterUploadConfirmView(
            cog=self.cog,
            title_key=self.title_key,
            chapter_key=self.chapter_key,
            chapter_dict=self.chapter,
            normalized=normalized
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ChapterUploadConfirmView(discord.ui.View):
    """
    Merge strategies:
      - Merge (keep current): insert only brand-new sections; skip conflicts & unchanged
      - Replace conflicts: overwrite conflicting keys; insert brand-new; skip unchanged
      - Skip conflicts: same as Merge (explicit alternate wording)
      - Cancel: do nothing
    """
    def __init__(self, *, cog: SpideyGov, title_key: str, chapter_key: str, chapter_dict: dict, normalized: list[tuple[str, dict]]):
        super().__init__(timeout=180)
        self.cog = cog
        self.title_key = title_key
        self.chapter_key = chapter_key
        self.chapter = chapter_dict
        self.normalized = normalized

    async def _apply(self, interaction: discord.Interaction, mode: str):
        inserted = replaced = skipped = unchanged = 0

        async with self.cog.registry_lock:
            sections_map = self.chapter.setdefault("sections", {})
            for key, s in self.normalized:
                incoming_text = s.get("text", "")
                incoming_short = s.get("short", "")
                if key in sections_map:
                    prev_text = sections_map[key].get("text", "")
                    if normalize_text(prev_text) == normalize_text(incoming_text):
                        unchanged += 1
                        continue
                    if mode == "replace_conflicts":
                        sections_map[key] = {"number": key, "short": incoming_short, "text": incoming_text}
                        replaced += 1
                    else:
                        # merge/skip_conflicts: keep existing
                        skipped += 1
                else:
                    sections_map[key] = {"number": key, "short": incoming_short, "text": incoming_text}
                    inserted += 1

            # persist
            save_federal_registry(self.cog.federal_registry)

        await interaction.response.edit_message(
            content=f"✅ Applied to Title {self.title_key}, Chapter {self.chapter_key} — "
                    f"Inserted {inserted}, Replaced {replaced}, Skipped {skipped}, Unchanged {unchanged}.",
            embed=None,
            view=None
        )

    @discord.ui.button(label="Merge (keep current)", style=discord.ButtonStyle.primary)
    async def merge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply(interaction, mode="merge")

    @discord.ui.button(label="Replace conflicts", style=discord.ButtonStyle.danger)
    async def replace_conflicts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply(interaction, mode="replace_conflicts")

    @discord.ui.button(label="Skip conflicts", style=discord.ButtonStyle.secondary)
    async def skip_conflicts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply(interaction, mode="skip_conflicts")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelled. No changes written.", embed=None, view=None)

_SEC_PATTERNS = [
    r"^\s*Sec(?:tion)?\.?\s*(?P<num>\d+[A-Za-z\-]*)\s*[—\-:\.]\s*(?P<title>.+)\s*$",
    r"^\s*§+\s*(?P<num>\d+[A-Za-z\-]*)\.?\s*(?P<title>.+)\s*$",
]

def _parse_sections_from_text(body: str) -> list[dict]:
    """
    Split a multiline text into sections by heading lines.
    Returns: [{"number": "...","title": "...","text": "..."}]
    """
    lines = (body or "").splitlines()
    sections = []
    cur = {"number": None, "title": None, "text": ""}

    def start_new(num, title):
        nonlocal cur
        if cur["number"] or cur["text"].strip():
            sections.append({**cur, "text": cur["text"].strip()})
        cur = {"number": num.strip(), "title": (title or "").strip(), "text": ""}

    for ln in lines:
        m = None
        for pat in _SEC_PATTERNS:
            m = re.match(pat, ln.strip())
            if m: break
        if m:
            start_new(m.group("num"), m.group("title"))
        else:
            cur["text"] += (ln + "\n")
    if cur["number"] or cur["text"].strip():
        sections.append({**cur, "text": cur["text"].strip()})
    # default if user forgot a heading at start: make it Sec. 1 — General
    if not sections:
        sections = [{"number": "1", "title": "General", "text": body.strip()}]
    return sections

def _format_eo_for_display(order: dict) -> list[str]:
    """Bold the Sec. headings for EO; chunk for safe embed sizes."""
    chunks: list[str] = []
    acc = ""
    sections = ((order.get("structure") or {}).get("titles") or [{}])[0].get("sections") or []
    for s in sections:
        hdr = f"**Sec. {s.get('number','')} — {s.get('title','')}**\n"
        body = (s.get("text") or "").strip() + "\n\n"
        if len(acc) + len(hdr) + len(body) > 1800:
            if acc.strip():
                chunks.append(acc); acc = ""
        acc += hdr + body
    if acc.strip():
        chunks.append(acc)
    return chunks

class ExecutiveOrderModal(discord.ui.Modal, title="New Executive Order"):
    eo_title = discord.ui.TextInput(
        label="Order Title",
        placeholder="e.g., Executive Order on Channel Access Controls",
        max_length=200
    )
    eo_summary = discord.ui.TextInput(
        label="Short Summary (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300
    )
    eo_body = discord.ui.TextInput(
        label="Sections (use 'Sec. 1 — ...' or '§ 1. ...')",
        style=discord.TextStyle.paragraph,
        placeholder="Sec. 1 — Policy\nBody...\n\nSec. 2 — Implementation\nBody...",
        max_length=5000
    )

    def __init__(self, parent):
        super().__init__()
        self.parent = parent  # the Cog

    async def on_submit(self, interaction: discord.Interaction):
        reg = self.parent.federal_registry
        store = reg.setdefault("executive_orders", {}).setdefault("items", {})

        # assign EO number (simple annual counter)
        from datetime import datetime
        yr = datetime.utcnow().year
        seq = reg.setdefault("executive_orders", {}).setdefault("seq", {}).get(str(yr), 0) + 1
        reg["executive_orders"]["seq"][str(yr)] = seq
        eo_id = f"EO-{yr}-{seq:04d}"

        # parse sections
        sections = _parse_sections_from_text(str(self.eo_body))

        order = {
            "id": eo_id,
            "title": str(self.eo_title).strip(),
            "summary": str(self.eo_summary).strip(),
            "text": str(self.eo_body),
            "structure": {"titles": [{"name": "Executive Order", "sections": sections}]},
            "issued_by": interaction.user.id,
            "issued_at": discord.utils.utcnow().isoformat(),
            "status": "ISSUED",
        }
        store[eo_id] = order
        save_federal_registry(reg)

        # post in White House channel, nicely formatted
        wh = interaction.client.get_channel(SPIDEY_HOUSE)
        pages = _format_eo_for_display(order)
        if wh:
            # header
            head = discord.Embed(
                title=f"{eo_id} — {order['title']}",
                description=(order.get("summary") or ""),
                color=discord.Color.dark_gold()
            )
            await wh.send(embed=head)
            for p in pages:
                await wh.send(embed=discord.Embed(description=p[:4000], color=discord.Color.dark_gold()))

        await interaction.response.send_message(f"✅ Issued **{eo_id}** — {order['title']}", ephemeral=True)



class SpideyGov(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.federal_registry = load_federal_registry()
        ensure_constitution_schema(self.federal_registry)
        normalize_registry_order(self.federal_registry)
        self.registry_lock = asyncio.Lock()

    def cog_unload(self):
        save_federal_registry(self.federal_registry)
    
    def to_roman(self, n: int) -> str:
        vals = [
            (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
            (100, "C"),  (90, "XC"),  (50, "L"),  (40, "XL"),
            (10, "X"),   (9, "IX"),   (5, "V"),   (4, "IV"), (1, "I"),
        ]
        out, x = [], n
        for v, s in vals:
            while x >= v:
                out.append(s); x -= v
        return "".join(out) if out else "I"

    legislature = app_commands.Group(name="legislature", description="Legislative commands")
    executive = app_commands.Group(name="executive", description="Executive commands")
    category = app_commands.Group(name="category", description="Category management commands")
    registry = app_commands.Group(name="registry", description="Commands for viewing and updating the federal registry")


    @legislature.command(name="propose_legislation", description="Propose new legislation")
    @app_commands.checks.has_any_role(SENATORS, REPRESENTATIVES)
    @app_commands.describe(
        title="Title",
        type="bill or resolution",
        joint="Both chambers?",
        codification="Is this a codification?",
        repealing="Is this a repealing measure?",
        committee="Sponsoring committee (optional)",
        co_sponsors="Co-sponsors, comma-separated (optional)",
        code_title="Code title if codifying/repealing (optional)",
        sections="Hyphenated sections if codifying/repealing (optional)",
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Bill", value="bill"),
        app_commands.Choice(name="Resolution", value="resolution"),
    ])
    async def propose_legislation(
        self,
        interaction: discord.Interaction,
        title: str,
        type: str,
        joint: bool=False,
        codification: bool=False,
        repealing: bool=False,
        committee: str | None = None,
        co_sponsors: str | None = None,
        code_title: str | None = None,
        sections: str | None = None,
    ):
        is_senator = any(r.id == SENATORS for r in interaction.user.roles)
        chamber = "Senate" if is_senator else "House"

        # If codifying/repealing but missing details, bounce early
        if (codification or repealing) and (not code_title or not sections):
            return await interaction.response.send_message(
                "Because this is a codification/repeal, `code_title` and `sections` are required. Re-run the command with those fields.",
                ephemeral=True
            )

        modal = LegislativeProposalModal(
            title=title,
            type=type,
            joint=joint,
            chamber=chamber,
            sponsor=interaction.user,
            # stash the short metadata on the modal for on_submit
            codification=codification,
            repealing=repealing,
            committee=committee,
            co_sponsors=co_sponsors,
            code_title=code_title,
            sections=sections,
        )
        await interaction.response.send_modal(modal)


    @registry.command(name="title_editor", description="Name a title for federal regulations")
    @app_commands.checks.has_any_role(SENATORS, REPRESENTATIVES)
    @app_commands.describe(
        title="The number of the Title",
        description="A brief description of the Title",
        replacing_desc="Replacing an existing desc?"
    )
    async def title_editor(self, interaction: discord.Interaction, title: int, description: str, replacing_desc: bool = False):
        root = self.federal_registry.setdefault("spidey_republic_code", {})
        if str(title) in root and not replacing_desc:
            return await interaction.response.send_message(
                f"Title {title} already exists in the federal registry.", ephemeral=True
        )
        node = root.setdefault(str(title), {"description": "", "chapters": {}})
        node["description"] = description

        save_federal_registry(self.federal_registry)
        await interaction.response.send_message(f"Title {title} - '{description}' has been {'added to' if not replacing_desc else 'updated for'} the federal registry.", ephemeral=True)

    async def code_title_autocomplete(self, interaction: discord.Interaction, current: str):
        titles = self.federal_registry.get("spidey_republic_code", {})
        keys = sorted(titles.keys(), key=lambda k: int(k) if str(k).isdigit() else 10**9)
        out = []
        cur = (current or "").lower()
        for t in keys:
            lab = f"{t} — {titles[t]['description']}"
            if cur in lab.lower():
                out.append(app_commands.Choice(name=lab, value=t))
        return out[:25]



    @registry.command(name="chapter_editor", description="Name a chapter for federal regulations")
    @app_commands.checks.has_any_role(SENATORS, REPRESENTATIVES)
    @app_commands.describe(
        title="The number of the Title",
        chapter="The number of the Chapter",
        description="A brief description of the Chapter",
        replacing_desc="Replacing an existing desc?"
    )
    @app_commands.autocomplete(title=code_title_autocomplete)
    async def chapter_editor(self, interaction: discord.Interaction, title: str, chapter: int, description: str, replacing_desc:bool=False):
        if str(title) not in self.federal_registry.get("spidey_republic_code", {}):
            return await interaction.response.send_message(f"Title {title} does not exist in the federal registry.", ephemeral=True)

        reg = self.federal_registry["spidey_republic_code"][title]
        if str(chapter) in reg["chapters"] and not replacing_desc:
            return await interaction.response.send_message(f"Chapter {chapter} already exists in Title {title}.", ephemeral=True)

        c = reg["chapters"].setdefault(str(chapter), {"description": "", "sections": {}})
        c["description"] = description

        save_federal_registry(self.federal_registry)
        await interaction.response.send_message(f"Chapter {chapter} - '{description}' has been {'added to' if not replacing_desc else 'updated for'} Title {title}.", ephemeral=True)

    async def chapter_autocomplete(self, interaction: discord.Interaction, current: str):
        ns = interaction.namespace
        title = getattr(ns, "title", None)
        chapters = self.federal_registry.get("spidey_republic_code", {}).get(str(title), {}).get("chapters", {})
        keys = sorted(chapters.keys(), key=lambda k: int(k) if str(k).isdigit() else 10**9)
        cur = (current or "").lower()
        out = []
        for c in keys:
            lab = f"{c} — {chapters[c].get('description','')}"
            if cur in lab.lower():
                out.append(app_commands.Choice(name=lab, value=c))
        return out[:25]


    @registry.command(name="code_upload_chapter", description="Upload one chapter (safe, previewed)")
    @app_commands.checks.has_any_role(SENATORS, REPRESENTATIVES)
    @app_commands.describe(
        title="Title number or key (e.g., 28)",
        chapter="Chapter number (e.g., 13)"
    )
    @app_commands.autocomplete(title=code_title_autocomplete, chapter=chapter_autocomplete)
    async def code_upload_chapter(self, interaction: discord.Interaction, title: str, chapter: str):
        code_root = self.federal_registry.get("spidey_republic_code", {})
        if title not in code_root:
            return await interaction.response.send_message(
                f"Title {title} does not exist. Create it first.", ephemeral=True
            )
        tnode = code_root[title]
        chapters = tnode.get("chapters") or {}
        if str(chapter) not in chapters:
            return await interaction.response.send_message(
                f"Chapter {chapter} does not exist under Title {title}. Create the chapter first.", ephemeral=True
            )

        chapter_dict = chapters[str(chapter)]
        # ensure 'sections' exists
        chapter_dict.setdefault("sections", {})
        # Open the modal. Pass the dict + keys + a reference back to this cog.
        modal = CodeChapterUploadModal(
            cog=self,
            title_key=title,
            chapter_key=str(chapter),
            chapter_dict=chapter_dict
        )
        await interaction.response.send_modal(modal)

    @registry.command(name="view_code", description="View code sections from a chapter")
    @app_commands.autocomplete(title=code_title_autocomplete, chap=chapter_autocomplete)
    @app_commands.describe(
        title="Title key/number (e.g., 28)",
        chap="Chapter number (e.g., 13)",
        sec_start="Start at this section (e.g., 1291 or § 1291)",
        sec_end="End at this section (optional)"
    )
    async def view_code(
        self,
        interaction: discord.Interaction,
        title: str,
        chap: str,
        sec_start: str | None = None,
        sec_end: str | None = None,
    ):
        # --- validate title/chapter exist ---
        code_root = self.federal_registry.get("spidey_republic_code", {})
        if title not in code_root:
            return await interaction.response.send_message(f"Title {title} not found.", ephemeral=True)
        tnode = code_root[title]
        chapters = tnode.get("chapters", {})
        if chap not in chapters:
            return await interaction.response.send_message(f"Chapter {chap} not found in Title {title}.", ephemeral=True)
        cnode = chapters[chap]
        sections = cnode.get("sections", {})
        if not sections:
            return await interaction.response.send_message("No sections in this chapter yet.", ephemeral=True)

        # --- helpers ---
        def sec_digits(s: str | None) -> int:
            if not s:
                return 0
            d = "".join(ch for ch in s if ch.isdigit())
            return int(d) if d else 0

        # sort keys like "§ 1291" numerically
        ordered_keys = sorted(sections.keys(), key=lambda k: sec_digits(k))

        # figure out start index (>= sec_start), and optional end cap (<= sec_end)
        start_num = sec_digits(sec_start) if sec_start else None
        end_num = sec_digits(sec_end) if sec_end else None

        start_idx = 0
        if start_num is not None:
            for i, k in enumerate(ordered_keys):
                if sec_digits(k) >= start_num:
                    start_idx = i
                    break
            else:
                return await interaction.response.send_message(
                    f"Couldn’t find a section ≥ {sec_start} in Chapter {chap}.", ephemeral=True
                )

        slice_keys = ordered_keys[start_idx:]
        if end_num is not None:
            slice_keys = [k for k in slice_keys if sec_digits(k) <= end_num]
            if not slice_keys:
                return await interaction.response.send_message(
                    f"No sections found between {sec_start} and {sec_end}.", ephemeral=True
                )

        # --- pack as many sections as will fit in a single embed description ---
        # Discord embed.description limit ~4096; keep a buffer
        BUDGET = 3800
        desc_parts: list[str] = []
        used = 0
        shown = []

        for k in slice_keys:
            sec = sections[k]
            heading = f" — {sec.get('short')}" if sec.get('short') else ""
            body = (sec.get('text') or "").strip()
            block = f"**{k}{heading}**\n{body}\n\n"
            if used + len(block) > BUDGET:
                break
            desc_parts.append(block)
            used += len(block)
            shown.append(k)

        # if the very first section is huge, hard-truncate its body
        if not shown and slice_keys:
            k = slice_keys[0]
            sec = sections[k]
            heading = f" — {sec.get('short')}" if sec.get('short') else ""
            head = f"**{k}{heading}**\n"
            room = max(0, BUDGET - len(head) - 3)  # for "..."
            body = (sec.get('text') or "").strip()
            desc_parts = [head + body[:room] + "..."]
            shown = [k]

        # build and send
        title_desc = cnode.get("description", "")
        embed = discord.Embed(
            title=f"Title {title} — Chapter {chap}" + (f": {title_desc}" if title_desc else ""),
            description="".join(desc_parts)
        )
        footer_bits = [f"Showing {len(shown)} section(s)"]
        if start_num: footer_bits.append(f"from §{start_num}")
        if end_num: footer_bits.append(f"to §{end_num}")
        if len(shown) < len(slice_keys): footer_bits.append("…truncated")
        embed.set_footer(text=" ".join(footer_bits))

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @commands.command(name="citizenship_assign")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def citizenship_assign(self, ctx: commands.Context):

        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

        assigned = skipped = 0
        await ctx.send("Starting automatic citizenship assignment…")

        for member in guild.members:
            if member.bot:
                continue
            # skip if they already have any citizenship role
            if any(r.id in CITIZENSHIP_IDS for r in member.roles):
                skipped += 1
                continue

            role_id = random.choice(tuple(CITIZENSHIP_IDS))
            role = guild.get_role(role_id)
            if not role:
                continue

            try:
                await member.add_roles(role, reason="Automatic citizenship assignment")
                assigned += 1
                await asyncio.sleep(0.5)  # gentle rate-limit buffer; tune as needed
            except (discord.Forbidden, discord.HTTPException) as e:
                await ctx.send(f"Failed to assign {role.name} to {member.mention}: {e}")

        await ctx.send(f"Done. Assigned: {assigned}. Already had one: {skipped}.")
    
    @category.command(name="view_category_info", description="View info about a category")
    @app_commands.describe(
        category="The category to view info about"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="Commons", value="commons"),
        app_commands.Choice(name="Gaming", value="gaming"),
        app_commands.Choice(name="Spideyton, District of Parker", value="dp"),
        app_commands.Choice(name="Crazy Times", value="crazy_times"),
        app_commands.Choice(name="User Themed", value="user_themed"),
    ])
    async def view_category_info(self, interaction: discord.Interaction, category: str):
        cat_key = category.value
        cat_info = CATEGORIES.get(cat_key)
        if not cat_info:
            return await interaction.response.send_message("Category not found.", ephemeral=True)

        role = interaction.guild.get_role(cat_info["role_id"]) if interaction.guild else None
        role_mention = role.mention if role else "Role not found"

        embed = discord.Embed(
            title=f"Category: {cat_info['name']}",
            description=cat_info["description"],
            color=discord.Color.blue()
        )
        embed.add_field(name="Associated Role", value=role_mention, inline=False)
        citizenship = [m for m in interaction.guild.members if CITIZENSHIP.get(cat_key) in [r.id for r in m.roles]] if interaction.guild else []
        embed.add_field(name="Total Citizens", value=str(len(citizenship)), inline=False)
        categories = self.federal_registry.setdefault("categories", {})
        categories.setdefault(cat_key, {})
        governor = categories[cat_key].get("governor")
        if governor:
            member = interaction.guild.get_member(governor) if interaction.guild else None
            governor_name = member.display_name if member else f"User ID {governor}"
            embed.add_field(name="Governor", value=governor_name, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @category.command(name="citizenship_rates", description="View citizenship role assignment rates")
    async def citizenship_rates(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        total_members = sum(1 for m in guild.members if not m.bot)
        with_role = {key: 0 for key in CITIZENSHIP.keys()}
        for member in guild.members:
            if member.bot:
                continue
            for key, role_id in CITIZENSHIP.items():
                if any(r.id == role_id for r in member.roles):
                    with_role[key] += 1

        embed = discord.Embed(
            title="Citizenship Role Assignment Rates",
            description=f"Out of {total_members} non-bot members:",
            color=discord.Color.green()
        )
        for key, count in with_role.items():
            percentage = (count / total_members * 100) if total_members > 0 else 0
            embed.add_field(name=CATEGORIES[key]["name"], value=f"{count} members ({percentage:.2f}%)", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    async def constitution_article_autocomplete(self, interaction, current: str):
        arts = self.federal_registry.get("constitution", {}).get("articles", {})
        keys = sorted((k for k in arts.keys() if str(k).isdigit()), key=lambda k: int(k))
        cur = (current or "").lower(); out=[]
        for k in keys:
            v = arts[k]; lab = f"Art. {self.to_roman(int(k))} — {v.get('heading','')}".strip(" —")
            if cur in lab.lower(): out.append(app_commands.Choice(name=lab, value=int(k)))
        return out[:25]

    async def constitution_amendment_autocomplete(self, interaction, current: str):
        amds = self.federal_registry.get("constitution", {}).get("amendments", {})
        keys = sorted((k for k in amds.keys() if str(k).isdigit()), key=lambda k: int(k))
        cur = (current or "").lower(); out=[]
        for k in keys:
            v = amds[k]; lab = f"Amend. {k} — {v.get('heading','')}".strip(" —")
            if cur in lab.lower(): out.append(app_commands.Choice(name=lab, value=int(k)))
        return out[:25]

    async def constitution_section_autocomplete(self, interaction, current: str):
        ns = interaction.namespace
        bucket = "articles" if getattr(ns, "article", None) is not None else "amendments"
        number = str(getattr(ns, "article", None) or getattr(ns, "amendment", None) or "")
        node = self.federal_registry.get("constitution", {}).get(bucket, {}).get(number)
        if not node: return []
        secs = node.get("sections", {})
        if "text" in secs and len(secs)==1: return []
        keys = sorted((k for k in secs.keys() if str(k).isdigit()), key=lambda k: int(k))
        cur = (current or "").lower(); out=[]
        for k in keys:
            h = secs[k].get("heading","")
            lab = f"Sec. {k}" + (f" — {h}" if h else "")
            if cur in lab.lower(): out.append(app_commands.Choice(name=lab, value=int(k)))
        return out[:25]





    @registry.command(name="constitution_upload_amendment", description="Upload an Amendment via modal")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        number="Amendment number (Arabic input, e.g., 14)",
        heading="Top-level Amendment heading (e.g., Due Process & Equal Protection)"
    )
    async def constitution_upload_amendment(self, interaction: discord.Interaction, number: int, heading: str | None = None):
        const = self.federal_registry.setdefault("constitution", {})
        amd = const.setdefault("amendments", {}).setdefault(str(number), {"heading": "", "sections": {}})

        if heading and heading.strip():
            amd["heading"] = heading.strip()
            save_federal_registry(self.federal_registry)

        await interaction.response.send_modal(
            ConstitutionUploadModal(kind="amendment", number=number, target_node=amd, top_heading=heading)
        )


    @registry.command(name="view_constitution", description="View Articles/Amendments (with headings; IRL or Court labels)")
    @app_commands.autocomplete(article=constitution_article_autocomplete, amendment=constitution_amendment_autocomplete, section=constitution_section_autocomplete)
    @app_commands.choices(style=[
        app_commands.Choice(name="IRL (default)", value="irl"),
        app_commands.Choice(name="Court", value="court"),
    ])
    @app_commands.describe(
        article="Article (Arabic input; autocomplete supports headings)",
        amendment="Amendment (Arabic input; autocomplete supports headings)",
        section="Section number (Arabic; autocomplete supports headings)",
        style="Label style for titles"
    )
    async def view_constitution(
        self,
        interaction: discord.Interaction,
        article: int | None = None,
        amendment: int | None = None,
        section: int | None = None,
        style: str | None = None
    ):
        # XOR guard
        if (article is None and amendment is None) or (article is not None and amendment is not None):
            return await interaction.response.send_message("Specify either an article or an amendment, not both.", ephemeral=True)

        style_val = (style.value if style else "irl")
        const = self.federal_registry.get("constitution", {})
        is_article = article is not None
        number = article if is_article else amendment
        bucket = "articles" if is_article else "amendments"
        node = const.get(bucket, {}).get(str(number))
        if not node:
            return await interaction.response.send_message(f"{'Article' if is_article else 'Amendment'} {number} not found.", ephemeral=True)

        top_heading = node.get("heading") or ""
        title_head = fmt_article(number) if is_article else fmt_amendment(number, style_val)
        title_line = f"{title_head}" + (f" — {top_heading}" if top_heading else "")

        secs = node.get("sections", {})

        # Single-body
        if section is None and "text" in secs and len(secs) == 1:
            embed = discord.Embed(title=f"Constitution — {title_line}", description=secs["text"], color=discord.Color.gold())
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        # Specific section
        if section is not None:
            sd = secs.get(str(section))
            if not sd:
                return await interaction.response.send_message(f"Section {section} not found in {title_head}.", ephemeral=True)
            sec_head = sd.get("heading") or ""
            sec_title = f"Section {section}" + (f". {sec_head}" if sec_head else "")
            embed = discord.Embed(title=f"Constitution — {title_line}", description=f"**{sec_title}**\n{sd.get('text','')}", color=discord.Color.gold())
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        # Pack multiple sections w/ headings
        BUDGET = 3800
        parts, used = [], 0
        # If it was previously single-body and then converted, you’ll have real sections now
        items = sorted(((int(k), v) for k, v in secs.items() if k.isdigit()), key=lambda kv: kv[0])
        for snum, sd in items:
            sec_head = sd.get("heading") or ""
            block = f"**Section {snum}" + (f". {sec_head}" if sec_head else "") + f"**\n{(sd.get('text') or '').strip()}\n\n"
            if used + len(block) > BUDGET:
                break
            parts.append(block); used += len(block)
        if not parts and items:
            snum, sd = items[0]
            head = f"**Section {snum}" + (f". {sd.get('heading')}" if sd.get('heading') else "") + "**\n"
            room = max(0, BUDGET - len(head) - 3)
            parts = [head + (sd.get('text') or "")[:room] + "..."]

        embed = discord.Embed(title=f"Constitution — {title_line}", description="".join(parts), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @registry.command(name="constitution_set_heading", description="Set a heading (Article/Amendment or specific Section)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        article="Article number (Arabic, e.g., 1)",
        amendment="Amendment number (Arabic, e.g., 14)",
        section="Section number (optional; leave empty to set the Article/Amendment heading)"
    )
    async def constitution_set_heading(
        self,
        interaction: discord.Interaction,
        article: int | None = None,
        amendment: int | None = None,
        section: int | None = None
    ):
        # XOR on article/amendment
        if (article is None and amendment is None) or (article is not None and amendment is not None):
            return await interaction.response.send_message(
                "Specify either an article or an amendment (not both).", ephemeral=True
            )
        const = self.federal_registry.setdefault("constitution", {})
        bucket = "articles" if article is not None else "amendments"
        number = article if article is not None else amendment
        node = const.setdefault(bucket, {}).get(str(number))
        if not node:
            return await interaction.response.send_message(f"{bucket[:-1].capitalize()} {number} not found.", ephemeral=True)

        path_label = f"{'Article' if bucket=='articles' else 'Amendment'} {number}"
        target = node
        if section is not None:
            secs = node.get("sections", {})
            s = secs.get(str(section))
            if not s:
                return await interaction.response.send_message(f"Section {section} not found in {path_label}.", ephemeral=True)
            target = s
            path_label = f"{path_label}, Section {section}"

        await interaction.response.send_modal(ConstitutionSetHeadingModal(path_label=path_label, node=target))

    async def bill_id_autocomplete(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        items = self.federal_registry.get("bills", {}).get("items", {})
        out = []
        for bid, b in items.items():
            label = f"{bid} — {b.get('title','')}"
            if current in label.lower():
                out.append(app_commands.Choice(name=label[:100], value=bid))
        return out[:25]

    @legislature.command(name="bill_view", description="View a bill/resolution draft")
    @app_commands.autocomplete(bill_id=bill_id_autocomplete)
    @app_commands.describe(bill_id="ID like S-0001 or H-0003")
    async def bill_view(self, interaction: discord.Interaction, bill_id: str):
        items = self.federal_registry.get("bills", {}).get("items", {})
        b = items.get(bill_id)
        if not b:
            return await interaction.response.send_message("Bill not found.", ephemeral=True)

        kind = "Bill" if b.get("type") == "bill" else "Resolution"
        joint_prefix = "Joint " if b.get("joint") else ""
        head = f"{b.get('chamber','?')} {joint_prefix}{kind} {bill_id}"

        # Meta embed (fields capped to 1024)
        meta = discord.Embed(
            title=head,
            description=(b.get("summary") or ""),
            color=discord.Color.blurple()
        )
        meta.add_field(name="Title", value=b.get("title","")[:1024] or "—", inline=False)
        if b.get("purpose"):
            meta.add_field(name="Purpose", value=b["purpose"][:1024], inline=False)
        if b.get("committee"):
            meta.add_field(name="Committee", value=b["committee"][:1024], inline=True)
        if b.get("co_sponsors"):
            meta.add_field(name="Co-sponsors", value=", ".join(b["co_sponsors"])[:1024], inline=False)
        meta.add_field(name="Status", value=b.get("status","DRAFT")[:1024], inline=True)
        if b.get("authority"):
            meta.add_field(name="Authority", value=b["authority"].get("primary_label","(unspecified)")[:1024], inline=False)
        if b.get("codification") or b.get("repealing"):
            cod = "Codification" if b.get("codification") else "Repeal"
            meta.add_field(
                name="Code Impact",
                value=f"{cod}: Title {b.get('code_title','?')} §§ {b.get('sections','?')}"[:1024],
                inline=False
            )

        # Build pages by bolding only heading lines, preserving your exact text
        pages = _bold_headings_preserve(b.get("text") or "")
        await interaction.response.send_message(embed=meta, ephemeral=False)

        if not pages:
            return  # no body text to show

        # Send the bill text as paginated description embeds (≤4096 each)
        total = len(pages)
        for i, txt in enumerate(pages, start=1):
            e = discord.Embed(
                title=f"{bill_id} — Text ({i}/{total})",
                description=txt[:4000],
                color=discord.Color.blurple()
            )
            await interaction.followup.send(embed=e)



    @legislature.command(name="docket", description="List active bills/resolutions by chamber")
    @app_commands.choices(chamber=[
        app_commands.Choice(name="Senate", value="Senate"),
        app_commands.Choice(name="House", value="House"),
    ])
    async def docket(self, interaction: discord.Interaction, chamber: str):
        items = self.federal_registry.get("bills", {}).get("items", {})
        # show DRAFT/INTRODUCED/IN_COMMITTEE/FLOOR; hide PASSED/FAILED/ENACTED by default
        active = [b for b in items.values() if b.get("chamber")==chamber.value and b.get("status") in {"DRAFT","INTRODUCED","IN_COMMITTEE","FLOOR"}]
        if not active:
            return await interaction.response.send_message(f"No active items in the {chamber.value}.", ephemeral=True)

        active.sort(key=lambda x: x["id"])
        desc = []
        for b in active[:15]:
            kind = "Bill" if b["type"] == "bill" else "Resolution"
            joint = " (Joint)" if b.get("joint") else ""
            desc.append(f"**{b['id']}** — {kind}{joint}: {b.get('title','')}  ·  *{b.get('status')}*")
        embed = discord.Embed(title=f"{chamber.value} Docket", description="\n".join(desc), color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, ephemeral=False)



    @executive.command(name="eo_new", description="Draft and issue an Executive Order (modal)")
    @app_commands.checks.has_permissions(administrator=True)
    async def eo_new(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ExecutiveOrderModal(self))

    @executive.command(name="eo_view", description="View an Executive Order")
    @app_commands.describe(eo_id="e.g., EO-2025-0001")
    async def eo_view(self, interaction: discord.Interaction, eo_id: str):
        reg = self.federal_registry
        order = reg.get("executive_orders", {}).get("items", {}).get(eo_id)
        if not order:
            return await interaction.response.send_message("Executive Order not found.", ephemeral=True)

        pages = _format_eo_for_display(order)
        head = discord.Embed(
            title=f"{eo_id} — {order.get('title','')}",
            description=(order.get("summary") or ""),
            color=discord.Color.dark_gold()
        )
        await interaction.response.send_message(embed=head, ephemeral=False)
        for p in pages:
            await interaction.followup.send(embed=discord.Embed(description=p[:4000], color=discord.Color.dark_gold()))


    async def eo_id_autocomplete(self, interaction: discord.Interaction, current: str):
        current = (current or "").lower()
        items = self.federal_registry.get("executive_orders", {}).get("items", {})
        out = []
        for k, v in items.items():
            label = f"{k} — {v.get('title','')}"
            if current in label.lower(): out.append(app_commands.Choice(name=label[:100], value=k))
        return out[:25]

    @executive.command(name="eo_list", description="List EOs (optionally by year/status)")
    @app_commands.describe(year="Year (e.g., 2025)", status="ACTIVE or RESCINDED")
    async def eo_list(self, interaction: discord.Interaction, year: int | None = None, status: str | None = None):
        items = self.federal_registry.get("executive_orders", {}).get("items", {})
        rows = []
        for k, v in sorted(items.items()):
            if year and not k.startswith(f"EO-{year}-"): continue
            if status and v.get("status") != status: continue
            rows.append(f"**{k}** — {v.get('title','')}")
        if not rows: return await interaction.response.send_message("No matching EOs.", ephemeral=True)
        await interaction.response.send_message("\n".join(rows[:30]), ephemeral=False)

    @executive.command(name="eo_rescind", description="Rescind (revoke) an Executive Order")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(eo_id=eo_id_autocomplete)
    @app_commands.describe(eo_id="EO ID", reason="Reason for rescission")
    async def eo_rescind(self, interaction: discord.Interaction, eo_id: str, reason: str | None = None):
        reg = self.federal_registry
        items = ensure_eo_schema(reg)["items"]
        order = items.get(eo_id)
        if not order: return await interaction.response.send_message("EO not found.", ephemeral=True)
        if order["status"] == "RESCINDED": return await interaction.response.send_message("EO already rescinded.", ephemeral=True)
        order["status"] = "RESCINDED"
        order["rescinded_at"] = discord.utils.utcnow().isoformat()
        order["rescinded_by"] = interaction.user.id
        order["rescission_reason"] = reason or ""
        save_federal_registry(reg)
        await interaction.response.send_message(f"✅ Rescinded {eo_id}.", ephemeral=True)

    @legislature.command(name="bill_view_sections", description="List amendable sections of a bill")
    @app_commands.autocomplete(bill_id=bill_id_autocomplete)
    async def bill_view_sections(self, interaction: discord.Interaction, bill_id: str):
        b = self.federal_registry.get("bills", {}).get("items", {}).get(bill_id)
        if not b: return await interaction.response.send_message("Bill not found.", ephemeral=True)
        struct = b.get("structure")
        if not struct: return await interaction.response.send_message("This bill isn't structured into sections.", ephemeral=True)
        rows = []
        for tid, t, s in index_sections(struct):
            tlabel = f"Title {t['n']}" + (f": {t['heading']}" if t.get("heading") else "")
            slabel = f"Sec. {s['n']}" + (f". {s['heading']}" if s.get("heading") else "")
            rows.append(f"**{tid}** — {tlabel} — {slabel}")
        await interaction.response.send_message("\n".join(rows[:40]), ephemeral=False)

    def next_amend_id(self, bill: dict) -> str:
        # simple per-bill sequence
        seq = bill.setdefault("_amend_seq", 0) + 1
        bill["_amend_seq"] = seq
        return f"A-{seq:03d}"
    
    async def bill_target_autocomplete(self, interaction: discord.Interaction, current: str):
        ns = interaction.namespace
        bill_id = getattr(ns, "bill_id", None)
        if not bill_id: return []
        b = self.federal_registry.get("bills", {}).get("items", {}).get(bill_id)
        if not b or not b.get("structure"): return []
        cur = (current or "").lower()
        out = []
        for tid, t, s in index_sections(b["structure"]):
            label = f"{tid} — Title {t['n']}" + (f": {t['heading']}" if t.get("heading") else "") + \
                    f" — Sec. {s['n']}" + (f". {s.get('heading')}" if s.get('heading') else "")
            if cur in label.lower():
                out.append(app_commands.Choice(name=label[:100], value=tid))
        return out[:25]




    @legislature.command(name="bill_amend_new", description="Propose a section-level amendment (no mutation; preview only)")
    @app_commands.autocomplete(bill_id=bill_id_autocomplete, target_id=bill_target_autocomplete)
    @app_commands.choices(op=[
        app_commands.Choice(name="Replace section", value="replace"),
        app_commands.Choice(name="Insert new section after target", value="insert_after"),
        app_commands.Choice(name="Insert new section at end of Title", value="insert_end"),
        app_commands.Choice(name="Delete section", value="delete"),
    ])
    @app_commands.describe(
        bill_id="Bill ID (e.g., S-0001)",
        target_id="Target like T1.S2 (or T1 for insert_end)",
        op="Amendment operation",
        section_heading="New section heading (for replace/insert ops)",
        body="New section body (for replace/insert ops)",
        rationale="Short reason for the change (optional)"
    )
    async def bill_amend_new(
        self,
        interaction: discord.Interaction,
        bill_id: str,
        target_id: str,
        op: str,
        section_heading: str | None = None,
        body: str | None = None,
        rationale: str | None = None,
    ):
        import re, difflib

        # ---- inline helpers (kept local so this is copy-pasteable) ----
        def _parse_target_tid(tid: str) -> tuple[int | None, int | None]:
            """
            'T1.S2' -> (1,2)
            'T1'    -> (1,None)
            """
            m = re.fullmatch(r"T(\d+)(?:\.S(\d+))?$", (tid or "").strip(), flags=re.I)
            if not m:
                return None, None
            t_no = int(m.group(1))
            s_no = int(m.group(2)) if m.group(2) else None
            return t_no, s_no

        def _find_section(struct: dict, t_no: int, s_no: int) -> tuple[dict | None, dict | None]:
            for t in struct.get("titles", []):
                if t.get("n") != t_no:
                    continue
                for s in t.get("sections", []):
                    if s.get("n") == s_no:
                        return t, s
                return t, None
            return None, None

        def _mkdiff(a: str, b: str, ctx: int = 3) -> str:
            return "\n".join(
                difflib.unified_diff((a or "").splitlines(), (b or "").splitlines(), lineterm="", n=ctx)
            )

        def _next_amend_id(bill: dict) -> str:
            seq = bill.setdefault("_amend_seq", 0) + 1
            bill["_amend_seq"] = seq
            return f"A-{seq:03d}"

        # ---- load bill & structure ----
        reg = self.federal_registry
        items = reg.get("bills", {}).get("items", {})
        bill = items.get(bill_id)
        if not bill:
            return await interaction.response.send_message("Bill not found.", ephemeral=True)
        struct = bill.get("structure")
        if not struct or not struct.get("titles"):
            return await interaction.response.send_message("This bill is not structured into titles/sections.", ephemeral=True)

        t_no, s_no = _parse_target_tid(target_id)
        if op.value in {"replace", "delete", "insert_after"} and (not t_no or not s_no):
            return await interaction.response.send_message(
                "Target must be a section like **T1.S2** for this operation.", ephemeral=True
            )
        if op.value == "insert_end" and not t_no:
            return await interaction.response.send_message(
                "For **insert_end**, target must be a title like **T1**.", ephemeral=True
            )

        # fetch nodes (for ops that need an existing section)
        tnode = snode = None
        if s_no is not None:
            tnode, snode = _find_section(struct, t_no, s_no)
            if op.value != "insert_end" and not snode:
                return await interaction.response.send_message("Target section not found.", ephemeral=True)

        # validate new content where required
        if op.value in {"replace", "insert_after", "insert_end"}:
            if not body or not body.strip():
                return await interaction.response.send_message("Body is required for this operation.", ephemeral=True)

        # capture old text for preview/history (when applicable)
        old_heading = snode.get("heading") if snode else ""
        old_body = snode.get("body") if snode else ""

        # build amendment record (no mutations yet)
        amend_id = _next_amend_id(bill)
        amend = {
            "id": amend_id,
            "op": op.value,
            "target_id": f"T{t_no}" + (f".S{s_no}" if s_no is not None else ""),
            "title_no": t_no if op.value == "insert_end" else None,
            "new_heading": (section_heading or "").strip() if op.value in {"replace","insert_after","insert_end"} else "",
            "new_body": (body or "").strip() if op.value in {"replace","insert_after","insert_end"} else "",
            "old_heading": old_heading,
            "old_body": old_body,
            "rationale": (rationale or "").strip(),
            "proposed_by": interaction.user.id,
            "proposed_at": discord.utils.utcnow().isoformat(),
            "status": "PENDING",
            "version_base": struct.get("version", 1),
            "vote_msg_id": None,
        }
        bill.setdefault("amendments", {})[amend_id] = amend
        save_federal_registry(reg)

        # ---- build a preview embed (no side effects) ----
        if op.value == "replace":
            ud = _mkdiff(old_body, amend["new_body"], ctx=3)
            preview = f"```diff\n{ud[:3500]}\n```" if ud else "(no textual changes)"
        elif op.value == "insert_after":
            preview = (
                f"Insert **after** T{t_no}.S{s_no}\n"
                + (f"**Heading:** {amend['new_heading']}\n\n" if amend['new_heading'] else "")
                + amend["new_body"][:1800]
            )
        elif op.value == "insert_end":
            preview = (
                f"Append as **new final section** of Title {t_no}\n"
                + (f"**Heading:** {amend['new_heading']}\n\n" if amend['new_heading'] else "")
                + amend["new_body"][:1800]
            )
        else:  # delete
            preview = f"Delete **T{t_no}.S{s_no}**\n\n{old_body[:1800]}"

        desc = f"**{bill_id}** — Proposed {op.name} at **{amend['target_id']}**"
        embed = discord.Embed(title=f"Amendment {amend_id}", description=desc, color=discord.Color.orange())
        if amend["rationale"]:
            embed.add_field(name="Rationale", value=amend["rationale"][:1024], inline=False)

        # Replace usually has a big diff; put it in description when small, else as a field
        if op.value == "replace" and len(preview) < 3900:
            embed.description += "\n\n" + preview
        else:
            embed.add_field(name="Preview", value=preview[:1024] if op.value != "replace" else preview[:1024], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)


    def _apply_amendment(self, bill: dict, amend: dict) -> bool:
        struct = bill.get("structure")
        if not struct: return False
        # simple optimistic apply; if text moved, we still target by numeric ids
        tid = amend["target_id"]
        # Find title list + index, and section list + index
        for t in struct["titles"]:
            if not t.get("sections"): continue
            for idx, s in enumerate(t["sections"]):
                cur_id = f"T{t['n']}.S{s['n']}"
                if cur_id == tid:
                    op = amend["op"]
                    if op == "replace":
                        if amend.get("new_heading"): s["heading"] = amend["new_heading"]
                        s["body"] = amend.get("new_body","")
                    elif op == "delete":
                        del t["sections"][idx]
                    elif op == "insert_after":
                        new_n = (s["n"] + 1)
                        # shift later numbers up by 1 to keep numeric order tidy
                        for s2 in t["sections"]:
                            if s2["n"] >= new_n:
                                s2["n"] += 1
                        t["sections"].append({"n": new_n, "heading": amend.get("new_heading",""), "body": amend.get("new_body","")})
                        t["sections"].sort(key=lambda x: x["n"])
                    struct["version"] = struct.get("version",1) + 1
                    return True
        return False
    
    

    @legislature.command(name="bill_amend_apply", description="Apply an adopted amendment (admin)")
    @app_commands.checks.has_any_role(SENATE_MAJORITY_LEADER, SPEAKER_OF_THE_HOUSE)
    @app_commands.autocomplete(bill_id=bill_id_autocomplete)
    @app_commands.describe(bill_id="Bill ID", amend_id="Amendment ID like A-001")
    async def bill_amend_apply(self, interaction: discord.Interaction, bill_id: str, amend_id: str):
        reg = self.federal_registry
        b = reg.get("bills", {}).get("items", {}).get(bill_id)
        if not b: return await interaction.response.send_message("Bill not found.", ephemeral=True)
        amend = b.get("amendments", {}).get(amend_id)
        if not amend: return await interaction.response.send_message("Amendment not found.", ephemeral=True)
        if amend["status"] not in {"PENDING","ADOPTED"}:
            return await interaction.response.send_message(f"Cannot apply amendment in status {amend['status']}.", ephemeral=True)

        ok = self._apply_amendment(b, amend)
        if not ok:
            return await interaction.response.send_message("Apply failed (target not found).", ephemeral=True)

        amend["status"] = "ADOPTED"
        amend["applied_at"] = discord.utils.utcnow().isoformat()
        save_federal_registry(reg)
        await interaction.response.send_message(f"✅ Applied {amend_id} to {bill_id}.", ephemeral=True)

    async def parent_committee_autocomplete(self, interaction: discord.Interaction, current: str):
        # Determine chamber from caller’s roles (leader → senate, else house)
        user_role_ids = {r.id for r in getattr(interaction.user, "roles", [])}
        chamber = "senate" if SENATE_MAJORITY_LEADER in user_role_ids else "house"

        committees = self.federal_registry.setdefault("committees", {
            "senate": {},
            "house": {},
            "joint": {},
        })
        chamber_committees = committees.get(chamber, {})

        cur = (current or "").lower()
        choices: list[app_commands.Choice[str]] = []

        # Only top-level committees
        for key, data in sorted(chamber_committees.items(), key=lambda kv: kv[0]):
            label = (data.get("name") or key.replace("_", " ").title()).strip()
            if not cur or cur in label.lower():
                choices.append(app_commands.Choice(name=label, value=key))

        return choices[:25]



    @legislature.command(name="create_committee", description="Create a congressional committee or subcommittee")
    @app_commands.checks.has_any_role(SENATE_MAJORITY_LEADER, SPEAKER_OF_THE_HOUSE)
    @app_commands.describe(
        name="The name of the committee",
        committee_type="Type (standing, select, joint, special, ad_hoc)",
        chair="Chair of the Committee",
        sub_committee="Is this a subcommittee?",
        parent_committee="If a subcommittee, the parent committee (key from autocomplete)"
    )
    @app_commands.autocomplete(parent_committee=parent_committee_autocomplete)
    @app_commands.choices(committee_type=[
        app_commands.Choice(name="Standing", value="standing"),
        app_commands.Choice(name="Select", value="select"),
        app_commands.Choice(name="Joint", value="joint"),
        app_commands.Choice(name="Special", value="special"),
        app_commands.Choice(name="Ad hoc", value="ad_hoc"),
    ])
    async def create_committee(
        self,
        interaction: discord.Interaction,
        name: str,
        committee_type: str | str = "standing",
        *,
        chair: discord.Member,
        sub_committee: bool = False,
        parent_committee: str | None = None,
    ):
        # normalize choice -> str
        ctype = committee_type.value if isinstance(committee_type, app_commands.Choice) else committee_type

        # decide bucket (senate/house or joint)
        user_role_ids = {r.id for r in getattr(interaction.user, "roles", [])}
        chamber = "joint" if ctype == "joint" else ("senate" if SENATE_MAJORITY_LEADER in user_role_ids else "house")

        reg = self.federal_registry
        committees = reg.setdefault("committees", {"senate": {}, "house": {}, "joint": {}})
        chamber_committees = committees.setdefault(chamber, {})

        key = name.strip().lower().replace(" ", "_")
        if key in chamber_committees:
            return await interaction.response.send_message("A committee with that name already exists.", ephemeral=True)

        # parent/child rules
        if sub_committee and not parent_committee:
            return await interaction.response.send_message("A parent committee must be specified for a subcommittee.", ephemeral=True)

        if parent_committee:
            parent_key = parent_committee.strip().lower()
            parent = chamber_committees.get(parent_key)
            if not parent:
                return await interaction.response.send_message("The specified parent committee does not exist.", ephemeral=True)
            if not sub_committee:
                return await interaction.response.send_message("Only subcommittees can have a parent committee.", ephemeral=True)

        # build record
        record = {
            "name": name,
            "type": ctype,
            "chair_id": chair.id,
            "members": [chair.id],
            "created_at": discord.utils.utcnow().isoformat(),
            "created_by": interaction.user.id,
        }

        if sub_committee:
            parent = chamber_committees[parent_key]  # from above
            parent.setdefault("sub_committees", {})[key] = record
        else:
            chamber_committees[key] = {**record, "sub_committees": {}}

        save_federal_registry(reg)
        where = "Joint" if chamber == "joint" else chamber.title()
        await interaction.response.send_message(f"✅ Created committee '{name}' in the {where}.", ephemeral=True)

    @legislature.command(name="view_committees", description="View the Congressional Committees")
    @app_commands.describe(filter="Narrow to specific body")
    @app_commands.choices(filter=[
        app_commands.Choice(name="Joint", value="joint"),
        app_commands.Choice(name="House", value="house"),
        app_commands.Choice(name="Senate", value="senate"),
    ])
    async def view_committees(self, interaction: discord.Interaction, filter: str | None = None):
        reg = self.federal_registry
        committees = reg.setdefault("committees", {"senate": {}, "house": {}, "joint": {}})

        title = f"{'Congressional' if not filter else filter.title()} Committees"
        embed = discord.Embed(title=title, color=discord.Color.blurple())

        def render_bucket(bucket: dict) -> list[str]:
            """Return formatted lines for a chamber bucket (committee + subcommittees)."""
            lines: list[str] = []
            for key, data in sorted(bucket.items(), key=lambda kv: kv[0]):  # sort by key
                name = (data.get("name") or key.replace("_", " ").title()).strip()
                lines.append(f"• {name}")
                subs = data.get("sub_committees") or {}
                for sk, sv in sorted(subs.items(), key=lambda kv: kv[0]):
                    sname = (sv.get("name") or sk.replace("_", " ").title()).strip()
                    lines.append(f"  └─ {sname}")
            return lines or ["(none)"]

        def add_field_safely(heading: str, lines: list[str]) -> None:
            """Discord field values max at 1024 chars; chunk if needed."""
            buf = ""
            part = 1
            for line in lines:
                newline = line + "\n"
                if len(buf) + len(newline) > 1024:
                    embed.add_field(name=heading if part == 1 else f"{heading} (cont.)", value=buf, inline=False)
                    buf = newline
                    part += 1
                else:
                    buf += newline
            if buf:
                embed.add_field(name=heading if part == 1 else f"{heading} (cont.)", value=buf, inline=False)

        # If a filter is provided, only show that bucket; otherwise show all three.
        if filter:
            bucket = committees.get(filter, {})
            add_field_safely(filter.title(), render_bucket(bucket))
        else:
            add_field_safely("Joint", render_bucket(committees.get("joint", {})))
            add_field_safely("House", render_bucket(committees.get("house", {})))
            add_field_safely("Senate", render_bucket(committees.get("senate", {})))

        await interaction.response.send_message(embed=embed)

    async def committee_name_autocomplete(self, interaction: discord.Interaction, current: str):
        """Return committees + subcommittees for the chosen chamber, sorted."""
        reg = self.federal_registry
        committees = _get_committees_root(reg)  # your existing helper

        # Chamber comes from the sibling option on the same slash command
        ns = interaction.namespace
        chamber = getattr(ns, "chamber", None)
        if isinstance(chamber, app_commands.Choice):
            chamber = chamber.value
        if chamber not in {"senate", "house", "joint"}:
            return []

        cur = (current or "").lower()
        out: list[app_commands.Choice[str]] = []
        bucket = committees.get(chamber, {})

        # Top-level committees
        for key, data in sorted(bucket.items(), key=lambda kv: kv[0]):
            label = (data.get("name") or key.replace("_", " ").title()).strip()
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label, value=key))
            # Subcommittees
            subs = data.get("sub_committees") or {}
            for sk, sv in sorted(subs.items(), key=lambda kv: kv[0]):
                slabel = (sv.get("name") or sk.replace("_", " ").title()).strip()
                full = f"{label} → {slabel}"
                if not cur or cur in full.lower():
                    # encode parent::child so handlers can resolve it
                    out.append(app_commands.Choice(name=full, value=f"{key}::{sk}"))

        return out[:25]


    @legislature.command(name="committee_info", description="Details about a (sub)committee")
    @app_commands.choices(chamber=[
        app_commands.Choice(name="Senate", value="senate"),
        app_commands.Choice(name="House", value="house"),
        app_commands.Choice(name="Joint", value="joint"),
    ])
    @app_commands.autocomplete(name=committee_name_autocomplete)
    @app_commands.describe(
        chamber="Which body the committee belongs to",
        name="Committee or subcommittee (autocomplete)",
    )
    async def committee_info(self, interaction: discord.Interaction, chamber: str, name: str):
        reg = self.federal_registry
        committees = _get_committees_root(reg)
        bucket = committees.get(chamber.value, {})

        # Resolve committee vs subcommittee from encoded value
        parent_key = None
        sub_key = None
        if "::" in name:
            parent_key, sub_key = name.split("::", 1)
        else:
            parent_key = name

        node = None
        parent = None
        if sub_key:
            parent = bucket.get(parent_key)
            if parent:
                node = (parent.get("sub_committees") or {}).get(sub_key)
        else:
            node = bucket.get(parent_key)

        if not node:
            return await interaction.response.send_message("Committee not found.", ephemeral=True)

        # Basics
        pretty_name = node.get("name") or (sub_key or parent_key).replace("_", " ").title()
        ctype = node.get("type", "standing").replace("_", " ").title()
        chair_id = node.get("chair_id")
        members = node.get("members") or []
        subcs = []
        if not sub_key:
            # Only show subcommittees when viewing a top-level committee
            subcs = list((node.get("sub_committees") or {}).values())

        # Next hearing
        hearing_title, hearing_dt = _next_hearing_info(node)

        # Build embed (lean and within field limits)
        title_prefix = chamber.name.title() if isinstance(chamber, app_commands.Choice) else str(chamber).title()
        embed = discord.Embed(
            title=f"{title_prefix} — {pretty_name}",
            color=discord.Color.teal()
        )
        embed.add_field(name="Type", value=ctype, inline=True)
        if chair_id:
            embed.add_field(name="Chair", value=_format_member_mention(interaction.guild, chair_id), inline=True)
        embed.add_field(name="# Members", value=str(len(set(members))), inline=True)

        # Subcommittees list (compact; truncated safely)
        if subcs:
            names = [("• " + (sc.get("name") or "").strip()) for sc in subcs if (sc.get("name") or "").strip()]
            text = "\n".join(names)
            if len(text) > 1024:
                # trim conservatively to avoid field limit
                trimmed = []
                total = 0
                for n in names:
                    if total + len(n) + 1 > 1000:
                        trimmed.append(f"(+{max(0, len(names) - len(trimmed))} more)")
                        break
                    trimmed.append(n)
                    total += len(n) + 1
                text = "\n".join(trimmed)
            embed.add_field(name="Subcommittees", value=text or "(none)", inline=False)

        # Hearing info
        if hearing_dt:
            # nice absolute + relative time display
            embed.add_field(
                name="Next Hearing",
                value=f"**{hearing_title or '(untitled)'}**\n"
                    f"{discord.utils.format_dt(hearing_dt, style='F')} "
                    f"({discord.utils.format_dt(hearing_dt, style='R')})",
                inline=False
            )
        else:
            embed.add_field(name="Next Hearing", value="(none scheduled)", inline=False)

        await interaction.response.send_message(embed=embed)

    
    @legislature.command(name="committee_hearing_schedule", description="Schedule a hearing (committee/subcommittee)")
    @app_commands.choices(chamber=[
        app_commands.Choice(name="Senate", value="senate"),
        app_commands.Choice(name="House", value="house"),
        app_commands.Choice(name="Joint", value="joint"),
    ])
    @app_commands.autocomplete(name=committee_name_autocomplete)  # your existing autocomplete
    @app_commands.choices(tz=_TZ_CHOICES)
    @app_commands.describe(
        chamber="Body",
        name="Committee or subcommittee (autocomplete)",
        title="Hearing title",
        date="YYYY-MM-DD (e.g., 2025-10-03)",
        time="Local time (e.g., 6:00 pm or 18:00)",
        tz="Timezone for the provided date/time",
    )
    async def committee_hearing_schedule(
        self,
        interaction: discord.Interaction,
        chamber: str,
        name: str,
        title: str,
        date: str,
        time: str,
        tz: str = None,  # default PT
    ):
        if not tz:
            tz = _TZ_CHOICES[0]
        reg = self.federal_registry
        parent, node = _resolve_committee_node(reg, chamber.value, name)
        if not node:
            return await interaction.response.send_message("Committee not found.", ephemeral=True)

        # Permission: chair or leadership override
        if not (_user_is_committee_chair(interaction.guild, interaction.user, node) or _user_has_leadership_override(interaction.user)):
            return await interaction.response.send_message("Only the committee chair (or leadership) may schedule hearings.", ephemeral=True)

        dt_local = _build_aware_dt(date, time, tz.value)
        if not dt_local:
            return await interaction.response.send_message("Invalid date/time. Use date=YYYY-MM-DD and time like '6:00 pm' or '18:00'.", ephemeral=True)

        # Store as UTC ISO for durability
        dt_utc = dt_local.astimezone(timezone.utc)
        node.setdefault("hearings", []).append({
            "title": title,
            "when": dt_utc.isoformat(),
            "status": "scheduled",
            "scheduled_by": interaction.user.id,
        })
        save_federal_registry(reg)

        # Confirm with pretty Discord timestamps
        embed = discord.Embed(
            title="Hearing scheduled",
            description=(parent.get("name") + " → " + node.get("name")) if parent else node.get("name"),
            color=discord.Color.teal()
        )
        embed.add_field(name="Title", value=title, inline=False)
        embed.add_field(
            name="When",
            value=f"{discord.utils.format_dt(dt_local, style='F')} ({discord.utils.format_dt(dt_local, style='R')})",
            inline=False
        )
        embed.set_footer(text=f"{chamber.name.title()} committee")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @legislature.command(name="committee_manage", description="Add/remove members, set chair, or bulk-appoint by role")
    @app_commands.choices(chamber=[
        app_commands.Choice(name="Senate", value="senate"),
        app_commands.Choice(name="House", value="house"),
        app_commands.Choice(name="Joint", value="joint"),
    ])
    @app_commands.choices(action=[
        app_commands.Choice(name="Add member", value="add_member"),
        app_commands.Choice(name="Remove member", value="remove_member"),
        app_commands.Choice(name="Set chair", value="set_chair"),
        app_commands.Choice(name="Bulk add by role", value="bulk_add_role"),
    ])
    @app_commands.autocomplete(name=committee_name_autocomplete)
    @app_commands.describe(
        chamber="Body",
        name="Committee or subcommittee (autocomplete)",
        action="What to do",
        member="Target user (required for add/remove/set chair)",
        role="Role to bulk-appoint (required for bulk add)",
        as_chair="When adding: also make this member the chair",
        force="When removing: allow removing the current chair"
    )
    async def committee_manage(
        self,
        interaction: discord.Interaction,
        chamber: str,
        name: str,
        action: str,
        member: discord.Member | None = None,
        role: discord.Role | None = None,
        as_chair: bool = False,
        force: bool = False,
    ):
        act = action.value
        ch = chamber.value

        # perms
        if not _is_chamber_leader(interaction.user, ch):
            return await interaction.response.send_message("Only the chamber leader may manage committees.", ephemeral=True)

        # resolve node
        reg = self.federal_registry
        parent, node = _resolve_committee_node(reg, ch, name)
        if not node:
            return await interaction.response.send_message("Committee not found.", ephemeral=True)

        # validate args per action
        if act in {"add_member", "remove_member", "set_chair"} and member is None:
            return await interaction.response.send_message("Please specify a member.", ephemeral=True)
        if act == "bulk_add_role" and role is None:
            return await interaction.response.send_message("Please specify a role.", ephemeral=True)

        # perform
        async with getattr(self, "registry_lock", asyncio.Lock()):
            if act == "add_member":
                _add_member(node, member.id)
                if as_chair:
                    node["chair_id"] = member.id
                save_federal_registry(reg)
                role_note = " (Chair)" if as_chair else ""
                msg = f"✅ Appointed {member.mention}{role_note} to **{node.get('name','(unnamed)')}**."

            elif act == "remove_member":
                chair_id = node.get("chair_id")
                if chair_id == member.id and not force:
                    return await interaction.response.send_message(
                        "That member is the chair. Use `force=True` or set a new chair first.", ephemeral=True
                    )
                members = set(node.get("members") or [])
                if member.id in members:
                    members.remove(member.id)
                    node["members"] = sorted(members)
                if chair_id == member.id:
                    node["chair_id"] = None
                save_federal_registry(reg)
                msg = f"✅ Removed {member.mention} from **{node.get('name','(unnamed)')}**."

            elif act == "set_chair":
                node["chair_id"] = member.id
                _add_member(node, member.id)
                save_federal_registry(reg)
                msg = f"✅ {member.mention} set as Chair of **{node.get('name','(unnamed)')}**."

            elif act == "bulk_add_role":
                added = 0
                for m in role.members:
                    if m.bot:
                        continue
                    if _add_member(node, m.id):
                        added += 1
                save_federal_registry(reg)
                msg = f"✅ Appointed **{added}** members from {role.mention} to **{node.get('name','(unnamed)')}**."

            else:
                return await interaction.response.send_message("Unknown action.", ephemeral=True)

        where = chamber.name.title()
        await interaction.response.send_message(f"{msg} ({where})", ephemeral=True)
    
    @legislature.command(name="report_bill", description="Introduce, vote, transmit, enroll, or present a bill")
    @app_commands.autocomplete(bill_id=bill_id_autocomplete)
    @app_commands.choices(action=[
        app_commands.Choice(name="Introduce bill", value="introduce"),
        app_commands.Choice(name="Open floor vote", value="open_vote"),
        app_commands.Choice(name="Close floor vote", value="close_vote"),
        app_commands.Choice(name="Send to other chamber", value="send_other"),
        app_commands.Choice(name="Receive from other chamber", value="receive_other"),
        app_commands.Choice(name="Mark second chamber PASSED", value="mark_second_passed"),
        app_commands.Choice(name="Enroll (freeze text)", value="enroll"),
        app_commands.Choice(name="Present to President", value="present"),
        app_commands.Choice(name="Status (quick view)", value="status"),
    ])
    @app_commands.choices(threshold=[
        app_commands.Choice(name="Simple majority", value="simple"),
        app_commands.Choice(name="Two-thirds", value="two_thirds"),
        app_commands.Choice(name="Three-fifths", value="three_fifths"),
    ])
    @app_commands.describe(
        action="What do you want to do?",
        bill_id="Existing bill ID (omit when introducing)",
        chamber="For introduction only: Senate or House",
        title="Short title (introduction)",
        summary="1-2 sentence summary (introduction)",
        text="Bill text (introduction)",
        joint="Is this a joint resolution? (introduction)",
        hours="Poll duration (open_vote)",
        threshold="Vote threshold (open_vote/close_vote)",
        notify="DM eligible members the poll link (open_vote)"
    )
    async def report_bill(
        self,
        interaction: discord.Interaction,
        action: str,
        bill_id: str | None = None,
        chamber: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        text: str | None = None,
        joint: bool = False,
        hours: int = 24,
        threshold: str | None = None,
        notify: bool = False,
    ):
        act = action.value
        reg = self.federal_registry
        items = ensure_bills_schema(reg)["items"]

        # ---------- INTRODUCE ----------
        if act == "introduce":
            if not chamber or not title or not text:
                return await interaction.response.send_message("Provide chamber, title, and text to introduce.", ephemeral=True)
            ch = chamber.value
            if not is_in_chamber(interaction.user, ch):
                return await interaction.response.send_message(f"Only {ch} members may introduce in the {ch}.", ephemeral=True)

            # number & create bill
            bill_no = next_bill_id(reg, ch)  # uses your existing helper
            struct = parse_bill_structure(text)
            has_sections = any(t.get("sections") for t in struct.get("titles", []))

            bill = {
                "id": bill_no,
                "chamber": ch,
                "type": "bill",
                "joint": joint,
                "title": title,
                "summary": summary or "",
                "text": text,
                "structure": struct if has_sections else None,
                "amendments": {},
                "status": "INTRODUCED",
                "introduced_by": interaction.user.id,
                "introduced_at": discord.utils.utcnow().isoformat(),
            }
            items[bill_no] = bill
            mark_history(bill, f"Introduced in {ch}", interaction.user.id)
            save_federal_registry(reg)
            chan = interaction.client.get_channel(chamber_channel_id(ch))
            if chan:
                intro_embed = discord.Embed(
                    title="Bill Introduced",
                    description=f"**{bill_no}** — {title}",
                    color=discord.Color.blurple()
                )
                intro_embed.add_field(name="Chamber", value=ch, inline=True)
                intro_embed.add_field(name="Sponsor", value=f"<@{interaction.user.id}>", inline=True)
                if summary:
                    intro_embed.add_field(name="Summary", value=summary[:1024], inline=False)
                await chan.send(embed=intro_embed)

            # Operator ack (public, not ephemeral)
            await interaction.response.send_message(f"✅ Introduced **{bill_no}** — {title} in the **{ch}**.", ephemeral=False)
            return
        
        # For all other actions we need an existing bill
        if not bill_id or bill_id not in items:
            return await interaction.response.send_message("Bill not found. (Provide bill_id.)", ephemeral=True)
        b = items[bill_id]

        # ---------- OPEN VOTE ----------
        if act == "open_vote":
            if not is_in_chamber(interaction.user, b["chamber"]):
                return await interaction.response.send_message(f"Only {b['chamber']} may open a vote on this bill.", ephemeral=True)
            if b.get("vote", {}).get("message_id"):
                return await interaction.response.send_message("A vote is already open.", ephemeral=True)

            # where to post poll
            chan = interaction.client.get_channel(chamber_channel_id(b["chamber"]))
            if not chan:
                return await interaction.response.send_message("Chamber channel not found.", ephemeral=True)

            # poll
            q = _poll_question_for(b)
            p = discord.Poll(
                question=q,
                duration=datetime.timedelta(hours=hours),
                allow_multiselect=False
            )
            p.add_answer(text="Yea", emoji="✅")
            p.add_answer(text="Nay", emoji="❌")
            p.add_answer(text="Present", emoji="➖")

            msg = await chan.send(content="Roll call is open:", poll=p)

            # quorum set-up (reuse your helper)
            eligible = await resolve_eligible_members(interaction.guild, chan, b["chamber"])
            quorum = quorum_required(len(eligible))

            b.setdefault("vote", {})
            b["vote"].update({
                "message_id": msg.id,
                "channel_id": chan.id,
                "opened_at": discord.utils.utcnow().isoformat(),
                "opened_by": interaction.user.id,
                "threshold": (threshold.value if threshold else "simple"),
                "hours": hours,
                "eligible_count": len(eligible),
                "quorum_required": quorum,
            })
            b["status"] = "FLOOR VOTE OPEN"
            save_federal_registry(reg)

            # optional DMs
            if notify:
                link = msg.jump_url
                ok = fail = 0
                for m in eligible:
                    try:
                        await m.send(f"A vote has opened in the {b['chamber']}.\n\n{link}")
                        ok += 1
                        await asyncio.sleep(0.5)
                    except Exception:
                        fail += 1
                await interaction.response.send_message(f"✅ Vote opened; quorum {quorum}. DMs sent {ok}, failed {fail}.", ephemeral=True)

            announce = discord.Embed(
                title="Floor Vote Opened",
                description=f"**{b['id']}** — {b.get('title','')}",
                color=discord.Color.gold()
            )
            announce.add_field(name="Chamber", value=b["chamber"], inline=True)
            announce.add_field(name="Duration", value=f"{hours}h", inline=True)
            announce.add_field(name="Threshold", value=b['vote'].get('threshold','simple'), inline=True)
            announce.add_field(name="Poll Link", value=f"[Jump to poll]({msg.jump_url})", inline=False)
            await chan.send(embed=announce)

            # Operator ack (public)
            await interaction.response.send_message(
                f"✅ Vote opened for **{b['id']}** in **{b['chamber']}**. Link: {msg.jump_url}",
                ephemeral=False
            )
            return
        # ---------- CLOSE VOTE ----------
        if act == "close_vote":
            v = b.get("vote")
            if not v or not v.get("message_id"):
                return await interaction.response.send_message("No open/recorded vote for this bill.", ephemeral=True)

            chan = interaction.client.get_channel(v["channel_id"])
            msg = await chan.fetch_message(v["message_id"])
            try:
                await msg.end_poll()
            except Exception:
                pass
            # re-fetch final
            try:
                msg = await chan.fetch_message(v["message_id"])
            except Exception:
                pass

            yea, nay, present, total = _tally_from_message(msg)
            quorum = v.get("quorum_required", 0)
            eligible = v.get("eligible_count", 0)

            if total < quorum:
                outcome = "NO_QUORUM"
                b["status"] = "FAILED"
            else:
                th = v.get("threshold", "simple")
                outcome = _decide(yea, nay, present, th)
                b["status"] = "PASSED" if outcome == "PASSED" else "FAILED"

            v.update({
                "closed_at": discord.utils.utcnow().isoformat(),
                "yea": yea, "nay": nay, "present": present, "total": total,
                "outcome": outcome,
            })
            save_federal_registry(reg)

            # if this was a 2/3 override vote on a vetoed bill, set flags (optional)
            if b.get("status") in {"PASSED","FAILED"} and b.get("prior_status") == "VETOED" or (b.get("status") == "VETOED"):
                if v.get("threshold") == "two_thirds":
                    ran = "Senate" if chamber_role_id("Senate") in {r.id for r in interaction.user.roles} else "House"
                    b["override_senate" if ran == "Senate" else "override_house"] = (outcome == "PASSED")
                    if b.get("override_senate") and b.get("override_house"):
                        b["status"] = "ENACTED"
                        b["enacted_at"] = discord.utils.utcnow().isoformat()
                        mark_history(b, "Veto overridden; enacted", interaction.user.id)
                    save_federal_registry(reg)

            color = discord.Color.green() if outcome == "PASSED" else discord.Color.red()
            embed = discord.Embed(
                title=f"{b['id']} — Vote {outcome}",
                description=b.get("title",""),
                color=color
            )
            embed.add_field(name="Yea", value=str(yea))
            embed.add_field(name="Nay", value=str(nay))
            embed.add_field(name="Present", value=str(present))
            embed.add_field(name="Ballots cast", value=str(total))
            embed.set_footer(text=f"Eligible: {eligible} · Quorum: {quorum} · Threshold: {v.get('threshold','simple')}")
            await chan.send(embed=embed)

            return await interaction.response.send_message(f"✅ Tallied vote for **{b['id']}** → {outcome}.", ephemeral=True)

        # ---------- SEND TO OTHER ----------
        if act == "send_other":
            if b.get("status") != "PASSED":
                return await interaction.response.send_message("Bill must be PASSED by its chamber before transmission.", ephemeral=True)
            if not is_in_chamber(interaction.user, b["chamber"]):
                return await interaction.response.send_message(f"Only {b['chamber']} may transmit.", ephemeral=True)
            b["sent_to"] = other_chamber(b["chamber"])
            b["status"] = "SENT_TO_OTHER"
            mark_history(b, f"Sent to {b['sent_to']}", interaction.user.id)
            save_federal_registry(reg)
            # PUBLIC NOTE in originating chamber
            orig_chan = interaction.client.get_channel(chamber_channel_id(b["chamber"]))
            if orig_chan:
                e = discord.Embed(
                    title="Transmitted to Other Chamber",
                    description=f"**{b['id']}** — {b.get('title','')}",
                    color=discord.Color.blue()
                )
                e.add_field(name="From", value=b["chamber"], inline=True)
                e.add_field(name="To", value=b["sent_to"], inline=True)
                await orig_chan.send(embed=e)

            await interaction.response.send_message(
                f"📨 Sent **{b['id']}** to the **{b['sent_to']}**.",
                ephemeral=False
            )
            return

        # ---------- RECEIVE ----------
        if act == "receive_other":
            if b.get("status") != "SENT_TO_OTHER":
                return await interaction.response.send_message("This bill is not awaiting receipt.", ephemeral=True)
            recv = b.get("sent_to")
            if not is_in_chamber(interaction.user, recv):
                return await interaction.response.send_message(f"Only {recv} may receive this bill.", ephemeral=True)
            b["received_by"] = recv
            b["status"] = "RECEIVED_OTHER"
            mark_history(b, f"Received by {recv}", interaction.user.id)
            save_federal_registry(reg)
            # PUBLIC NOTE in receiving chamber
            recv_chan = interaction.client.get_channel(chamber_channel_id(recv))
            if recv_chan:
                e = discord.Embed(
                    title="Received from Other Chamber",
                    description=f"**{b['id']}** — {b.get('title','')}",
                    color=discord.Color.blue()
                )
                e.add_field(name="Received by", value=recv, inline=True)
                await recv_chan.send(embed=e)

            await interaction.response.send_message(
                f"📥 **{b['id']}** received by the **{recv}**.",
                ephemeral=False
            )
            return


        # ---------- MARK SECOND CHAMBER PASSED ----------
        if act == "mark_second_passed":
            if b.get("status") not in {"RECEIVED_OTHER","PASSED"}:
                return await interaction.response.send_message("Bill must be received/passed in the second chamber.", ephemeral=True)
            # Require a member of the receiving chamber or leadership to mark this
            recv = b.get("received_by") or b.get("sent_to")
            if not (is_in_chamber(interaction.user, recv) or is_leadership(interaction.user)):
                return await interaction.response.send_message("Only the receiving chamber or leadership may mark passage.", ephemeral=True)
            b["received_by_passed"] = True
            # normalize status back to PASSED (both chambers) so enroll can run
            b["status"] = "PASSED"
            mark_history(b, f"{recv} passed", interaction.user.id)
            save_federal_registry(reg)
            # PUBLIC NOTE in receiving chamber
            note_chan = interaction.client.get_channel(chamber_channel_id(recv))
            if note_chan:
                e = discord.Embed(
                    title="Second Chamber Passage Recorded",
                    description=f"**{b['id']}** — {b.get('title','')}",
                    color=discord.Color.green()
                )
                e.add_field(name="Chamber", value=recv, inline=True)
                await note_chan.send(embed=e)

            await interaction.response.send_message(
                f"✅ Recorded second-chamber passage for **{b['id']}**.",
                ephemeral=False
            )
            return


        # ---------- ENROLL ----------
        if act == "enroll":
            if not (b.get("status") == "PASSED" and b.get("received_by_passed")):
                return await interaction.response.send_message("Bill must be passed by both chambers before enrollment.", ephemeral=True)
            if not is_leadership(interaction.user):
                return await interaction.response.send_message("Only leadership may enroll.", ephemeral=True)
            b["enrolled_text"] = b.get("text")
            b["status"] = "ENROLLED"
            mark_history(b, "Enrolled", interaction.user.id)
            save_federal_registry(reg)
            # PUBLIC NOTE (post to both chambers, since text is now frozen)
            for ch_name in {b["chamber"], b.get("received_by") or b.get("sent_to")}:
                if not ch_name: 
                    continue
                chx = interaction.client.get_channel(chamber_channel_id(ch_name))
                if chx:
                    e = discord.Embed(
                        title="Enrolled (Text Frozen)",
                        description=f"**{b['id']}** — {b.get('title','')}",
                        color=discord.Color.purple()
                    )
                    await chx.send(embed=e)

            await interaction.response.send_message(f"📝 **{b['id']}** enrolled.", ephemeral=False)
            return


        # ---------- PRESENT ----------
        if act == "present":
            if b.get("status") != "ENROLLED":
                return await interaction.response.send_message("Bill must be ENROLLED first.", ephemeral=True)
            if not is_leadership(interaction.user):
                return await interaction.response.send_message("Only leadership may present.", ephemeral=True)
            b["status"] = "PRESENTED"
            b["presented_at"] = discord.utils.utcnow().isoformat()
            mark_history(b, "Presented to President", interaction.user.id)
            save_federal_registry(reg)
            # PUBLIC NOTE in White House channel
            wh = interaction.client.get_channel(SPIDEY_HOUSE)
            if wh:
                e = discord.Embed(
                    title="Presented to the President",
                    description=f"**{b['id']}** — {b.get('title','')}",
                    color=discord.Color.dark_gold()
                )
                await wh.send(embed=e)

            await interaction.response.send_message(f"📜 **{b['id']}** presented to the President.", ephemeral=False)
            return


        # ---------- STATUS ----------
        if act == "status":
            embed = discord.Embed(
                title=f"{b['id']} — {b.get('title','')}",
                description=b.get("summary",""),
                color=discord.Color.blurple()
            )
            embed.add_field(name="Status", value=b.get("status","?"), inline=True)
            embed.add_field(name="Chamber", value=b.get("chamber","?"), inline=True)
            if b.get("sent_to"): embed.add_field(name="Sent to", value=b["sent_to"], inline=True)
            if b.get("received_by"): embed.add_field(name="Received by", value=b["received_by"], inline=True)
            if b.get("received_by_passed"): embed.add_field(name="Second chamber", value="PASSED", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # assumes you have PRESIDENT role id
    @executive.command(name="bill_sign", description="Sign a presented bill into law")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(bill_id=bill_id_autocomplete)
    @app_commands.describe(
        reasons="Optional message from the President",
        codify="If true, instruct the Registry to codify immediately"
    )
    async def bill_sign(self, interaction: discord.Interaction, bill_id: str, reasons: str | None = None, codify: bool = False):
        reg = self.federal_registry
        b = reg.get("bills", {}).get("items", {}).get(bill_id)
        if not b or b.get("status") != "PRESENTED":
            return await interaction.response.send_message("Bill must be PRESENTED.", ephemeral=True)

        b["status"] = "ENACTED"
        b["enacted_at"] = discord.utils.utcnow().isoformat()
        mark_history(b, "Signed into law", interaction.user.id)
        save_federal_registry(reg)

        # PUBLIC PROCLAMATION in SPIDEY_HOUSE
        wh = interaction.client.get_channel(SPIDEY_HOUSE)
        if wh:
            date_str = discord.utils.utcnow().strftime("%B %d, %Y")
            chamber_title = (b.get("chamber") or "").title()
            act_title = b.get("title") or "(untitled)"
            msg = (
    f"""{date_str}

    Pursuant to Art. I Sec. 7 of the Constitution, the Executive shall approve or veto all legislative proposals submitted by the two chambers of Congress. The act submitted by the {chamber_title} which has been marked {bill_id} and was titled “{act_title}” shall be signed into law.

    My administration has signed the act into law{f" due to {reasons}" if (reasons and reasons.strip()) else " due to its good faith passage by the joint bodies"}.

    The Federal Registry shall submit this decision into the record{(" and codify it into law" if codify else "")}.

    /s/ spidey simp
    President of the Spidey Republic"""
            )
            await wh.send(msg)

        # Operator ack (public)
        await interaction.response.send_message(f"✅ **{bill_id}** signed into law.", ephemeral=False)


    @executive.command(name="bill_veto", description="Return a presented bill with objections")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(bill_id=bill_id_autocomplete)
    @app_commands.describe(reason="Brief veto message (why the objections?)")
    async def bill_veto(self, interaction: discord.Interaction, bill_id: str, reason: str):
        reg = self.federal_registry
        b = reg.get("bills", {}).get("items", {}).get(bill_id)
        if not b or b.get("status") != "PRESENTED":
            return await interaction.response.send_message("Bill must be PRESENTED.", ephemeral=True)

        b["status"] = "VETOED"
        b["veto"] = {
            "reason": reason,
            "by": interaction.user.id,
            "at": discord.utils.utcnow().isoformat()
        }
        mark_history(b, "Vetoed", interaction.user.id)
        save_federal_registry(reg)

        # PUBLIC PROCLAMATION in SPIDEY_HOUSE
        wh = interaction.client.get_channel(SPIDEY_HOUSE)
        if wh:
            date_str = discord.utils.utcnow().strftime("%B %d, %Y")
            chamber_title = (b.get("chamber") or "").title()
            act_title = b.get("title") or "(untitled)"
            msg = (
    f"""{date_str}

    Pursuant to Art. I Sec. 7 of the Constitution, the Executive shall approve or veto all legislative proposals submitted by the two chambers of Congress. The act submitted by the {chamber_title} which has been marked {bill_id} and was titled “{act_title}” shall be vetoed.

    My administration has vetoed the act due to {reason}.

    The Federal Registry shall submit this decision into the record.

    /s/ spidey simp
    President of the Spidey Republic"""
            )
            await wh.send(msg)

        # Operator ack (public)
        await interaction.response.send_message(f"🚫 **{bill_id}** vetoed.", ephemeral=False)

