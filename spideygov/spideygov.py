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
from datetime import datetime, timezone, timedelta, date
import math
import difflib
from zoneinfo import ZoneInfo
from discord.ext import tasks
import shutil
import time
from pathlib import Path
import io
import tempfile
import xml.etree.ElementTree as ET
import hashlib
import sqlite3

try:
    import docx  # python-docx
except Exception:
    docx = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

UTC = timezone.utc
REGISTRY_SUSPENDED = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FED_REGISTRY_FILE = os.path.join(BASE_DIR, "federal_registry.json")



SENATORS = 1327053499405701142
REPRESENTATIVES = 1327053334036742215
SENATE = 1302330234422562887
HOUSE = 1302330037365772380
SENATE_MAJORITY_LEADER = 1417354264795418664
SPEAKER_OF_THE_HOUSE = 1417354436472344586
SPIDEY_HOUSE = 1302330503399084144
SENATE_VOTING_CHANNEL = 1334289687996796949
STATE_DEPARTMENT_CHANNEL = 1424208056459198495
BOT_DEPARTMENT_CHANNEL = 1423094053247127623

CITIZENSHIP = {
    "commons": 1415927703340716102,
    "gaming": 1415928304757637175,
    "dp": 1415928367730921482,
    "crazy_times": 1415928481505738792,
    "user_themed": 1415928541740142672
}
CITIZENSHIP_IDS = set(CITIZENSHIP.values())

CITIZENSHIP_ROLE = 1302324304712695909
RESIDENTS = 1287978893755547769
WAVING = 1287676691552145529
PENDING_RESIDENT = 1428131256327078009
SEC_OF_STATE = 650814947437182977
RULES = 1287700985275355147
CITIZENSHIP_APPLICANT = 1428142777308549263
PENDING_ALLOWED_CHANNELS = {RULES, WAVING}

CITIZENSHIP_EXAM_LEN = 8           # number of questions per exam
CITIZENSHIP_PASSING  = 80          # percent
CITIZENSHIP_EXAM_COOLDOWN_DAYS = 14

# --- Elections constants (put with your other channel/role IDs) ---
FEC_ROLE_ID = 0                 # (optional) role that can manage recounts; else admins
CLERK_ROLE_ID = 0               # Clerk of the House (for certifications) or leave 0 to allow admins
DEFAULT_ELECTION_HOURS = 24
ELECTIONS_ANNOUNCE_CHANNEL = 1334216429884407808

USC_DB_FILE = os.path.join(BASE_DIR, "usc.sqlite3")

USLM_NS = "http://xml.house.gov/schemas/uslm/1.0"
STRUCT_TAGS = {"subsection", "paragraph", "subparagraph", "clause", "subclause"}

_indent_re = re.compile(r"indent(\d+)")
_cite_re = re.compile(
    r"^\s*(?P<title>\d+)\s*(?:U\.?\s*S\.?\s*C\.?|USC)\s*(?:§+)?\s*(?P<section>[\w\.\-]+)\s*$",
    re.IGNORECASE,
)

def _usc_local(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag

def _usc_norm_ws(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def _usc_fix_heading_brackets(s: str | None) -> str:
    s = _usc_norm_ws(s)
    # Heuristic: some converters omit the leading '[' but keep the trailing ']'
    if s.endswith("]") and not s.startswith("[") and s.count("]") == 1:
        return "[" + s
    return s

def _usc_num_text(num_elem: ET.Element) -> str:
    """
    Prefer visible text, but fall back to @value when text is empty.
    If @value looks like a bare token (a, 1, A, i), wrap it as (token).
    """
    raw = _usc_norm_ws("".join(num_elem.itertext()))
    if raw:
        return raw

    v = _usc_norm_ws(num_elem.get("value"))
    if not v:
        return ""

    # If it's already formatted, leave it.
    if v.startswith("(") or v.startswith("“(") or v.startswith("§"):
        return v

    # Most USLM @value for paragraph markers is bare (a, b, 1, A, i)
    return f"({v})"

def _usc_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _usc_db_connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

SRC_DB_FILE = os.path.join(BASE_DIR, "src.sqlite3")

_SRC_SEC_RE = re.compile(r"^\s*§\s*([\w\.\-]+)\s*$", re.IGNORECASE)

def _src_norm_section_num(s: str) -> str:
    s = (s or "").strip()
    m = _SRC_SEC_RE.match(s)
    if m:
        return m.group(1)
    # allow user to pass "551" directly
    return s.replace("§", "").strip()

def _src_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _src_db_connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def _src_db_init(db_path: str) -> None:
    conn = _src_db_connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS src_titles (
              title_num      INTEGER PRIMARY KEY,
              heading        TEXT NOT NULL,
              imported_at    TEXT,
              source_sha256  TEXT
            );

            CREATE TABLE IF NOT EXISTS src_nodes (
              id         INTEGER PRIMARY KEY AUTOINCREMENT,
              title_num  INTEGER NOT NULL,
              node_type  TEXT NOT NULL,         -- "chapter" (for now)
              num        TEXT,
              heading    TEXT,
              parent_id  INTEGER,
              ord        INTEGER,
              FOREIGN KEY(title_num) REFERENCES src_titles(title_num)
            );

            CREATE TABLE IF NOT EXISTS src_sections (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              title_num   INTEGER NOT NULL,
              node_id     INTEGER,
              section_num TEXT NOT NULL,        -- "551", "552a", etc
              heading     TEXT,                 -- short title
              body_text   TEXT,
              ord         INTEGER,
              UNIQUE(title_num, section_num),
              FOREIGN KEY(title_num) REFERENCES src_titles(title_num),
              FOREIGN KEY(node_id) REFERENCES src_nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_src_nodes_title_ord
              ON src_nodes(title_num, ord);

            CREATE INDEX IF NOT EXISTS idx_src_sections_title_node_ord
              ON src_sections(title_num, node_id, ord);

            -- FTS (matches USC approach; helpful later for search/compare)
            CREATE VIRTUAL TABLE IF NOT EXISTS src_sections_fts
            USING fts5(title_num UNINDEXED, section_num UNINDEXED, heading, body_text);

            CREATE VIRTUAL TABLE IF NOT EXISTS src_nodes_fts
            USING fts5(title_num UNINDEXED, node_type UNINDEXED, num UNINDEXED, heading);
            """
        )
        conn.commit()
    finally:
        conn.close()

def _src_sort_key_chapter(k: str):
    k = str(k)
    return (0, int(k)) if k.isdigit() else (1, k)

def _src_sort_key_section(sec_num: str):
    # order "552", "552a", "552b" sensibly
    s = _src_norm_section_num(sec_num)
    m = re.match(r"^(\d+)(.*)$", s)
    if not m:
        return (1, s)
    return (0, int(m.group(1)), m.group(2) or "")

# --- ANSI helpers (for compare output) ---
ANSI_RESET = "\x1b[0m"
ANSI_DIM   = "\x1b[90m"
ANSI_RED   = "\x1b[31m"
ANSI_GREEN = "\x1b[32m"
ANSI_BOLD  = "\x1b[1m"

def _norm_lines_for_diff(text: str) -> tuple[list[str], list[str]]:
    """
    Returns (norm_lines, orig_lines)
    - norm_lines: lowercased + whitespace-collapsed + stripped (so formatting differences don't create noise)
    - orig_lines: original lines, right-stripped (what we actually print)
    """
    s = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    orig = [ln.rstrip() for ln in s.split("\n")]
    norm = [re.sub(r"\s+", " ", ln.strip()).lower() for ln in orig]
    return norm, orig

def _usc_src_unified_diff_lines(usc_text: str, src_text: str) -> tuple[list[str], dict, float]:
    """
    Builds a unified diff:
      - red lines are USC-only (-)
      - green lines are SRC-only (+)
      - dim lines are shared ( )
    Returns: (diff_lines, stats, similarity_ratio)
    """
    a_norm, a_orig = _norm_lines_for_diff(usc_text)
    b_norm, b_orig = _norm_lines_for_diff(src_text)

    sm = difflib.SequenceMatcher(None, a_norm, b_norm, autojunk=False)

    stats = {"deleted": 0, "inserted": 0, "replaced": 0}
    out: list[str] = []

    # Legend at the top
    out.append(f"{ANSI_BOLD}Legend:{ANSI_RESET} {ANSI_DIM}  match{ANSI_RESET}  {ANSI_RED}- USC-only{ANSI_RESET}  {ANSI_GREEN}+ SRC-only{ANSI_RESET}")
    out.append("")

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j1, j2):
                out.append(f"{ANSI_DIM}  {b_orig[k]}{ANSI_RESET}")
        elif tag == "delete":
            stats["deleted"] += (i2 - i1)
            for k in range(i1, i2):
                out.append(f"{ANSI_RED}- {a_orig[k]}{ANSI_RESET}")
        elif tag == "insert":
            stats["inserted"] += (j2 - j1)
            for k in range(j1, j2):
                out.append(f"{ANSI_GREEN}+ {b_orig[k]}{ANSI_RESET}")
        elif tag == "replace":
            stats["replaced"] += 1
            for k in range(i1, i2):
                out.append(f"{ANSI_RED}- {a_orig[k]}{ANSI_RESET}")
            for k in range(j1, j2):
                out.append(f"{ANSI_GREEN}+ {b_orig[k]}{ANSI_RESET}")

    return out, stats, sm.ratio()

def _src_import_json_bytes(db_path: str, json_bytes: bytes, force: bool = False) -> dict:
    """
    Expects your current src.json structure:
      {
        "5": { "description": "...", "chapters": { "5": { "description": "...", "sections": {...} } } },
        ...
      }
    Stores titles / chapters / sections (no notes).
    """
    _src_db_init(db_path)
    sha = _src_sha256(json_bytes)

    data = json.loads(json_bytes.decode("utf-8"))
    if not isinstance(data, dict) or not all(str(k).isdigit() for k in data.keys()):
        raise ValueError("SRC import expects a JSON object keyed by title number strings (e.g., '5', '28', etc.).")

    conn = _src_db_connect(db_path)
    cur = conn.cursor()

    imported_titles = 0
    total_chapters = 0
    total_sections = 0

    now_iso = discord.utils.utcnow().isoformat()

    try:
        for title_key in sorted(data.keys(), key=lambda x: int(x)):
            title_num = int(title_key)
            tval = data[title_key] or {}
            title_heading = (tval.get("description") or f"Title {title_num}").strip()

            # dedupe: if same sha and not force, skip
            row = cur.execute(
                "SELECT source_sha256 FROM src_titles WHERE title_num=?",
                (title_num,),
            ).fetchone()
            if row and row["source_sha256"] == sha and not force:
                continue

            # replace title contents
            cur.execute("DELETE FROM src_sections_fts WHERE title_num=?", (title_num,))
            cur.execute("DELETE FROM src_sections WHERE title_num=?", (title_num,))
            cur.execute("DELETE FROM src_nodes WHERE title_num=?", (title_num,))
            cur.execute("DELETE FROM src_nodes_fts WHERE title_num=?", (title_num,))

            cur.execute(
                """
                INSERT INTO src_titles(title_num, heading, imported_at, source_sha256)
                VALUES(?,?,?,?)
                ON CONFLICT(title_num) DO UPDATE SET
                  heading=excluded.heading,
                  imported_at=excluded.imported_at,
                  source_sha256=excluded.source_sha256
                """,
                (title_num, title_heading, now_iso, sha),
            )

            chapters = tval.get("chapters") or {}
            if not isinstance(chapters, dict):
                chapters = {}

            chap_ord = 0
            sec_ord = 0

            for chap_key in sorted(chapters.keys(), key=_src_sort_key_chapter):
                chap_ord += 1
                cval = chapters.get(chap_key) or {}
                chap_heading = (cval.get("description") or "").strip()

                cur.execute(
                    """
                    INSERT INTO src_nodes(title_num, node_type, num, heading, parent_id, ord)
                    VALUES(?, 'chapter', ?, ?, NULL, ?)
                    """,
                    (title_num, str(chap_key), chap_heading, chap_ord),
                )
                cur.execute(
                    "INSERT INTO src_nodes_fts(rowid, title_num, node_type, num, heading) VALUES(?,?,?,?,?)",
                    (node_id, title_num, "chapter", str(chap_key), chap_heading or "")
                )
                node_id = cur.lastrowid
                total_chapters += 1

                sections = cval.get("sections") or {}
                if not isinstance(sections, dict):
                    sections = {}

                for sec_key in sorted(sections.keys(), key=_src_sort_key_section):
                    sval = sections.get(sec_key) or {}
                    sec_num = _src_norm_section_num(sval.get("number") or sec_key)
                    sec_head = (sval.get("short") or "").strip()
                    sec_text = _src_pretty_indent((sval.get("text") or "").rstrip())

                    sec_ord += 1
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO src_sections(title_num, node_id, section_num, heading, body_text, ord)
                        VALUES(?,?,?,?,?,?)
                        """,
                        (title_num, node_id, sec_num, sec_head, sec_text, sec_ord),
                    )
                    sid = cur.lastrowid
                    cur.execute(
                        "INSERT INTO src_sections_fts(rowid, title_num, section_num, heading, body_text) VALUES(?,?,?,?,?)",
                        (sid, title_num, sec_num, sec_head, sec_text),
                    )
                    total_sections += 1

            imported_titles += 1

        conn.commit()

        return {
            "titles_processed": len(data),
            "titles_imported_or_updated": imported_titles,
            "chapters": total_chapters,
            "sections": total_sections,
            "sha256": sha,
        }
    finally:
        conn.close()

def _src_db_search(db_path: str, query: str, title: int | None, limit_sections: int = 25, limit_chapters: int = 10):
    conn = _src_db_connect(db_path)
    try:
        q = _usc_make_fts_query(query)  # reuse your existing helper
        if not q:
            return {"titles": {}, "counts": {"sections": 0, "chapters": 0}}

        # Sections (heading weighted higher than body)
        sec_sql = """
        SELECT
          s.id,
          s.title_num,
          s.section_num,
          COALESCE(s.heading,'') AS heading,
          COALESCE(n.num,'') AS chapter_num,
          COALESCE(n.heading,'') AS chapter_heading,
          bm25(src_sections_fts, 0.0, 0.0, 6.0, 1.0) AS rank,
          snippet(src_sections_fts, 2, (char(27) || '[1;33m'), (char(27) || '[0m'), '…', 12) AS hsnip,
          snippet(src_sections_fts, 3, (char(27) || '[1;33m'), (char(27) || '[0m'), '…', 24) AS bsnip
        FROM src_sections_fts
        JOIN src_sections s ON s.id = src_sections_fts.rowid
        LEFT JOIN src_nodes n ON n.id = s.node_id
        WHERE src_sections_fts MATCH ?
        """
        params = [q]
        if title is not None:
            sec_sql += " AND s.title_num = ?"
            params.append(int(title))
        sec_sql += " ORDER BY rank LIMIT ?"
        params.append(int(limit_sections))
        sec_rows = conn.execute(sec_sql, params).fetchall()

        # Chapter headings
        ch_sql = """
        SELECT
          n.id,
          n.title_num,
          COALESCE(n.num,'') AS num,
          COALESCE(n.heading,'') AS heading,
          bm25(src_nodes_fts, 0.0, 0.0, 0.0, 1.0) AS rank,
          snippet(src_nodes_fts, 3, (char(27) || '[1;33m'), (char(27) || '[0m'), '…', 16) AS snip
        FROM src_nodes_fts
        JOIN src_nodes n ON n.id = src_nodes_fts.rowid
        WHERE src_nodes_fts MATCH ?
          AND n.node_type='chapter'
        """
        params = [q]
        if title is not None:
            ch_sql += " AND n.title_num = ?"
            params.append(int(title))
        ch_sql += " ORDER BY rank LIMIT ?"
        params.append(int(limit_chapters))
        ch_rows = conn.execute(ch_sql, params).fetchall()

        title_nums = sorted({r["title_num"] for r in sec_rows} | {r["title_num"] for r in ch_rows})
        title_map = {}
        if title_nums:
            qmarks = ",".join("?" for _ in title_nums)
            for r in conn.execute(f"SELECT title_num, heading FROM src_titles WHERE title_num IN ({qmarks})", title_nums):
                title_map[int(r["title_num"])] = r["heading"]

        grouped = {tn: {"title_heading": title_map.get(tn, ""), "chapters": [], "sections": []} for tn in title_nums}

        for r in ch_rows:
            grouped[int(r["title_num"])]["chapters"].append({
                "num": r["num"],
                "snip": r["snip"] or r["heading"],
            })

        for r in sec_rows:
            grouped[int(r["title_num"])]["sections"].append({
                "chapter_num": r["chapter_num"],
                "chapter_heading": r["chapter_heading"],
                "section_num": r["section_num"],
                "hsnip": r["hsnip"] or r["heading"],
                "bsnip": r["bsnip"] or "",
            })

        return {"titles": grouped, "counts": {"sections": len(sec_rows), "chapters": len(ch_rows)}}
    finally:
        conn.close()

def _src_db_reindex_fts(db_path: str) -> dict:
    conn = _src_db_connect(db_path)
    try:
        conn.execute("DELETE FROM src_nodes_fts;")
        conn.execute("DELETE FROM src_sections_fts;")

        conn.execute("""
            INSERT INTO src_nodes_fts(rowid, title_num, node_type, num, heading)
            SELECT id, title_num, node_type, COALESCE(num,''), COALESCE(heading,'')
            FROM src_nodes
        """)

        conn.execute("""
            INSERT INTO src_sections_fts(rowid, title_num, section_num, heading, body_text)
            SELECT id, title_num, section_num, COALESCE(heading,''), COALESCE(body_text,'')
            FROM src_sections
        """)

        conn.commit()
        return {
            "nodes": int(conn.execute("SELECT COUNT(*) AS n FROM src_nodes_fts").fetchone()["n"]),
            "sections": int(conn.execute("SELECT COUNT(*) AS n FROM src_sections_fts").fetchone()["n"]),
        }
    finally:
        conn.close()

_SRC_MARKER_RE = re.compile(r"^\s*\(([^)]+)\)\s*(.*)$")
_ROMAN_LOWER_RE = re.compile(r"^[ivx]+$")

def _src_marker_level(tok: str) -> int | None:
    """
    Map common statutory markers to indentation levels:
      (a) -> 0
      (1) -> 1
      (A) -> 2
      (i) -> 3
    """
    t = tok.strip()

    if not t:
        return None

    if t.isdigit():
        return 1

    if t.isalpha():
        # roman numerals
        low = t.lower()
        if all(ch in _ROMAN_CHARS for ch in low):
            return 3

        # letters
        if t.islower():
            return 0
        if t.isupper():
            return 2

    return None

def _src_pretty_indent(text: str) -> str:
    """
    Indent SRC text based on leading markers:
      (a) -> level 0
      (1) -> level 1
      (A) -> level 2
      (i)/(ii)/... -> level 3 ONLY if we're currently under an uppercase marker (A/B/C...)
    This avoids C/D being treated as roman numerals.
    """
    if not text:
        return ""

    # stack[level] = last token seen at that level (we only need presence)
    stack: list[str] = []

    out_lines = []
    for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        m = _SRC_MARKER_RE.match(ln)
        if not m:
            out_lines.append(ln.rstrip())
            continue

        tok_raw, rest = m.group(1).strip(), (m.group(2) or "").strip()

        lvl = None

        if tok_raw.isdigit():
            lvl = 1

        elif tok_raw.isalpha() and len(tok_raw) == 1 and tok_raw.islower():
            # (a) style
            lvl = 0

        elif tok_raw.isalpha() and len(tok_raw) == 1 and tok_raw.isupper():
            # (A) style — NEVER roman
            lvl = 2

        elif tok_raw.isalpha() and tok_raw.islower() and _ROMAN_LOWER_RE.match(tok_raw):
            # roman-like (i), (ii), (iv), etc.
            # Treat as roman only if we are inside an uppercase-letter block (level 2 exists).
            inside_upper = len(stack) > 2 and bool(stack[2])
            lvl = 3 if inside_upper else 0

        if lvl is None:
            out_lines.append(ln.rstrip())
            continue

        # maintain stack to reflect current nesting
        while len(stack) <= lvl:
            stack.append("")
        stack[lvl] = tok_raw
        # clear deeper levels
        for i in range(lvl + 1, len(stack)):
            stack[i] = ""

        indent = "    " * lvl
        out_lines.append(f"{indent}({tok_raw})" + (f" {rest}" if rest else ""))

    return "\n".join(out_lines).rstrip()

def _src_db_list_titles(db_path: str) -> list[sqlite3.Row]:
    _src_db_init(db_path)
    conn = _src_db_connect(db_path)
    try:
        return conn.execute(
            "SELECT title_num, heading, imported_at FROM src_titles ORDER BY title_num"
        ).fetchall()
    finally:
        conn.close()

def _src_db_get_chapters(db_path: str, title_num: int) -> list[sqlite3.Row]:
    conn = _src_db_connect(db_path)
    try:
        return conn.execute(
            """
            SELECT id, num, heading, ord
            FROM src_nodes
            WHERE title_num=? AND node_type='chapter'
            ORDER BY ord
            """,
            (int(title_num),),
        ).fetchall()
    finally:
        conn.close()

def _src_db_get_chapter_id(db_path: str, title_num: int, chapter_num: str) -> int | None:
    conn = _src_db_connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT id FROM src_nodes
            WHERE title_num=? AND node_type='chapter' AND num=?
            LIMIT 1
            """,
            (int(title_num), str(chapter_num)),
        ).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()

def _src_db_get_sections_in_chapter(db_path: str, title_num: int, chapter_id: int) -> list[sqlite3.Row]:
    conn = _src_db_connect(db_path)
    try:
        return conn.execute(
            """
            SELECT section_num, heading
            FROM src_sections
            WHERE title_num=? AND node_id=?
            ORDER BY ord
            """,
            (int(title_num), int(chapter_id)),
        ).fetchall()
    finally:
        conn.close()

def _src_db_get_section(db_path: str, title_num: int, section_num: str) -> sqlite3.Row | None:
    conn = _src_db_connect(db_path)
    try:
        return conn.execute(
            """
            SELECT s.section_num, s.heading, s.body_text,
                   n.num AS chapter_num, n.heading AS chapter_heading
            FROM src_sections s
            LEFT JOIN src_nodes n ON n.id = s.node_id
            WHERE s.title_num=? AND s.section_num=?
            LIMIT 1
            """,
            (int(title_num), _src_norm_section_num(section_num)),
        ).fetchone()
    finally:
        conn.close()

def _chunk_lines(lines: list[str], limit: int = 1700) -> list[str]:
    pages, cur, cur_len = [], [], 0
    for ln in lines:
        add = len(ln) + 1
        if cur and cur_len + add > limit:
            pages.append("\n".join(cur))
            cur, cur_len = [ln], add
        else:
            cur.append(ln)
            cur_len += add
    if cur:
        pages.append("\n".join(cur))
    return pages or ["(none)"]

_FTS_ADVANCED = re.compile(r'["*():]|\\b(NEAR|OR|AND|NOT)\\b', re.IGNORECASE)

def _usc_make_fts_query(q: str) -> str:
    q = (q or "").strip()
    if not q:
        return ""
    # If user is doing advanced FTS syntax, don’t touch it
    if _FTS_ADVANCED.search(q):
        return q
    # Default: all words must appear (good “Lexis-ish” behavior)
    toks = [t for t in re.split(r"\s+", q) if t]
    if len(toks) == 1:
        return toks[0]
    return " AND ".join(toks)

def _usc_fmt_dt(s: str | None) -> str:
    if not s:
        return "Unknown"
    s = s.strip()

    # Handle plain date
    try:
        d = date.fromisoformat(s)
        return d.strftime("%b %-d, %Y") if hasattr(d, "strftime") else str(d)
    except Exception:
        pass

    # Handle ISO datetime (including trailing Z)
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
    except Exception:
        return s  # fallback: show raw if parsing fails

    return dt.strftime("%b %-d, %Y")

def _usc_db_init(db_path: str) -> None:
    conn = _usc_db_connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS usc_titles (
              title_num      INTEGER PRIMARY KEY,
              heading        TEXT NOT NULL,
              created_at     TEXT,
              imported_at    TEXT,
              source_sha256  TEXT
            );

            CREATE TABLE IF NOT EXISTS usc_nodes (
              id         INTEGER PRIMARY KEY AUTOINCREMENT,
              title_num  INTEGER NOT NULL,
              node_type  TEXT NOT NULL,
              num        TEXT,
              heading    TEXT,
              identifier TEXT,
              parent_id  INTEGER,
              ord        INTEGER,
              FOREIGN KEY(title_num) REFERENCES usc_titles(title_num)
            );

            CREATE TABLE IF NOT EXISTS usc_sections (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              title_num   INTEGER NOT NULL,
              node_id     INTEGER,
              section_num TEXT NOT NULL,
              heading     TEXT,
              identifier  TEXT,
              body_text   TEXT,
              ord         INTEGER,
              UNIQUE(title_num, section_num),
              FOREIGN KEY(title_num) REFERENCES usc_titles(title_num),
              FOREIGN KEY(node_id) REFERENCES usc_nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_usc_nodes_title_ord
              ON usc_nodes(title_num, ord);

            CREATE INDEX IF NOT EXISTS idx_usc_sections_title_node_ord
              ON usc_sections(title_num, node_id, ord);

            -- simple FTS for later (not required for the basic commands, but cheap to add now)
            CREATE VIRTUAL TABLE IF NOT EXISTS usc_sections_fts
            USING fts5(title_num UNINDEXED, section_num UNINDEXED, heading, body_text);

            CREATE VIRTUAL TABLE IF NOT EXISTS usc_nodes_fts
            USING fts5(title_num UNINDEXED, node_type UNINDEXED, num UNINDEXED, heading);
            """
        )
        conn.commit()
    finally:
        conn.close()

def _usc_render_struct(elem: ET.Element, depth: int = 0) -> list[str]:
    """
    Render subsection/paragraph/etc. recursively with indentation.
    """
    lines: list[str] = []

    num_text = ""
    heading_text = ""
    content_text = ""

    for ch in list(elem):
        lt = _usc_local(ch.tag)

        if lt == "num" and not num_text:
            num_text = _usc_num_text(ch)

        elif lt == "heading" and not heading_text:
            heading_text = _usc_norm_ws("".join(ch.itertext()))
            heading_text = _usc_fix_heading_brackets(heading_text)

        elif lt in {"content", "chapeau", "text"} and not content_text:
            content_text = _usc_norm_ws("".join(ch.itertext()))

    # Build the line for this node
    parts = []
    if num_text:
        parts.append(num_text)
    if heading_text:
        parts.append(heading_text)
    if content_text:
        parts.append(content_text)

    head = " ".join([p for p in parts if p])
    if head:
        lines.append(("    " * depth) + head)

    # Recurse into children
    for ch in list(elem):
        if _usc_local(ch.tag) in STRUCT_TAGS:
            lines.extend(_usc_render_struct(ch, depth + 1))

    return lines

def _usc_render_section_body(section_elem: ET.Element) -> str:
    """
    Render statute text only (skip notes/sourceCredit).
    Handles:
      - <content><p class="indent1"> ... </p></content>
      - direct <subsection>/<paragraph>/... trees
    """
    lines: list[str] = []

    # 1) section-level <content> (common)
    for ch in list(section_elem):
        lt = _usc_local(ch.tag)
        if lt != "content":
            continue

        ps = [c for c in list(ch) if _usc_local(c.tag) == "p"]
        if ps:
            for p in ps:
                cls = p.get("class") or ""
                m = _indent_re.search(cls)
                indent = int(m.group(1)) if m else 0
                txt = _usc_norm_ws("".join(p.itertext()))
                if txt:
                    lines.append(("    " * indent) + txt)
        else:
            txt = _usc_norm_ws("".join(ch.itertext()))
            if txt:
                lines.append(txt)

    # 2) structural children (subsections, etc.)
    for ch in list(section_elem):
        if _usc_local(ch.tag) in STRUCT_TAGS:
            lines.extend(_usc_render_struct(ch, 0))

    return "\n".join(lines).strip()

_USC_SEC_ID_RE = re.compile(r"^/us/usc/t(?P<title>\d+)/s(?P<section>[^/]+)$")

def _usc_is_real_usc_section(identifier: str | None, title_num: int | None) -> bool:
    if not identifier or not title_num:
        return False
    m = _USC_SEC_ID_RE.match(identifier)
    return bool(m and int(m.group("title")) == int(title_num))

_HEADING_NOISE_RE = re.compile(r"\s+\d+\s+So in original\..*$", re.IGNORECASE)

def _usc_clean_section_heading(h: str | None) -> str:
    h = _usc_fix_heading_brackets(_usc_norm_ws(h))
    # remove “11 So in original...” style junk
    h = re.sub(_HEADING_NOISE_RE, "", h).strip()
    # remove trailing lone footnote numbers (e.g., "Judicial Review 1")
    h = re.sub(r"\s+\d+$", "", h).strip()
    return h

def _usc_import_xml_bytes(db_path: str, xml_bytes: bytes, force: bool = False) -> dict:
    """
    Parse one Title XML (USLM), store:
      - title number
      - title heading
      - created date (meta)
      - chapters (as nodes)
      - sections (statute text only; no notes)
    Returns a summary dict.
    """
    _usc_db_init(db_path)
    sha = _usc_sha256(xml_bytes)

    conn = _usc_db_connect(db_path)
    cur = conn.cursor()

    title_num: int | None = None
    title_heading: str | None = None
    created_at: str | None = None
    prepared = False
    updated_existing = False

    chapter_ord = 0
    section_ord = 0

    chapter_stack: list[dict] = []

    def prepare_if_ready() -> None:
        nonlocal prepared, updated_existing
        if prepared:
            return
        if title_num is None or not title_heading:
            return

        row = cur.execute(
            "SELECT title_num, heading, created_at, imported_at, source_sha256 FROM usc_titles WHERE title_num=?",
            (title_num,),
        ).fetchone()

        if row and (row["source_sha256"] == sha) and not force:
            raise StopIteration

        if row:
            # replace existing title content
            updated_existing = True
            cur.execute("DELETE FROM usc_sections_fts WHERE title_num=?", (title_num,))
            cur.execute("DELETE FROM usc_sections WHERE title_num=?", (title_num,))
            cur.execute("DELETE FROM usc_nodes WHERE title_num=?", (title_num,))

        cur.execute(
            """
            INSERT INTO usc_titles(title_num, heading, created_at, imported_at, source_sha256)
            VALUES(?,?,?,?,?)
            ON CONFLICT(title_num) DO UPDATE SET
              heading=excluded.heading,
              created_at=excluded.created_at,
              imported_at=excluded.imported_at,
              source_sha256=excluded.source_sha256
            """,
            (
                title_num,
                title_heading,
                created_at,
                discord.utils.utcnow().isoformat(),
                sha,
            ),
        )
        prepared = True

    try:
        it = ET.iterparse(io.BytesIO(xml_bytes), events=("start", "end"))
        stack: list[str] = []

        for ev, el in it:
            t = _usc_local(el.tag)

            if ev == "start":
                stack.append(t)
                if t == "chapter":
                    chapter_ord += 1
                    parent_ctx = chapter_stack[-1] if chapter_stack else None
                    chapter_stack.append({
                        "identifier": el.get("identifier"),
                        "num": None,
                        "heading": None,
                        "ord": chapter_ord,
                        "node_id": None,
                        "_inserted": False,
                        "parent_ctx": parent_ctx,
                    })

            else:
                parent = stack[-2] if len(stack) >= 2 else None

                # meta/title basics
                if t == "docNumber" and parent == "meta" and title_num is None:
                    try:
                        title_num = int(_usc_norm_ws(el.text))
                    except Exception:
                        title_num = None

                if t == "created" and parent == "meta" and created_at is None:
                    created_at = _usc_norm_ws(el.text)

                if t == "heading" and parent == "title" and title_heading is None:
                    title_heading = _usc_norm_ws("".join(el.itertext()))

                # once we have title_num + title_heading we can check dedupe/replace
                try:
                    prepare_if_ready()
                except StopIteration:
                    # already imported, stop parsing
                    raise

                # chapter details + insert node (supports nested chapters)
                if chapter_stack:
                    top = chapter_stack[-1]

                    if t == "num" and parent == "chapter" and top["num"] is None:
                        # chapters usually want the @value token (e.g., 1) not "CHAPTER 1—"
                        v = el.get("value") or _usc_norm_ws("".join(el.itertext()))
                        top["num"] = _usc_norm_ws(v)

                    if t == "heading" and parent == "chapter" and top["heading"] is None:
                        top["heading"] = _usc_fix_heading_brackets(_usc_norm_ws("".join(el.itertext())))

                    if prepared and top["num"] and top["heading"] and not top["_inserted"]:
                        parent_id = None
                        if top["parent_ctx"] is not None:
                            parent_id = top["parent_ctx"]["node_id"]

                        cur.execute(
                            """
                            INSERT INTO usc_nodes(title_num, node_type, num, heading, identifier, parent_id, ord)
                            VALUES(?, 'chapter', ?, ?, ?, ?, ?)
                            """,
                            (
                                title_num,
                                str(top["num"]),
                                top["heading"],
                                top["identifier"],
                                parent_id,
                                top["ord"],
                            ),
                        )
                        top["node_id"] = cur.lastrowid
                        top["_inserted"] = True

                # section end: insert section row + fts row
                if t == "section":
                    ident = el.get("identifier")

                    # Skip “sections” that live inside notes or aren’t true USC sections
                    if "notes" in stack or not _usc_is_real_usc_section(ident, title_num):
                        el.clear()
                        stack.pop()
                        continue


                    if not prepared:
                        # defensive; should not happen in valid files
                        el.clear()
                        stack.pop()
                        continue

                    

                    section_ord += 1

                    sec_num = None
                    sec_head = None
                    for c in list(el):
                        lt = _usc_local(c.tag)
                        if lt == "num" and sec_num is None:
                            sec_num = _usc_norm_ws(c.get("value") or "".join(c.itertext()))
                        elif lt == "heading" and sec_head is None:
                            sec_head = _usc_norm_ws("".join(c.itertext()))
                            sec_head = _usc_clean_section_heading(sec_head)

                    body = _usc_render_section_body(el)
                    node_id = chapter_stack[-1]["node_id"] if (chapter_stack and chapter_stack[-1]["node_id"]) else None

                    cur.execute(
                        """
                        INSERT OR REPLACE INTO usc_sections(title_num, node_id, section_num, heading, identifier, body_text, ord)
                        VALUES(?,?,?,?,?,?,?)
                        """,
                        (
                            title_num,
                            node_id,
                            str(sec_num or ""),
                            sec_head,
                            el.get("identifier"),
                            body,
                            section_ord,
                        ),
                    )
                    sec_id = cur.lastrowid
                    cur.execute(
                        "INSERT INTO usc_sections_fts(rowid, title_num, section_num, heading, body_text) VALUES(?,?,?,?,?)",
                        (sec_id, title_num, str(sec_num or ""), sec_head or "", body or ""),
                    )

                    el.clear()

                if t == "chapter":
                    if chapter_stack:
                        chapter_stack.pop()
                    el.clear()

                stack.pop()

        conn.commit()

        # counts
        ch_ct = cur.execute(
            "SELECT COUNT(*) AS n FROM usc_nodes WHERE title_num=? AND node_type='chapter'",
            (title_num,),
        ).fetchone()["n"]
        sec_ct = cur.execute(
            "SELECT COUNT(*) AS n FROM usc_sections WHERE title_num=?",
            (title_num,),
        ).fetchone()["n"]

        return {
            "status": "updated" if updated_existing else "imported",
            "title_num": title_num,
            "heading": title_heading,
            "created_at": created_at,
            "chapters": int(ch_ct),
            "sections": int(sec_ct),
            "sha256": sha,
        }

    except StopIteration:
        # already imported
        row = cur.execute(
            "SELECT title_num, heading, created_at, imported_at, source_sha256 FROM usc_titles WHERE title_num=?",
            (title_num,),
        ).fetchone()
        return {
            "status": "already_imported",
            "title_num": row["title_num"] if row else title_num,
            "heading": row["heading"] if row else title_heading,
            "created_at": row["created_at"] if row else created_at,
            "chapters": int(
                cur.execute(
                    "SELECT COUNT(*) AS n FROM usc_nodes WHERE title_num=? AND node_type='chapter'",
                    (title_num,),
                ).fetchone()["n"]
            ) if title_num else 0,
            "sections": int(
                cur.execute(
                    "SELECT COUNT(*) AS n FROM usc_sections WHERE title_num=?",
                    (title_num,),
                ).fetchone()["n"]
            ) if title_num else 0,
            "sha256": row["source_sha256"] if row else sha,
        }
    finally:
        conn.close()


def _usc_chunk_lines(lines: list[str], limit: int = 1700) -> list[str]:
    """
    Chunk lines into pages that will fit inside a normal Discord message
    once wrapped in a code block + header.
    """
    pages: list[str] = []
    cur: list[str] = []
    cur_len = 0

    for ln in lines:
        add = len(ln) + 1
        if cur and (cur_len + add) > limit:
            pages.append("\n".join(cur))
            cur = [ln]
            cur_len = add
        else:
            cur.append(ln)
            cur_len += add

    if cur:
        pages.append("\n".join(cur))
    return pages or ["(none)"]


class USCTextPaginator(discord.ui.View):
    def __init__(self, title: str, pages: list[str], meta: str | None = None):
        super().__init__(timeout=900)
        self.title = title
        self.pages = pages or ["(none)"]
        self.meta = meta or ""
        self.i = 0
        self._sync()

    def _sync(self):
        self.prev.disabled = (self.i <= 0)
        self.next.disabled = (self.i >= len(self.pages) - 1)

    def make_content(self) -> str:
        meta_part = f"\n{self.meta}" if self.meta else ""
        return (
            f"**{self.title}**\n"
            f"```ansi\n{self.pages[self.i]}\n```\n"
            f"`Page {self.i+1}/{len(self.pages)}`{meta_part}"
        )

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = max(0, self.i - 1)
        self._sync()
        await interaction.response.edit_message(content=self.make_content(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = min(len(self.pages) - 1, self.i + 1)
        self._sync()
        await interaction.response.edit_message(content=self.make_content(), view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(view=None)

def _usc_db_list_titles(db_path: str) -> list[sqlite3.Row]:
    _usc_db_init(db_path)
    conn = _usc_db_connect(db_path)
    try:
        return conn.execute(
            "SELECT title_num, heading, created_at, imported_at FROM usc_titles ORDER BY title_num"
        ).fetchall()
    finally:
        conn.close()

def _usc_db_get_chapters(db_path: str, title_num: int) -> list[sqlite3.Row]:
    _usc_db_init(db_path)
    conn = _usc_db_connect(db_path)
    try:
        return conn.execute(
            """
            SELECT id, num, heading, parent_id, ord
            FROM usc_nodes
            WHERE title_num=? AND node_type='chapter'
            ORDER BY ord
            """,
            (title_num,),
        ).fetchall()
    finally:
        conn.close()

def _usc_db_get_chapter_id(db_path: str, title_num: int, chapter_num: str) -> int | None:
    conn = _usc_db_connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT id FROM usc_nodes
            WHERE title_num=? AND node_type='chapter' AND num=?
            LIMIT 1
            """,
            (title_num, str(chapter_num)),
        ).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()

def _usc_db_get_sections_in_chapter(db_path: str, title_num: int, chapter_id: int) -> list[sqlite3.Row]:
    conn = _usc_db_connect(db_path)
    try:
        return conn.execute(
            """
            SELECT section_num, heading
            FROM usc_sections
            WHERE title_num=? AND node_id=?
            ORDER BY ord
            """,
            (title_num, chapter_id),
        ).fetchall()
    finally:
        conn.close()

def _usc_db_get_section(db_path: str, title_num: int, section_num: str) -> sqlite3.Row | None:
    conn = _usc_db_connect(db_path)
    try:
        return conn.execute(
            """
            SELECT s.section_num, s.heading, s.body_text, s.identifier,
                   n.num AS chapter_num, n.heading AS chapter_heading
            FROM usc_sections s
            LEFT JOIN usc_nodes n ON n.id = s.node_id
            WHERE s.title_num=? AND s.section_num=?
            LIMIT 1
            """,
            (title_num, str(section_num)),
        ).fetchone()
    finally:
        conn.close()

def _usc_chunk_codeblock(text: str, limit: int = 1700) -> list[str]:
    lines = (text or "").splitlines()
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for ln in lines:
        add = len(ln) + 1
        if cur and (cur_len + add) > limit:
            chunks.append("\n".join(cur))
            cur = [ln]
            cur_len = add
        else:
            cur.append(ln)
            cur_len += add
    if cur:
        chunks.append("\n".join(cur))
    return chunks

class USCSectionPaginator(discord.ui.View):
    def __init__(self, header: str, where: str | None, pages: list[str]):
        super().__init__(timeout=900)  # 15 min
        self.header = header
        self.where = where or ""
        self.pages = pages or ["(No statute text found.)"]
        self.i = 0
        self._sync()

    def _sync(self):
        self.prev.disabled = (self.i <= 0)
        self.next.disabled = (self.i >= len(self.pages) - 1)

    def make_embed(self) -> discord.Embed:
        body = self.pages[self.i]
        desc = ""
        if self.where:
            desc += f"{self.where}\n\n"
        desc += f"```text\n{body}\n```"

        emb = discord.Embed(title=self.header, description=desc)
        emb.set_footer(text=f"Page {self.i+1}/{len(self.pages)}")
        return emb

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = max(0, self.i - 1)
        self._sync()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = min(len(self.pages) - 1, self.i + 1)
        self._sync()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(view=None)

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

def _try_json_load(txt: str):
    try:
        return json.loads(txt)
    except Exception:
        return None

def _get_state_channel(bot, guild):
    try:
        return guild.get_channel(STATE_DEPARTMENT_CHANNEL) or bot.get_channel(STATE_DEPARTMENT_CHANNEL)
    except Exception:
        return None
    
def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _pick_residency_question(reg: dict) -> str:
    bank = reg.get("residency_questions") or []
    if bank:
        return random.choice(bank)["question"]
    return "What's your favorite flavor of ice cream?"

def _ensure_registry_schema(reg: dict) -> dict:
    # keep this minimal; add/normalize anything you rely on
    if "recent_citizenship_changes" in reg and "recent_citizenship_change" not in reg:
        reg["recent_citizenship_change"] = reg.get("recent_citizenship_changes") or []
    reg.setdefault("recent_citizenship_change", [])
    if not isinstance(reg["recent_citizenship_change"], list):
        reg["recent_citizenship_change"] = []
    return reg

def load_federal_registry():
    """
    Load registry with auto-recovery:
      1) try main file
      2) fall back to .bak
      3) if corrupt, quarantine bad file and return {}
    """
    path = FED_REGISTRY_FILE
    bak  = path + ".bak"

    if not os.path.exists(path):
        return {}

    # First, try the main file
    try:
        with open(path, "r", encoding="utf-8") as f:
            reg = json.load(f)
            reg = _ensure_registry_schema(reg)
            return reg

    except json.JSONDecodeError:
        # Try backup
        try:
            if os.path.exists(bak):
                with open(bak, "r", encoding="utf-8") as bf:
                    return json.load(bf)
        except Exception:
            pass
        # Quarantine the bad file so we can boot
        try:
            bad = f"{path}.corrupt-{int(time.time())}.json"
            os.replace(path, bad)  # keeps the evidence for manual salvage if you want
        finally:
            return {}
    except Exception:
        # any other unexpected I/O error
        return {}

def save_federal_registry(data: dict) -> None:
    # never write half a file again
    os.makedirs(os.path.dirname(FED_REGISTRY_FILE), exist_ok=True)
    # pre-save backup
    if os.path.exists(FED_REGISTRY_FILE):
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak = f"{FED_REGISTRY_FILE}.{ts}.bak"
        try:
            os.replace(FED_REGISTRY_FILE, bak)
        except Exception:
            pass  # best effort

    # write atomically
    fd, tmp = tempfile.mkstemp(prefix="freg_", suffix=".json", dir=os.path.dirname(FED_REGISTRY_FILE))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, FED_REGISTRY_FILE)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _elections_root(reg: dict) -> dict:
    return reg.setdefault("elections", {"contests": {}, "voters": {}})

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()

def _next_general_election(today: date | None = None) -> date:
    # Tuesday after the first Monday in November
    d = today or datetime.now(UTC).date()
    year = d.year if (d.month, d.day) <= (11, 30) else d.year + 1
    nov1 = date(year, 11, 1)
    # weekday(): Mon=0..Sun=6 ; we want first Monday then add a day to get Tuesday
    first_monday = nov1 + timedelta(days=(0 - nov1.weekday()) % 7)
    election_day = first_monday + timedelta(days=1)  # Tuesday after first Monday
    return election_day

def _compute_deadlines(elec_day: date) -> tuple[date, date]:
    filing = elec_day - timedelta(days=21)
    certify = elec_day - timedelta(days=14)
    return filing, certify

def _contest_id(office: str, category: str, election_day: date, district: str | None, seats: int) -> str:
    base = f"{election_day.isoformat()}_{office.lower()}_{category.lower()}"
    if district:
        base += f"_{district.lower()}"
    if seats and seats > 1:
        base += f"_x{seats}"
    return base

def _contest_bucket(reg: dict, cid: str) -> dict:
    return _elections_root(reg)["contests"].setdefault(cid, {})

def _has_role_or_admin(member: discord.Member, role_id: int) -> bool:
    return (role_id and any(r.id == role_id for r in member.roles)) or member.guild_permissions.administrator

def _poll_tally_from_message(msg: discord.Message) -> list[tuple[str, int]]:
    """
    Returns list of (answer_text, votes) in the order shown on the poll.
    """
    poll = getattr(msg, "poll", None)
    if not poll:
        return []
    out = []
    for a in poll.answers:
        # answer: .text, .emoji, .vote_count
        out.append((a.text, int(getattr(a, "vote_count", 0))))
    return out

def _percent(n: int, d: int) -> float:
    return (100.0 * n / d) if d else 0.0

def _top_two_margin_one_percent(tally: list[tuple[str,int]]) -> tuple[bool, float]:
    if not tally or len(tally) < 2:
        return (False, 0.0)
    sorted_by_votes = sorted(tally, key=lambda kv: kv[1], reverse=True)
    top, second = sorted_by_votes[0][1], sorted_by_votes[1][1]
    total = sum(v for _, v in tally)
    # margin as percentage points of total ballots
    margin_pct = abs(_percent(top - second, total))
    return (margin_pct <= 1.0, margin_pct)

def _grace_bucket(reg: dict) -> dict:
    # Global one-time grace holder
    return _elections_root(reg).setdefault("grace_once", {
        "enabled": False,
        "through": None,               # "YYYY-MM-DD"
        "allow_registration": False,
        "allow_filing": False,
        "note": None,                  # optional audit note
    })

def _grace_ok(reg: dict, contest: dict | None, key: str) -> bool:
    """
    key in {"registration","filing"}.
    Checks contest.grace first, then global grace_once.
    Only true if enabled AND today <= through.
    """
    def _check(g: dict | None) -> bool:
        if not g or not g.get("enabled"):
            return False
        if not g.get(f"allow_{key}", False):
            return False
        thru = g.get("through")
        try:
            if thru and datetime.now(UTC).date() <= date.fromisoformat(thru):
                return True
        except Exception:
            return False
        return False

    if contest and _check(contest.get("grace")):
        return True
    return _check(_grace_bucket(reg))

def _next_federal_election_day(start: date | None = None) -> date:
    """Tuesday after the first Monday in November of this year (or next)."""
    today = start or datetime.now(UTC).date()
    # First Monday in November
    first_nov = date(today.year, 11, 1)
    first_mon = first_nov + timedelta(days=(0 - first_nov.weekday()) % 7)  # Monday=0
    if first_mon.month != 11:  # if wrapped back into Oct, push a week
        first_mon = first_mon + timedelta(days=7)
    election = first_mon + timedelta(days=1)  # Tuesday
    if today > election:
        # use next year
        first_nov = date(today.year + 1, 11, 1)
        first_mon = first_nov + timedelta(days=(0 - first_nov.weekday()) % 7)
        if first_mon.month != 11:
            first_mon = first_mon + timedelta(days=7)
        election = first_mon + timedelta(days=1)
    return election

def _equal_proportions_apportion(pop_map: dict[str,int], house_size: int) -> dict[str,int]:
    """
    Huntington–Hill with min 1 seat per category.
    Deterministic tie-break: higher pop, then name (A→Z).
    """
    # start with 1 each
    seats = {k: 1 for k in pop_map}
    assigned = len(seats)
    # priority function p/sqrt(n(n+1))
    def priority(p, n): return p / math.sqrt(n * (n + 1))
    # keep handing out seats until house_size
    while assigned < house_size:
        # choose the category with the max next priority
        best_key = max(
            pop_map.keys(),
            key=lambda k: (priority(pop_map[k], seats[k]), pop_map[k], -ord(k[0]) if k else 0)
        )
        seats[best_key] += 1
        assigned += 1
    return seats

def _count_category_citizens(guild, CITIZENSHIP: dict[str,int]) -> dict[str,int]:
    """
    Counts members that hold exactly one of the category roles in CITIZENSHIP (bots excluded).
    If you want to restrict to Citizens only, add an extra filter for CITIZENSHIP_ROLE.
    """
    counts = {k: 0 for k in CITIZENSHIP}
    cid_to_key = {rid: k for k, rid in CITIZENSHIP.items()}
    for m in guild.members:
        if m.bot: 
            continue
        cat_keys = [cid_to_key[r.id] for r in m.roles if r.id in cid_to_key]
        # treat the first category role as their residence if they somehow have several
        if cat_keys:
            counts[cat_keys[0]] += 1
    return counts

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

STATUS_CHANNEL_ID = 1420796334910210178  # “bill status” channel you created

def _now_iso():
    return datetime.now(UTC).isoformat()

def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # allow both ISO and ISO with 'Z'
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

def _ensure_citizenship_bucket(reg: dict) -> dict:
    # normalize plural vs singular
    if "recent_citizenship_changes" not in reg and "recent_citizenship_change" in reg:
        reg["recent_citizenship_changes"] = reg.get("recent_citizenship_change") or {}
    bucket = reg.setdefault("recent_citizenship_changes", {})
    # coerce keys to str and values to ISO strings
    fixed, changed = {}, False
    for k, v in list(bucket.items()):
        sk = str(k)
        if isinstance(v, datetime):
            iso = v.astimezone(UTC).isoformat()
        elif isinstance(v, (int, float)):
            iso = datetime.fromtimestamp(v, UTC).isoformat()
        elif isinstance(v, str):
            iso = v if _parse_iso(v) else _now_iso()
        else:
            iso = _now_iso()
        if sk != k or iso != v:
            changed = True
        fixed[sk] = iso
    if changed:
        reg["recent_citizenship_changes"] = fixed
    # future-proof switch you mentioned
    reg.setdefault("election_active", False)
    return reg

def _iso_to_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(UTC)
    except Exception:
        return datetime.now(UTC)

def _vote_expired(vote: dict) -> bool:
    if not vote: return False
    opened_at = _iso_to_dt(vote.get("opened_at",""))
    hours = int(vote.get("hours", 24))
    return datetime.now(UTC) >= opened_at + timedelta(hours=hours)

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

def _choice_val(x):
    """Return .value for app_commands.Choice, else the string as-is (or None)."""
    try:
        return x.value  # Choice
    except AttributeError:
        return x        # already a str or None

# --- helper: parse attachment text without saving a file ---
async def extract_text_from_attachment(att: discord.Attachment) -> str:
    """
    Reads a Discord attachment and returns extracted text.
    Supported:
      - .txt / .md -> UTF-8 decode (with errors='replace')
      - .docx      -> python-docx (if available)
      - .pdf       -> PyPDF2 (if available)
    Falls back to UTF-8 decode if unknown.
    """
    name = (att.filename or "").lower()
    data = await att.read()

    def _utf8(b: bytes) -> str:
        return b.decode("utf-8", errors="replace")

    if name.endswith((".txt", ".md")):
        return _utf8(data)

    if name.endswith(".docx"):
        if not docx:
            raise RuntimeError("`.docx` parsing requires the `python-docx` package.")
        from io import BytesIO
        try:
            d = docx.Document(BytesIO(data))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception as e:
            raise RuntimeError(f"Failed to parse .docx: {e}")

    if name.endswith(".pdf"):
        if not PdfReader:
            raise RuntimeError("`.pdf` parsing requires the `PyPDF2` package.")
        from io import BytesIO
        try:
            reader = PdfReader(BytesIO(data))
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
            return "\n".join(parts)
        except Exception as e:
            raise RuntimeError(f"Failed to parse .pdf: {e}")

    # Unknown type → try UTF-8 best-effort
    return _utf8(data)


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

def _seat_key(self, c: dict) -> str:
    """Stable key for a single-seat contest. House uses seat_index if present."""
    kind = c.get("kind")
    cat  = c.get("category")
    if kind == "senate":
        return f"senate:{cat}"
    # one-seat-per-contest model
    return f"house:{cat}:{c.get('seat_index') or 1}"

async def _grant_office(self, interaction: discord.Interaction, contest_id: str, winner_id: int):
    """Certify & seat the winner. Allows the same user to occupy multiple offices."""
    reg    = self.federal_registry
    eroot  = _elections_root(reg)
    c      = (eroot.get("contests") or {}).get(contest_id)
    if not c:
        return

    seats  = eroot.setdefault("seats", {})
    seats[self._seat_key(c)] = {
        "member_id": int(winner_id),
        "contest_id": contest_id,
        "sworn_at": _now_iso(),
    }

    # Grant the chamber role (they can end up with both roles if they won both)
    guild  = interaction.guild
    member = guild.get_member(int(winner_id))
    if member:
        role_id = SENATORS if c.get("kind") == "senate" else REPRESENTATIVES
        role = guild.get_role(role_id)
        if role and role not in member.roles:
            try:
                await member.add_roles(role, reason=f"Elected via {contest_id}")
            except Exception:
                pass

    # Update registry and lightly announce
    save_federal_registry(reg)
    try:
        ch = interaction.client.get_channel(ELECTIONS_ANNOUNCE_CHANNEL)
        if ch:
            await ch.send(f"✅ Certified **{contest_id}** — seated <@{winner_id}>.")
    except Exception:
        pass


def _bold_headings_single(raw_text: str, budget: int = 4000) -> str:
    """
    Bold only heading lines (Title/Section/§) while preserving the line EXACTLY.
    Returns a single string trimmed to embed-safe size.
    """
    out = []
    used = 0
    for line in (raw_text or "").splitlines():
        s = line.rstrip("\r\n")
        if _TITLE_LINE.match(s) or _SECTION_LINE.match(s):
            s = f"**{s.strip()}**"
        # +1 for newline
        need = len(s) + 1
        if used + need > budget:
            # graceful tail if first line is huge
            room = max(0, budget - used - 3)
            if room > 0:
                if need > room:
                    out.append(s[:room] + "...")
                else:
                    out.append(s)
            break
        out.append(s)
        used += need
    return "\n".join(out)


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
    
def probe_federal_registry():
    """
    Return (data, None) if OK, (None, exc) if JSON is corrupt.
    Does NOT rename or modify files. Pure read.
    """
    path = FED_REGISTRY_FILE
    p = Path(path)
    if not p.exists():
        return {}, None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, e

def _validate_exam_bank(bank: list[dict]) -> None:
    # Optional: sanity checks; raises if something is off.
    for i, q in enumerate(bank, start=1):
        if not isinstance(q.get("q"), str) or not q["q"].strip():
            raise ValueError(f"Exam q#{i}: missing text")
        choices = q.get("choices") or []
        if not isinstance(choices, list) or len(choices) < 2:
            raise ValueError(f"Exam q#{i}: need ≥2 choices")
        ans = q.get("answer")
        if not isinstance(ans, int) or not (0 <= ans < len(choices)):
            raise ValueError(f"Exam q#{i}: bad answer index {ans}")

def _build_exam_paper(reg: dict, n: int) -> list[dict]:
    bank = _ensure_exam_bank(reg)
    _validate_exam_bank(bank)  # safe to remove if you don’t want the guard
    n = max(1, min(n, len(bank)))
    selected = random.sample(bank, n)
    paper = []
    for item in selected:
        # shuffle choices and remap correct index
        order = list(range(len(item["choices"])))
        random.shuffle(order)
        shuffled = [item["choices"][i] for i in order]
        correct_idx = order.index(item["answer"])
        paper.append({
            "id": item["id"],
            "text": item["q"],
            "choices": shuffled,
            "correct_idx": correct_idx,
        })
    return paper

class CitizenshipApplicationModal(discord.ui.Modal, title="Citizenship Application"):
    def __init__(self, cog: commands.Cog, applicant: discord.Member):
        super().__init__()
        self.cog = cog
        self.applicant = applicant

        self.q1 = discord.ui.TextInput(
            label="Why do you want citizenship?",
            style=discord.TextStyle.paragraph, max_length=500, required=True
        )
        self.q2 = discord.ui.TextInput(
            label="Have you read the Rules & Constitution?",
            placeholder="Yes / No (and any comments)",
            style=discord.TextStyle.short, max_length=100, required=True
        )
        self.q3 = discord.ui.TextInput(
            label="Category preference (optional)",
            placeholder="The Category you most identify with, if any",
            style=discord.TextStyle.short, max_length=50, required=False
        )
        self.q4 = discord.ui.TextInput(
            label="Anything else we should know? (optional)",
            style=discord.TextStyle.paragraph, max_length=500, required=False
        )

        for inp in (self.q1, self.q2, self.q3, self.q4):
            self.add_item(inp)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        cog = self.cog
        guild = interaction.guild

        # mark applicant role
        role = guild.get_role(CITIZENSHIP_APPLICANT)
        try:
            if role and role not in self.applicant.roles:
                await self.applicant.add_roles(role, reason="Filed citizenship application")
        except Exception:
            pass

        # find/create intake thread (reuse your residency thread bucket)
        intake_map = cog.federal_registry.setdefault("residency_threads", {})
        info = (intake_map.get(str(self.applicant.id)) or {})
        thread = cog.bot.get_channel(int(info.get("thread_id"))) if info.get("thread_id") else None
        if not thread:
            # fallback: private thread under WAVING (you allow PENDING to see WAVING)
            parent = cog.bot.get_channel(WAVING)
            if parent and str(getattr(parent, "type", "")) == "text":
                thread = await parent.create_thread(
                    name=f"Citizenship — {self.applicant.display_name}",
                    type=discord.ChannelType.private_thread,
                    invitable=False,
                    auto_archive_duration=1440
                )
                try:
                    await thread.add_user(self.applicant)
                except Exception:
                    pass
                intake_map[str(self.applicant.id)] = {"thread_id": thread.id, "opened_at": _now_iso()}
                save_federal_registry(cog.federal_registry)

        # persist application
        apps = cog.federal_registry.setdefault("citizenship_applications", {})
        apps[str(self.applicant.id)] = {
            "filed_at": _now_iso(),
            "answers": {
                "why": str(self.q1.value).strip(),
                "read_const": str(self.q2.value).strip(),
                "pref": (str(self.q3.value).strip() or None),
                "extra": (str(self.q4.value).strip() or None),
            },
            "status": "filed"
        }
        save_federal_registry(cog.federal_registry)

        # post to thread & state channel
        body = (
            f"**Citizenship Application — {self.applicant.mention}**\n"
            f"**Q1:** {self.q1.value}\n"
            f"**Q2:** {self.q2.value}\n"
            f"**Q3:** {self.q3.value or '—'}\n"
            f"**Q4:** {self.q4.value or '—'}\n"
        )
        if thread:
            try: await thread.send(body, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
            except Exception: pass
        st = _get_state_channel(cog.bot, guild)
        if st:
            try: await st.send(body)
            except Exception: pass

        await interaction.followup.send("✅ Application submitted!", ephemeral=True)

class OathView(discord.ui.View):
    def __init__(self, cog: commands.Cog, user_id: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="I swear", style=discord.ButtonStyle.success)
    async def swear(self, interaction: discord.Interaction, button: discord.ui.Button):
        reg = self.cog.federal_registry
        rec = reg.setdefault("citizenship_records", {}).setdefault(str(self.user_id), {})
        rec["oath_taken_at"] = _now_iso()
        save_federal_registry(reg)

        # Optional: auto-assign Citizenship role here (commented to keep your approval flow)
        # role = interaction.guild.get_role(CITIZENSHIP_ROLE)
        # if role and role not in interaction.user.roles:
        #     try: await interaction.user.add_roles(role, reason="Oath taken")
        #     except Exception: pass

        st = _get_state_channel(self.cog.bot, interaction.guild)
        if st:
            try: await st.send(f"🤝 Oath taken by {interaction.user.mention}.")
            except Exception: pass
        await interaction.response.send_message("✅ Oath recorded.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("You declined the oath. You can run the command again later.", ephemeral=True)
        self.stop()
    
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
        self.summary = discord.ui.TextInput(label="Summary", style=discord.TextStyle.paragraph, required=False)
        self.purpose = discord.ui.TextInput(label="Purpose Statement", style=discord.TextStyle.paragraph, required=False)
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
        max_length=4000
    )

    def __init__(self, parent):
        super().__init__()
        self.parent = parent  # the Cog

    async def on_submit(self, interaction: discord.Interaction):
        reg = self.parent.federal_registry
        store = reg.setdefault("executive_orders", {}).setdefault("items", {})

        from datetime import datetime
        yr = datetime.utcnow().year
        seq = reg.setdefault("executive_orders", {}).setdefault("seq", {}).get(str(yr), 0) + 1
        reg["executive_orders"]["seq"][str(yr)] = seq
        eo_id = f"EO-{yr}-{seq:04d}"

        # FIX: pull .value for all inputs
        title = (self.eo_title.value or "").strip()
        summary = (self.eo_summary.value or "").strip()
        body = (self.eo_body.value or "")

        sections = _parse_sections_from_text(body)

        order = {
            "id": eo_id,
            "title": title,
            "summary": summary,
            "text": body,
            "structure": {"titles": [{"name": "Executive Order", "sections": sections}]},
            "issued_by": interaction.user.id,
            "issued_at": discord.utils.utcnow().isoformat(),
            "status": "ISSUED",
        }
        store[eo_id] = order
        save_federal_registry(reg)

        wh = interaction.client.get_channel(SPIDEY_HOUSE)
        pages = _format_eo_for_display(order)
        if wh:
            head = discord.Embed(title=f"{eo_id} — {order['title']}", description=(order.get("summary") or ""), color=discord.Color.dark_gold())
            await wh.send(embed=head)
            for p in pages:
                await wh.send(embed=discord.Embed(description=p[:4000], color=discord.Color.dark_gold()))

        await interaction.response.send_message(f"✅ Issued **{eo_id}** — {order['title']}", ephemeral=True)

def _ensure_exam_bank(reg: dict):
    bank = reg.setdefault("citizenship_exam_bank", [])
    if bank:
        return bank
    # seed a few example questions (edit/expand later via admin cmds)
    bank.extend([
        {"id": "c1", "q": "What does Art. I primarily cover?", "choices": ["Judiciary", "Executive", "Legislature", "Elections"], "answer": 2},
        {"id": "c2", "q": "How many chambers in Congress here?", "choices": ["1", "2", "3", "It depends"], "answer": 1},
        {"id": "c3", "q": "Who can open a floor vote?", "choices": ["Any user", "Only chamber members", "Only President", "Only admins"], "answer": 1},
        {"id": "c4", "q": "Bills exceeding 4000 chars should be…", "choices": ["Rejected", "Split across embeds", "Threaded/paginated", "DM’d to mods"], "answer": 2},
        {"id": "c5", "q": "Where are enacted laws recorded?", "choices": ["Random channel", "Federal Registry", "Direct Messages", "Welcome"], "answer": 1},
        {"id": "c6", "q": "Quorum is computed using…", "choices": ["All online users", "Eligible chamber members", "Admins only", "Citizens only"], "answer": 1},
        {"id": "c7", "q": "Executive Orders are…", "choices": ["Legislation", "Court opinions", "Executive directives", "None"], "answer": 2},
        {"id": "c8", "q": "Amendments to a bill can target…", "choices": ["Whole bill only", "Specific Title/Section", "Only Title level", "Only Section level"], "answer": 1},
        {"id": "c9", "q": "Reporter publishes…", "choices": ["Bills", "Opinions/Orders", "Polls", "Rules"], "answer": 1},
        {"id": "c10","q": "Intake threads live under…", "choices": ["Rules", "Waving", "DMs", "Forum"], "answer": 1},
    ])
    return bank

def _exam_bucket(reg: dict):
    return reg.setdefault("citizenship_exams", {})  # user_id -> record

def _pick_exam(reg: dict, n: int):
    import random
    bank = _ensure_exam_bank(reg)
    n = max(1, min(n, len(bank)))
    return random.sample(bank, n)

class ExamQuestionView(discord.ui.View):
    def __init__(self, cog: commands.Cog, user_id: int, exam_id: str, q_idx: int, total: int, choices: list[str], timeout: float = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.user_id = user_id
        self.exam_id = exam_id
        self.q_idx = q_idx
        self.total = total
        labels = ["A", "B", "C", "D"][:len(choices)]
        for i, label in enumerate(labels):
            self.add_item(ExamChoiceButton(label=label, idx=i))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

class ExamChoiceButton(discord.ui.Button):
    def __init__(self, label: str, idx: int):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.choice_idx = idx

    async def callback(self, interaction: discord.Interaction):
        cog: "SpideyGov" = interaction.client.get_cog("SpideyGov")
        if not cog:
            return await interaction.response.send_message("Cog missing.", ephemeral=True)
        await cog._exam_record_and_advance(interaction, self.choice_idx)

class SpideyGov(commands.Cog):
    def __init__(self, bot):
        global REGISTRY_SUSPENDED

        self.bot = bot
        self.registry_readonly = REGISTRY_SUSPENDED
        data, err = probe_federal_registry()
        if err is None:
            self.federal_registry = data or {}
            self.registry_readonly = False
            REGISTRY_SUSPENDED = False
            try:
                self.bill_poll_sweeper.start()
                self.bill_status_ticker.start()
            except Exception:
                pass
        else:
            self.federal_registry = {}
            self.registry_readonly = True
            REGISTRY_SUSPENDED = True
            print(f"ERROR: Could not load federal registry JSON: {err}")

        ensure_constitution_schema(self.federal_registry)
        normalize_registry_order(self.federal_registry)
        self.registry_lock = asyncio.Lock()

        self.SPEAKER_OF_THE_HOUSE = None
        self.SENATE_MAJORITY_LEADER = None

        try:
            _usc_db_init(USC_DB_FILE)
        except Exception as e:
            print(f"USC DB init error: {e}")
        
        self.usc_lock = asyncio.Lock()

        # --- SRC database init ---
        try:
            _src_db_init(SRC_DB_FILE)
        except Exception as e:
            print(f"SRC DB init error: {e}")

        self.src_lock = asyncio.Lock()
        

    def cog_unload(self):
        # Always stop tasks
        try: self.bill_poll_sweeper.cancel()
        except Exception: pass
        try: self.bill_status_ticker.cancel()
        except Exception: pass

        # Skip saving if we were in read-only
        if getattr(self, "registry_readonly", False):
            return
        try:
            save_federal_registry(self.federal_registry)
        except Exception:
            pass
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Give PENDING role and open an intake thread with a residency question."""
        guild = member.guild
        
            
        if guild.id != 1287645024309477460:
            return
        
        state_dep = guild.get_channel(STATE_DEPARTMENT_CHANNEL)
        bot_dep = guild.get_channel(BOT_DEPARTMENT_CHANNEL)

        if member.bot:
            await member.add_roles(guild.get_role(1288016221383561236), reason="Bot account")
            await state_dep.send(f"Bot account {member.mention} has been added to the server.")
            await bot_dep.send(f"A bot account has been added to the server: {member.mention}. If this was not agreed upon by the council, please inform an admin, and they will be removed immediately.")
            return

        try:
            pend = guild.get_role(PENDING_RESIDENT)
            if pend and pend not in member.roles:
                await member.add_roles(pend, reason="New arrival — residency intake")
        except Exception:
            pass

        parent = self.bot.get_channel(WAVING)
        if not parent:
            return

        q = _pick_residency_question(self.federal_registry)
        admin_role = guild.get_member(SEC_OF_STATE)
        admin_ping = admin_role.mention

        try:
            thread = await parent.create_thread(
                name=f"Residency — {member.display_name}",
                type=discord.ChannelType.private_thread,
                invitable=False,
                auto_archive_duration=1440
            )
            try:
                await thread.add_user(member)  # ensure they can see it first
            except Exception:
                pass

            await thread.send(
                f"{admin_ping}\nWelcome {member.mention}! Please answer:\n\n> {q}",
                allowed_mentions=discord.AllowedMentions(roles=True, users=True, everyone=False)
            )
            bucket = self.federal_registry.setdefault("residency_threads", {})
            bucket[str(member.id)] = {"thread_id": thread.id, "opened_at": discord.utils.utcnow().isoformat()}
            save_federal_registry(self.federal_registry)
        except Exception:
            # swallow — onboarding should not crash join
            pass

        
        await state_dep.send(f"New member {member.mention} joined. Residency intake thread opened: {thread.mention}")

    async def elections_contest_autocomplete(self, interaction: discord.Interaction, current: str):
        reg = self.federal_registry
        contests = _elections_root(reg)["contests"]
        cur = (current or "").lower()
        out = []
        for cid, c in contests.items():
            label = f"{cid} — {(c.get('office') or c.get('kind') or '?').title()} ({c.get('category','?')})"
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label[:100], value=cid))
        return out[:25]

    async def category_autocomplete(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        out = []
        for key, role_id in CITIZENSHIP.items():
            label = key.replace("_", " ").title()
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label, value=key))
        return out[:25]

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
    
    async def _fetch_message(self, channel_id: int, message_id: int):
        ch = self.bot.get_channel(int(channel_id))
        if not ch: return None, None
        try:
            msg = await ch.fetch_message(int(message_id))
            return ch, msg
        except Exception:
            return ch, None

    async def _auto_close_vote_for_bill(self, bill: dict):
        """Mirror your close_vote math, but without an interaction context."""
        v = bill.get("vote") or {}
        ch, msg = await self._fetch_message(v.get("channel_id"), v.get("message_id"))
        if not ch or not msg:
            # mark failed if we can’t fetch the poll
            bill["status"] = "FAILED"
            v["closed_at"] = _now_iso()
            return

        # try to end poll
        try:
            await msg.end_poll()
            msg = await ch.fetch_message(msg.id)  # re-fetch for final tallies
        except Exception:
            pass

        yea, nay, present, total = _tally_from_message(msg)
        quorum = v.get("quorum_required", 0)
        eligible = v.get("eligible_count", 0)

        if total < quorum:
            outcome = "NO_QUORUM"
            bill["status"] = "FAILED"
        else:
            th = v.get("threshold", "simple")
            outcome = _decide(yea, nay, present, th)
            bill["status"] = "PASSED" if outcome == "PASSED" else "FAILED"

        v.update({
            "closed_at": _now_iso(),
            "yea": yea, "nay": nay, "present": present,
            "total": total,
            "outcome": outcome,
        })

        # public result embed in the chamber channel
        color = discord.Color.green() if outcome == "PASSED" else discord.Color.red()
        e = discord.Embed(
            title=f"{bill['id']} — Vote {outcome}",
            description=bill.get("title",""),
            color=color
        )
        e.add_field(name="Yea", value=str(yea))
        e.add_field(name="Nay", value=str(nay))
        e.add_field(name="Present", value=str(present))
        e.add_field(name="Ballots cast", value=str(total))
        e.set_footer(text=f"Eligible: {eligible} · Quorum: {quorum} · Threshold: {v.get('threshold','simple')}")
        await ch.send(embed=e)

        # nice: flash in status channel
        await self._status_flash(f"**{bill['id']}** vote closed → **{outcome}** ({yea}-{nay}-{present}).")

    async def _get_status_channel(self):
        return self.bot.get_channel(STATUS_CHANNEL_ID)

    async def _status_flash(self, text: str, color: discord.Color = discord.Color.gold()):
        ch = await self._get_status_channel()
        if not ch: return
        try:
            await ch.send(embed=discord.Embed(description=text, color=color), delete_after=86400)
        except Exception:
            pass
    
    def _compose_bill_status_embed(self, reg: dict) -> discord.Embed:
        items = (reg.get("bills") or {}).get("items") or {}
        # group by status
        buckets = {}
        for b in items.values():
            buckets.setdefault(b.get("status","DRAFT"), []).append(b)

        # show a compact summary + top few IDs per bucket
        e = discord.Embed(
            title="Legislative Status — Live",
            color=discord.Color.blurple(),
            timestamp=datetime.now(UTC)
        )
        order = ["DRAFT","INTRODUCED","FLOOR VOTE OPEN","PASSED","FAILED","SENT_TO_OTHER","RECEIVED_OTHER","ENROLLED","PRESENTED","ENACTED","VETOED"]
        for key in order:
            arr = buckets.get(key, [])
            if not arr: continue
            # list first 8 bills in this status
            ids = ", ".join(sorted((b["id"] for b in arr))[:8])
            e.add_field(name=f"{key.title()} ({len(arr)})", value=(ids or "—"), inline=False)
        return e
    
    async def _upsert_status_message(self):
        reg = self.federal_registry
        # remember a single message id so we always edit in place
        root = reg.setdefault("bills", {})
        meta = root.setdefault("status_meta", {})
        ch = await self._get_status_channel()
        if not ch: return

        embed = self._compose_bill_status_embed(reg)
        msg_id = meta.get("message_id")
        if msg_id:
            try:
                msg = await ch.fetch_message(int(msg_id))
                await msg.edit(embed=embed)
                return
            except Exception:
                pass
        # create fresh if missing
        m = await ch.send(embed=embed)
        meta["message_id"] = m.id
        save_federal_registry(reg)

    @tasks.loop(hours=1.0)
    async def bill_poll_sweeper(self):
        """Hourly: auto-close any expired polls."""
        reg = self.federal_registry
        items = (reg.get("bills") or {}).get("items") or {}
        dirty = False
        for b in list(items.values()):
            v = b.get("vote") or {}
            if v.get("message_id") and b.get("status") == "FLOOR VOTE OPEN" and _vote_expired(v):
                try:
                    await self._auto_close_vote_for_bill(b)
                    mark_history(b, "Vote auto-closed by sweeper", None)
                    dirty = True
                except Exception:
                    # don’t crash the loop; try the next bill
                    continue
        if dirty:
            save_federal_registry(reg)


    @bill_poll_sweeper.before_loop
    async def _wait_ready_sweeper(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1.0)
    async def bill_status_ticker(self):
        """Hourly: update the live status card."""
        try:
            await self._upsert_status_message()
        except Exception:
            pass

    @bill_status_ticker.before_loop
    async def _wait_ready_status(self):
        await self.bot.wait_until_ready()

    

    government = app_commands.Group(name="government", description="Government-related commands")
    legislature = app_commands.Group(name="legislature", description="Legislative commands", parent=government)
    executive = app_commands.Group(name="executive", description="Executive commands", parent=government)
    category = app_commands.Group(name="category", description="Category management commands", parent=government)
    registry = app_commands.Group(name="registry", description="Commands for viewing and updating the federal registry", parent=government)
    citizenship = app_commands.Group(name="citizenship", description="Citizenship-related commands", parent=government)
    elections = app_commands.Group(name="elections", description="Elections & registration")
    usc = app_commands.Group(name="usc", description="United States Code")
    src = app_commands.Group(name="src", description="Spidey Republic Code (S.R.C.)")
    compare = app_commands.Group(
        name="compare",
        description="Compare S.R.C. to U.S.C.",
        parent=src
    )


    @elections.command(name="party_create", description="Create a new political party")
    @app_commands.describe(name="Full name of the party", abbreviation="Short abbreviation (3-6 chars)", color="Color for the party (hex code, e.g. #ff0000)", desc="Short description (optional)")
    async def party_create(self, interaction: discord.Interaction, name: str, abbreviation: str, color: str, desc: str = None):
        await interaction.response.defer(ephemeral=True)
        reg = self.federal_registry
        parties = _elections_root(reg).setdefault("parties", {})

        name = (name or "").strip()
        abbreviation = (abbreviation or "").strip().upper()
        color = (color or "").strip()
        desc = (desc or "").strip()

        if not name:
            return await interaction.followup.send("Party name is required.", ephemeral=True)
        if not abbreviation or not re.match(r"^[A-Z]{3,6}$", abbreviation):
            return await interaction.followup.send("Abbreviation must be 3-6 letters (A-Z).", ephemeral=True)
        if abbreviation in parties:
            return await interaction.followup.send("Abbreviation already in use.", ephemeral=True)
        try:
            if color.startswith("#"):
                color = color[1:]
            int(color, 16)
            if len(color) not in (3, 6):
                raise ValueError()
            color = "#" + color.upper()
        except Exception:
            return await interaction.followup.send("Color must be a valid hex code, e.g. #ff0000.", ephemeral=True)

        party_id = abbreviation
        parties[party_id] = {
            "id": party_id,
            "name": name,
            "abbreviation": abbreviation,
            "color": color,
            "description": desc,
            "created_at": discord.utils.utcnow().isoformat(),
            "members": [],
        }
        save_federal_registry(reg)

        await interaction.followup.send(f"✅ Created party **{name}** ({abbreviation})", ephemeral=True)
    
    @elections.command(name="party_list", description="List all political parties")
    async def party_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        reg = self.federal_registry
        parties = _elections_root(reg).get("parties", {})

        if not parties:
            return await interaction.followup.send("No parties found.", ephemeral=True)

        embed = discord.Embed(title="Political Parties", color=discord.Color.blue())
        for p in sorted(parties.values(), key=lambda x: x.get("name","")):
            name = f"{p.get('name','')} ({p.get('abbreviation','')})"
            desc = p.get("description") or "No description."
            members = len(p.get("members", []))
            embed.add_field(name=name, value=f"{desc}\nMembers: {members}", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def party_autocomplete(self, interaction: discord.Interaction, current: str):
        reg = self.federal_registry
        parties = _elections_root(reg).get("parties", {})
        cur = (current or "").lower()
        out = []
        for pid, p in parties.items():
            label = f"{p.get('name','')} ({p.get('abbreviation','')})"
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label[:100], value=pid))
        out.append(app_commands.Choice(name="None / Independent", value="independent"))
        return out[:25]
    
    @elections.command(name="register_to_vote", description="Register to vote for Federal elections")
    @app_commands.describe(category="Your Category (for House/Senate voting)", party="Your party label or 'independent'")
    @app_commands.autocomplete(category=category_autocomplete, party=party_autocomplete)
    async def register_to_vote(self, interaction: discord.Interaction, category: str, party: str = "independent"):
        reg = self.federal_registry
        eroot = _elections_root(reg)
        voters = eroot["voters"]

        # gate: must be Citizen in that Category
        if not any(r.id == CITIZENSHIP_ROLE for r in interaction.user.roles):
            return await interaction.response.send_message("You must be a Citizen to register.", ephemeral=True)
        cat_role_id = CITIZENSHIP.get(category)
        if not cat_role_id or not any(r.id == cat_role_id for r in interaction.user.roles):
            return await interaction.response.send_message("Your roles do not reflect that Category.", ephemeral=True)

        # freeze check (optional) with grace override
        freeze = eroot.get("registration_freeze")
        if freeze:
            if datetime.now(UTC).date() > date.fromisoformat(freeze) and not _grace_ok(reg, None, "registration"):
                return await interaction.response.send_message("Registration deadline has passed.", ephemeral=True)

        voters[str(interaction.user.id)] = {
            "category": category,
            "party": (party or "independent"),
            "registered_at": _now_iso(),
            "active": True,
            "late_grace": bool(freeze and _grace_ok(reg, None, "registration")),
        }
        save_federal_registry(reg)
        return await interaction.response.send_message(
            f"✅ Registered to vote in **{category.replace('_',' ').title()}**"
            + (" (accepted under one-time grace)" if voters[str(interaction.user.id)]["late_grace"] else ""),
            ephemeral=True
        )


    @elections.command(name="voter_status", description="See your voter registration")
    async def voter_status(self, interaction: discord.Interaction):
        rec = _elections_root(self.federal_registry)["voters"].get(str(interaction.user.id))
        if not rec:
            return await interaction.response.send_message("You are not registered.", ephemeral=True)
        e = discord.Embed(title="Voter Registration",
                        description=f"**Category:** {rec.get('category','?').replace('_',' ').title()}\n**Party:** {rec.get('party','independent')}\n**Active:** {rec.get('active',True)}\n**Since:** {rec.get('registered_at','?')}",
                        color=discord.Color.green())
        await interaction.response.send_message(embed=e, ephemeral=True)
    
    @elections.command(name="open_contest", description="Create an election contest (general or special)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        office="house or senate",
        category="Category key (autocomplete)",
        seats="Number of seats (≥1). >1 will open a multi-select poll.",
        district="Optional district label (e.g., D1)",
        election_date="YYYY-MM-DD (omit = next general)",
        post_channel="Channel where the poll & notices will be posted",
    )
    @app_commands.autocomplete(category=category_autocomplete)
    async def open_contest(self,
        interaction: discord.Interaction,
        office: str,
        category: str,
        seats: app_commands.Range[int, 1, 25] = 1,
        district: str | None = None,
        election_date: str | None = None,
        post_channel: discord.TextChannel | None = None,
    ):
        if office.lower() not in {"house","senate"}:
            return await interaction.response.send_message("office must be 'house' or 'senate'.", ephemeral=True)

        try:
            eday = (datetime.strptime(election_date, "%Y-%m-%d").date() if election_date
                    else _next_general_election())
        except Exception:
            return await interaction.response.send_message("Bad date format. Use YYYY-MM-DD.", ephemeral=True)

        filing_deadline, cert_deadline = _compute_deadlines(eday)
        cid = _contest_id(office, category, eday, district, seats)
        bucket = _contest_bucket(self.federal_registry, cid)
        if bucket.get("status"):
            return await interaction.response.send_message("Contest already exists.", ephemeral=True)

        bucket.update({
            "id": cid,
            "office": office.lower(),
            "category": category,
            "district": (district or None),
            "seats": int(seats),
            "election_day": eday.isoformat(),
            "filing_deadline": filing_deadline.isoformat(),
            "cert_deadline": cert_deadline.isoformat(),
            "candidates": [],           # [{user_id, display, party, filed_at}]
            "certified": [],            # list of user_ids
            "status": "OPEN",           # OPEN -> FILED -> CERTIFIED -> VOTING -> TALLIED -> CERTIFIED_WINNER
            "post_channel_id": (post_channel.id if post_channel else interaction.channel.id),
            "poll_message_id": None,
            "poll_thread_id": None,
            "results": None,            # {"tally":[(name,votes)...], "total":N, "winners":[...], "closed_at":iso}
        })
        save_federal_registry(self.federal_registry)

        e = discord.Embed(
            title=f"Contest opened — {office.title()} ({category.replace('_',' ').title()})",
            description=f"**Election Day:** {eday.isoformat()}\n**Filing deadline:** {filing_deadline.isoformat()}\n**Ballot cert:** {cert_deadline.isoformat()}\n**Seats:** {seats}" + (f"\n**District:** {district}" if district else ""),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=e, ephemeral=False)

    # ---------------- CANDIDATE FILING ----------------

    @elections.command(name="file_candidate", description="File as a candidate in a scheduled contest (House/Senate).")
    @app_commands.describe(
        contest_id="The contest id (from /elections list or auto_general output)",
        statement="Optional short statement (appears on the ballot, trimmed)",
        party="Political party affiliation (optional)"
    )
    @app_commands.autocomplete(contest_id=elections_contest_autocomplete, party=party_autocomplete)
    async def file_candidate(self, interaction: discord.Interaction, contest_id: str, statement: str | None = None, party: str | None = None):
        await interaction.response.defer(ephemeral=True, thinking=True)

        reg = self.federal_registry
        eroot = _elections_root(reg)
        contests = eroot.get("contests", {})
        c = contests.get(contest_id)
        if not c:
            return await interaction.followup.send("❌ Contest not found.", ephemeral=True)

        # sanity: contest must be scheduled and filing open (or grace)
        filing_deadline = date.fromisoformat(c["filing_deadline"])
        today = datetime.now(UTC).date()
        late = False
        if today > filing_deadline and not _grace_ok(reg, c, "filing"):
            return await interaction.followup.send("❌ Filing deadline has passed.", ephemeral=True)
        if today > filing_deadline:
            late = True  # grace window

        # Category residency check (lightweight)
        cat_key = c.get("category")
        role_id = CITIZENSHIP.get(cat_key)
        if role_id:
            if not any(r.id == role_id for r in interaction.user.roles):
                return await interaction.followup.send(f"❌ You must be a resident of **{cat_key.replace('_',' ').title()}** to file for this contest.", ephemeral=True)

        # Ensure not already in THIS contest (but DO allow filing in other contests)
        cands = c.setdefault("candidates", [])
        if any(str(x.get("user_id")) == str(interaction.user.id) for x in cands):
            return await interaction.followup.send("You’re already filed in this contest.", ephemeral=True)

        # Add candidate
        cands.append({
            "user_id": interaction.user.id,
            "display": interaction.user.display_name,
            "party": (party or "independent"),
            "filed_at": _now_iso(),
            "late": late,
            "statement": (statement or "").strip()[:200],
        })
        save_federal_registry(reg)

        # Public ack in an elections channel if you have one
        try:
            if ELECTIONS_ANNOUNCE_CHANNEL:
                ch = interaction.client.get_channel(ELECTIONS_ANNOUNCE_CHANNEL)
                if ch:
                    await ch.send(f"🗳️ **Candidate filed**: {interaction.user.mention} → `{contest_id}`")
        except Exception:
            pass

        await interaction.followup.send(f"✅ Filed for `{contest_id}`. (Late: {late})", ephemeral=True)

    @elections.command(name="withdraw_candidate", description="Withdraw from a contest before certification.")
    @app_commands.describe(contest_id="Contest to withdraw from")
    async def withdraw_candidate(self, interaction: discord.Interaction, contest_id: str):
        await interaction.response.defer(ephemeral=True)

        reg = self.federal_registry
        contests = _elections_root(reg).get("contests", {})
        c = contests.get(contest_id)
        if not c:
            return await interaction.followup.send("❌ Contest not found.", ephemeral=True)

        # Block withdrawals on/after certification deadline
        cert_deadline = date.fromisoformat(c["cert_deadline"])
        if datetime.now(UTC).date() >= cert_deadline and not _grace_ok(reg, c, "filing"):
            return await interaction.followup.send("❌ Certification is underway/complete; withdrawals are closed.", ephemeral=True)

        orig = len(c.get("candidates", []))
        c["candidates"] = [x for x in c.get("candidates", []) if str(x.get("user_id")) != str(interaction.user.id)]
        if len(c["candidates"]) == orig:
            return await interaction.followup.send("You are not filed in that contest.", ephemeral=True)

        save_federal_registry(reg)
        await interaction.followup.send(f"✅ Withdrawn from `{contest_id}`.", ephemeral=True)


    # ---------------- BALLOT CERTIFICATION ----------------

    @elections.command(name="certify_ballot", description="Publish the certified candidate list")
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    async def certify_ballot(self, interaction: discord.Interaction, contest: str):
        reg = self.federal_registry
        c = _elections_root(reg)["contests"].get(contest)
        if not c:
            return await interaction.response.send_message("Contest not found.", ephemeral=True)
        # gate: Clerk or admin
        if not _has_role_or_admin(interaction.user, CLERK_ROLE_ID):
            return await interaction.response.send_message("Only the Clerk (or admin) may certify.", ephemeral=True)

        today = datetime.now(UTC).date()
        certline = date.fromisoformat(c["cert_deadline"])
        if today > certline and not _grace_ok(self.federal_registry, c, "filing"):
            return await interaction.response.send_message("Certification deadline has passed.", ephemeral=True)


        cands = c.get("candidates", [])
        if not cands:
            return await interaction.response.send_message("No candidates filed.", ephemeral=True)

        c["certified"] = [str(x["user_id"]) for x in cands]
        c["status"] = "CERTIFIED"
        save_federal_registry(reg)

        # publish
        chan = self.bot.get_channel(int(c["post_channel_id"]))
        names = "\n".join(f"• {x['display']} ({x.get('party','independent')})" for x in cands)
        e = discord.Embed(
            title=f"Ballot certified — {contest}",
            description=f"**Candidates:**\n{names}",
            color=discord.Color.gold()
        )
        if chan:
            await chan.send(embed=e)
        await interaction.response.send_message("✅ Ballot certified.", ephemeral=True)

    # ---------------- OPEN POLL ----------------

    @elections.command(name="open_poll", description="Open the election poll")
    @app_commands.describe(contest="Contest", hours="Poll duration hours (default 24)")
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    async def open_poll(self, interaction: discord.Interaction, contest: str, hours: int = DEFAULT_ELECTION_HOURS):
        reg = self.federal_registry
        c = _elections_root(reg)["contests"].get(contest)
        if not c:
            return await interaction.response.send_message("Contest not found.", ephemeral=True)
        if c.get("status") != "CERTIFIED":
            return await interaction.response.send_message("Contest must be CERTIFIED.", ephemeral=True)

        chan = self.bot.get_channel(int(c["post_channel_id"]))
        if not chan:
            return await interaction.response.send_message("Post channel not found.", ephemeral=True)

        # Build answers from certified candidates
        cert_ids = set(c.get("certified") or [])
        roster = [x for x in c.get("candidates", []) if str(x["user_id"]) in cert_ids]
        if not roster:
            return await interaction.response.send_message("No certified candidates to place on ballot.", ephemeral=True)

        q = f"{c['office'].title()} — {c['category'].replace('_',' ').title()}" + (f" ({c['district']})" if c.get("district") else "")
        p = discord.Poll(
            question=q,
            duration=timedelta(hours=hours),
            multiple=(int(c.get("seats",1)) > 1)
        )
        for cand in roster:
            p.add_answer(text=f"{cand['display']} ({cand.get('party','independent')})")

        msg = await chan.send(content="🗳️ **Election Poll Open**", poll=p)

        c["poll_message_id"] = msg.id
        c["status"] = "VOTING"
        ballot_map = {}
        for cand in roster:
            label = f"{cand['display']} ({cand.get('party','independent')})"
            p.add_answer(text=label)
            ballot_map[label] = cand['user_id']

        c.setdefault('results', {})['ballot_map'] = ballot_map
        save_federal_registry(reg)

        await interaction.response.send_message(f"✅ Poll opened: {msg.jump_url}", ephemeral=True)

    # ---------------- CLOSE & TALLY ----------------

    @elections.command(name="close_poll", description="Close an election poll and tally")
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    async def close_poll(self, interaction: discord.Interaction, contest: str):
        reg = self.federal_registry
        c = _elections_root(reg)["contests"].get(contest)
        if not c:
            return await interaction.response.send_message("Contest not found.", ephemeral=True)
        if c.get("status") != "VOTING":
            return await interaction.response.send_message("Contest is not in VOTING.", ephemeral=True)

        chan = self.bot.get_channel(int(c["post_channel_id"]))
        msg = await chan.fetch_message(int(c["poll_message_id"]))
        try:
            await msg.end_poll()
        except Exception:
            pass
        try:
            msg = await chan.fetch_message(int(c["poll_message_id"]))
        except Exception:
            pass

        tally = _poll_tally_from_message(msg)
        total = sum(v for _, v in tally)
        # winners = top N by votes (N = seats)
        seats = int(c.get("seats",1))
        winners = [name for name, _ in sorted(tally, key=lambda kv: kv[1], reverse=True)[:seats]]

        c["results"] = {
            "tally": tally,
            "total": total,
            "winners": winners,
            "closed_at": _now_iso()
        }
        c["status"] = "TALLIED"
        ballot_map = (c.get('results') or {}).get('ballot_map', {})
        winner_ids = [ballot_map.get(name) for name in winners if ballot_map.get(name)]
        c['results']['winners_user_ids'] = winner_ids
        save_federal_registry(reg)


        # Publish an audit embed
        lines = []
        for name, votes in tally:
            pct = _percent(votes, total)
            lines.append(f"{name} — **{votes}** ({pct:.1f}%)")
        e = discord.Embed(
            title=f"Unofficial Results — {contest}",
            description="\n".join(lines) or "No ballots cast.",
            color=discord.Color.green()
        )
        e.set_footer(text=f"Ballots: {total} • Seats: {seats}")
        await chan.send(embed=e)
        await interaction.response.send_message("✅ Tallied.", ephemeral=True)

    # ---------------- RECOUNT ----------------

    @elections.command(name="finalize", description="Certify winners and (optionally) assign roles")
    @app_commands.autocomplete(contest_id=elections_contest_autocomplete)
    async def elections_finalize(self, interaction: discord.Interaction, contest_id: str):
        reg = self.federal_registry
        c = _elections_root(reg)["contests"].get(contest_id)
        if not c:
            return await interaction.response.send_message("Contest not found.", ephemeral=True)
        if c.get("status") not in {"TALLIED"}:
            return await interaction.response.send_message("Contest isn’t ready to finalize.", ephemeral=True)

        winner_ids = (c.get("results") or {}).get("winners_user_ids") or []
        if not winner_ids:
            return await interaction.response.send_message("No winners recorded yet.", ephemeral=True)

        # (Optional) assign chamber roles here if you keep SENATOR_ROLE_ID / REPRESENTATIVE_ROLE_ID constants
        # for uid in winner_ids: ... add roles safely

        c["status"] = "CERTIFIED_WINNER"
        save_federal_registry(reg)
        await interaction.response.send_message(f"✅ Finalized `{contest_id}` with {len(winner_ids)} winner(s).", ephemeral=False)

    @elections.command(name="recount_request", description="Request a recount (≤1.0% and within 48h)")
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    async def recount_request(self, interaction: discord.Interaction, contest: str):
        reg = self.federal_registry
        c = _elections_root(reg)["contests"].get(contest)
        if not c or c.get("status") != "TALLIED":
            return await interaction.response.send_message("Contest not found or not tallied.", ephemeral=True)

        # must be a candidate in the contest
        cand_names = [x["display"] for x in c.get("candidates", [])]
        if interaction.user.display_name not in cand_names:
            return await interaction.response.send_message("Only candidates may request a recount.", ephemeral=True)

        # time window 48h from close
        closed_at = datetime.fromisoformat(c["results"]["closed_at"])
        if datetime.now(UTC) > (closed_at + timedelta(hours=48)):
            return await interaction.response.send_message("Recount request window (48h) has expired.", ephemeral=True)

        # ≤1.0% margin check
        tally = c["results"]["tally"]
        ok, margin = _top_two_margin_one_percent(tally)
        if not ok:
            return await interaction.response.send_message(f"Margin is {margin:.2f}%, which exceeds 1.0%.", ephemeral=True)

        c["recount_requested_by"] = interaction.user.id
        c["recount_requested_at"] = _now_iso()
        c["status"] = "RECOUNT_REQUESTED"
        save_federal_registry(reg)

        chan = self.bot.get_channel(int(c["post_channel_id"]))
        await chan.send(f"🔁 Recount requested for **{contest}** (margin {margin:.2f}%).")
        await interaction.response.send_message("✅ Recount requested. FEC will respond.", ephemeral=True)

    @elections.command(name="recount_set", description="FEC/Administrator sets the recount outcome")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    @app_commands.choices(outcome=[
        app_commands.Choice(name="Uphold tally", value="uphold"),
        app_commands.Choice(name="Reverse order", value="reverse"),
    ])
    async def recount_set(self, interaction: discord.Interaction, contest: str, outcome: str):
        if not (_has_role_or_admin(interaction.user, FEC_ROLE_ID)):
            return await interaction.response.send_message("Only FEC or admins may set recount outcome.", ephemeral=True)
        reg = self.federal_registry
        c = _elections_root(reg)["contests"].get(contest)
        if not c or c.get("status") != "RECOUNT_REQUESTED":
            return await interaction.response.send_message("No recount pending for that contest.", ephemeral=True)

        # simple model: uphold keeps winners; reverse flips top two
        winners = list(c["results"]["winners"])
        if outcome == "reverse" and len(winners) >= 2:
            winners[0], winners[1] = winners[1], winners[0]
        c["results"]["recount_outcome"] = outcome
        c["results"]["final_winners"] = winners
        c["status"] = "CERTIFIED_WINNER"
        save_federal_registry(reg)

        chan = self.bot.get_channel(int(c["post_channel_id"]))
        await chan.send(f"📜 **Recount {outcome}** — Final winners: " + ", ".join(winners))
        await interaction.response.send_message("✅ Recount outcome recorded.", ephemeral=True)

    # ---------------- (Stub) REAPPORTIONMENT ----------------

    @elections.command(name="apportion_preview", description="(Stub) Preview a House apportionment from Category counts")
    @app_commands.describe(house_size="Total House seats", counts_json="JSON: {category: population, ...}")
    async def apportion_preview(self, interaction: discord.Interaction, house_size: int, counts_json: str):
        """
        Minimal preview (no stateful changes). We can wire equal-proportions fully later.
        """
        import json
        try:
            counts = json.loads(counts_json)
            if not isinstance(counts, dict) or not counts:
                raise ValueError
        except Exception:
            return await interaction.response.send_message("Bad JSON. Expect: {\"commons\": 5, \"gaming\": 3, ...}", ephemeral=True)

        # equal proportions divisor method (quick and dirty)
        seats = {k: 1 for k in counts}  # min 1
        # generate priority numbers
        priorities = []
        for cat, pop in counts.items():
            for n in range(2, house_size * 3):  # generous upper bound
                priorities.append((cat, pop / math.sqrt(n*(n-1))))
        priorities.sort(key=lambda x: x[1], reverse=True)

        total = len(seats)
        i = 0
        while total < house_size and i < len(priorities):
            cat, _ = priorities[i]
            seats[cat] = seats.get(cat, 1) + 1
            total += 1
            i += 1

        # reply
        lines = [f"{k.replace('_',' ').title()}: {v}" for k, v in sorted(seats.items())]
        await interaction.response.send_message(
            embed=discord.Embed(title=f"Apportionment preview (House={house_size})",
                                description="\n".join(lines),
                                color=discord.Color.teal()),
            ephemeral=True
        )
    


    @elections.command(name="registration_freeze", description="Set/clear the global registration freeze date (YYYY-MM-DD).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(when="Date like 2025-10-28. Omit to clear.")
    async def registration_freeze(self, interaction: discord.Interaction, when: str | None = None):
        reg = self.federal_registry
        eroot = _elections_root(reg)
        if when:
            # validate
            try:
                date.fromisoformat(when)
            except Exception:
                return await interaction.response.send_message("Bad date. Use YYYY-MM-DD.", ephemeral=True)
            eroot["registration_freeze"] = when
            note = f"Freeze set to {when}."
        else:
            eroot.pop("registration_freeze", None)
            note = "Registration freeze cleared."
        save_federal_registry(reg)
        await interaction.response.send_message(f"✅ {note}", ephemeral=True)


    @elections.command(name="grace_once", description="Set a one-time late window (global or per contest).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        through="Last day grace applies (YYYY-MM-DD)",
        allow_registration="Allow late voter registration?",
        allow_filing="Allow late candidate filing?",
        note="Optional public note",
        contest="(Optional) limit to one contest ID; omit for global"
    )
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    async def grace_once(self,
        interaction: discord.Interaction,
        through: str,
        allow_registration: bool = True,
        allow_filing: bool = True,
        note: str | None = None,
        contest: str | None = None,
    ):
        try:
            date.fromisoformat(through)
        except Exception:
            return await interaction.response.send_message("Bad date. Use YYYY-MM-DD.", ephemeral=True)

        reg = self.federal_registry
        if contest:
            contests = _elections_root(reg)["contests"]
            c = contests.get(contest)
            if not c:
                return await interaction.response.send_message("Contest not found.", ephemeral=True)
            c["grace"] = {
                "enabled": True,
                "through": through,
                "allow_registration": allow_registration,
                "allow_filing": allow_filing,
                "note": (note or None),
            }
            who = f"contest **{contest}**"
        else:
            gb = _grace_bucket(reg)
            gb.update({
                "enabled": True,
                "through": through,
                "allow_registration": allow_registration,
                "allow_filing": allow_filing,
                "note": (note or None),
            })
            who = "GLOBAL"

        save_federal_registry(reg)
        await interaction.response.send_message(
            f"✅ Grace enabled ({who}) through {through} • "
            f"registration={allow_registration} filing={allow_filing}.", ephemeral=True
        )

    @elections.command(name="grace_clear", description="Disable the one-time late window.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(contest="(Optional) contest to clear; omit for global")
    @app_commands.autocomplete(contest=elections_contest_autocomplete)
    async def grace_clear(self, interaction: discord.Interaction, contest: str | None = None):
        reg = self.federal_registry
        if contest:
            contests = _elections_root(reg)["contests"]
            c = contests.get(contest)
            if not c:
                return await interaction.response.send_message("Contest not found.", ephemeral=True)
            c.pop("grace", None)
            who = f"contest **{contest}**"
        else:
            _grace_bucket(reg).update({"enabled": False})
            who = "GLOBAL"
        save_federal_registry(reg)
        await interaction.response.send_message(f"✅ Grace cleared for {who}.", ephemeral=True)


    @elections.command(name="auto_general", description="Auto-create the November general election contests from current citizenship rolls.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        house_size="Total House seats (default 7)",
        exclude_senate="Comma-separated category keys to exclude from Senate (e.g., 'dp')",
        grace_through="YYYY-MM-DD to allow late filing/registration (default: day after Election Day)"
    )
    async def auto_general(
        self,
        interaction: discord.Interaction,
        house_size: int = 7,
        exclude_senate: str | None = "dp",
        grace_through: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("Must be used in a server.", ephemeral=True)

        # 1) Determine Election Day & related dates
        e_day = _next_federal_election_day()
        filing_deadline = e_day - timedelta(days=21)
        cert_deadline   = e_day - timedelta(days=14)
        grace_default   = (e_day + timedelta(days=1)).isoformat()
        grace_until     = grace_through or grace_default

        # 2) Count current citizenship by Category
        pops = _count_category_citizens(guild, CITIZENSHIP)

        # 3) Apportion House seats (min 1 each, total house_size)
        seats = _equal_proportions_apportion(pops, house_size)

        # 4) Build/merge contests
        reg = self.federal_registry
        eroot = _elections_root(reg)
        contests = eroot.setdefault("contests", {})

        # ID prefix, e.g., "2025-11-general"
        key_prefix = f"{e_day.year}-11-general"

        # House contests (at-large until districts exist, per §2(e),(h))
        for cat_key, seat_count in seats.items():
            for idx in range(1, seat_count + 1):
                cid = f"{key_prefix}-house-{cat_key}-seat-{idx}"
                contests[cid] = {
                    "kind": "house",
                    "category": cat_key,
                    "district": None,              # at-large
                    "seat_index": idx,
                    "election_day": e_day.isoformat(),
                    "filing_deadline": filing_deadline.isoformat(),
                    "cert_deadline": cert_deadline.isoformat(),
                    "candidates": [],
                    "status": "SCHEDULED",
                }

        # Senate contests (one per Category, but exclude e.g. dp)
        excluded = set((exclude_senate or "").replace(" ", "").split(",")) if exclude_senate else set()
        for cat_key in CITIZENSHIP.keys():
            if cat_key in excluded:
                continue
            cid = f"{key_prefix}-senate-{cat_key}"
            contests[cid] = {
                "kind": "senate",
                "category": cat_key,
                "election_day": e_day.isoformat(),
                "filing_deadline": filing_deadline.isoformat(),
                "cert_deadline": cert_deadline.isoformat(),
                "candidates": [],
                "status": "SCHEDULED",
                "term_begins": date(e_day.year+1, 1, 3).isoformat(),  # Jan 3 per your §1
            }

        # 5) One-time global grace for this cycle (late filings + registrations)
        gb = _grace_bucket(reg)
        gb.update({
            "enabled": True,
            "through": grace_until,            # e.g., 2025-11-05
            "allow_registration": True,
            "allow_filing": True,
            "note": f"One-time 2025 general election grace (set {datetime.now(UTC).date().isoformat()})",
        })

        # 6) Persist
        eroot["contests"] = contests
        # (Optional) publish the President’s apportionment “statement” per §2(a),(g)
        eroot["apportionment"] = {
            "election_year": e_day.year,
            "house_size": house_size,
            "population": pops,
            "seats": seats,
            "published_by": interaction.user.id,
            "published_at": _now_iso(),
        }

        save_federal_registry(reg)

        # 7) Announce
        # Summary text: who got how many House seats + which Categories have Senate races
        house_lines = []
        for k in sorted(seats.keys()):
            house_lines.append(f"• {k.replace('_',' ').title()}: {seats[k]} seat(s) — pop {pops.get(k,0)}")
        senate_lines = [k for k in CITIZENSHIP.keys() if k not in excluded]
        emb = discord.Embed(
            title=f"General Election Setup — {e_day.isoformat()}",
            description="Contests created and deadlines set.",
            color=discord.Color.blurple()
        )
        emb.add_field(name="House apportionment (equal proportions, min 1)", value="\n".join(house_lines), inline=False)
        emb.add_field(name="Senate contests", value=", ".join(x.replace('_',' ').title() for x in senate_lines) or "—", inline=False)
        emb.add_field(name="Deadlines", value=f"Filing: **{filing_deadline.isoformat()}**\nCertification: **{cert_deadline.isoformat()}**", inline=True)
        emb.add_field(name="Grace window", value=f"Through **{grace_until}** (registration & filing)", inline=True)

        if ELECTIONS_ANNOUNCE_CHANNEL:
            ch = interaction.client.get_channel(ELECTIONS_ANNOUNCE_CHANNEL)
            if ch:
                try: await ch.send(embed=emb)
                except Exception: pass

        await interaction.followup.send(embed=emb, ephemeral=True)

    @commands.command(name="residency_gate_apply", aliases=["rga"])
    @commands.is_owner()
    async def residency_gate_apply(self, ctx: commands.Context):
        guild = ctx.guild
        pend = guild.get_role(PENDING_RESIDENT)
        if not pend:
            return await ctx.reply("Pending Resident role not found.")

        touched = 0

        # 1) Deny everywhere (per-channel), we’ll whitelist specific IDs next.
        for ch in guild.channels:
            try:
                await ch.set_permissions(pend, view_channel=False, send_messages=False)
                touched += 1
            except Exception:
                pass

        # 2) Whitelist must-see channels (rules / waving / intake parent, etc.)
        for ch_id in PENDING_ALLOWED_CHANNELS:
            ch = guild.get_channel(ch_id)
            if not ch:
                continue
            try:
                await ch.set_permissions(
                    pend,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
                touched += 1
            except Exception:
                pass

        await ctx.reply(f"✅ Applied residency gate to {touched} places. Review anything custom and you’re done.")

    @citizenship.command(name="exam_begin", description="Start the citizenship exam in a private thread")
    async def exam_begin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        reg = self.federal_registry
        exams = _exam_bucket(reg)
        uid = str(interaction.user.id)

        # Cooldown
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        rec = exams.get(uid)
        if rec and rec.get("last_attempt_at"):
            try:
                last = datetime.fromisoformat(rec["last_attempt_at"])
                if now < last + timedelta(days=CITIZENSHIP_EXAM_COOLDOWN_DAYS):
                    rem = (last + timedelta(days=CITIZENSHIP_EXAM_COOLDOWN_DAYS) - now).days + 1
                    return await interaction.followup.send(f"⏳ You can retake the exam in ~{rem} day(s).", ephemeral=True)
            except Exception:
                pass

        # Find/create the exam thread under WAVING and add the user
        parent = self.bot.get_channel(WAVING)
        if not parent:
            return await interaction.followup.send("Waving channel not found.", ephemeral=True)
        if str(getattr(parent, "type", "")) != "text":
            return await interaction.followup.send("Waving must be a text channel.", ephemeral=True)

        thread = None
        try:
            thread = await parent.create_thread(
                name=f"Citizenship Exam — {interaction.user.display_name}",
                type=discord.ChannelType.private_thread,
                invitable=False,
                auto_archive_duration=1440
            )
            await thread.add_user(interaction.user)
        except Exception as e:
            return await interaction.followup.send(f"Could not open exam thread: {e}", ephemeral=True)

        # Build exam
        paper = _build_exam_paper(reg, CITIZENSHIP_EXAM_LEN)
        exams[uid] = {
            "exam_id": f"x-{interaction.user.id}-{int(now.timestamp())}",
            "started_at": _now_iso(),
            "last_attempt_at": _now_iso(),
            "paper": paper,        # store the shuffled paper
            "answers": [],         # user selections (0..3)
            "score": None,
            "passed": None,
            "thread_id": thread.id,
        }
        save_federal_registry(reg)


        await thread.send(
            f"{interaction.user.mention} **Citizenship Exam** begins now. "
            f"Answer by clicking A/B/C/D on each question. Passing: **{CITIZENSHIP_PASSING}%**.",
            allowed_mentions=discord.AllowedMentions(users=True)
        )
        # Post first question
        await self._exam_post_question(thread, interaction.user, exams[uid], 0)
        await interaction.followup.send(f"📘 Exam thread created: {thread.mention}", ephemeral=True)

    async def _exam_post_question(self, thread: discord.Thread, user: discord.Member, rec: dict, idx: int):
        q = rec["paper"][idx]
        choices = q["choices"]
        view = ExamQuestionView(self, user.id, rec["exam_id"], idx, len(rec["paper"]), choices)
        letters = ["A", "B", "C", "D"][:len(choices)]
        text = f"**Q{idx+1}/{len(rec['paper'])}.** {q['text']}\n" + "\n".join(f"{letters[i]}. {c}" for i, c in enumerate(choices))
        await thread.send(text, view=view)

    async def _exam_record_and_advance(self, interaction: discord.Interaction, choice_idx: int):
        reg = self.federal_registry
        exams = _exam_bucket(reg)
        uid = str(interaction.user.id)
        rec = exams.get(uid)
        if not rec or rec.get("passed") is not None:
            return await interaction.response.send_message("No active exam.", ephemeral=True)

        answers = rec.setdefault("answers", [])
        current_idx = len(answers)
        answers.append(choice_idx)
        save_federal_registry(reg)

        thread = interaction.channel if isinstance(interaction.channel, discord.Thread) else None
        if current_idx + 1 < len(rec["paper"]):
            await interaction.response.defer(ephemeral=True)
            await self._exam_post_question(thread, interaction.user, rec, current_idx + 1)
        else:
            # grade using the per-question correct_idx
            paper = rec["paper"]
            correct = sum(1 for i, ans in enumerate(answers) if i < len(paper) and ans == paper[i]["correct_idx"])
            total = len(paper)
            pct = int(round((correct / total) * 100))
            passed = pct >= CITIZENSHIP_PASSING
            rec["score"] = pct
            rec["passed"] = passed
            rec["completed_at"] = _now_iso()
            save_federal_registry(reg)

            await interaction.response.defer(ephemeral=True)
            color = "🟩" if passed else "🟥"
            msg = f"{color} **Exam complete:** {correct}/{total} — **{pct}%**. " + ("✅ You passed!" if passed else f"❌ You did not pass. Retry in {CITIZENSHIP_EXAM_COOLDOWN_DAYS} days.")
            try:
                await thread.send(f"{interaction.user.mention} {msg}", allowed_mentions=discord.AllowedMentions(users=True))
            except Exception:
                pass
            st = _get_state_channel(self.bot, interaction.guild)
            if st:
                try: await st.send(f"🧪 Exam result — {interaction.user.mention}: {pct}% ({'pass' if passed else 'fail'})")
                except Exception: pass


    @citizenship.command(name="exam_status", description="See your citizenship exam status/cooldown")
    async def exam_status(self, interaction: discord.Interaction):
        reg = self.federal_registry
        rec = _exam_bucket(reg).get(str(interaction.user.id))
        if not rec:
            return await interaction.response.send_message("No exam on record.", ephemeral=True)
        lines = [f"Started: {rec.get('started_at','—')}", f"Completed: {rec.get('completed_at','—')}", f"Score: {rec.get('score','—')}", f"Passed: {rec.get('passed','—')}"]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


    @registry.command(
        name="upload_fixed",
        description="Upload a corrected registry JSON and swap it in (validates + backs up current)."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        file="Attach a UTF-8 .json of the FULL registry",
        commit="If false, only validate and report without replacing"
    )
    async def registry_upload_fixed(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        commit: bool = True,
    ):
        global REGISTRY_SUSPENDED

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Basic sanity
        if not file:
            return await interaction.followup.send("❌ No file attached.", ephemeral=True)
        if file.size and file.size > 10_000_000:
            return await interaction.followup.send("❌ File too large (>10MB).", ephemeral=True)

        # Read & decode
        try:
            raw = await file.read()
        except Exception as e:
            return await interaction.followup.send(f"❌ Couldn’t read attachment: {e}", ephemeral=True)
        try:
            text = raw.decode("utf-8-sig")
        except Exception:
            return await interaction.followup.send("❌ File is not valid UTF-8.", ephemeral=True)

        # Parse JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return await interaction.followup.send(
                f"❌ JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}",
                ephemeral=True
            )

        # Normalize schema (keeps bad keys from bricking later)
        data = _ensure_registry_schema(data)

        # Dry-run?
        if not commit:
            keys = ", ".join(sorted(data.keys())[:12])
            more = "…" if len(data.keys()) > 12 else ""
            return await interaction.followup.send(
                f"✅ JSON is valid. Top-level keys: {keys}{more}\n"
                "Re-run with `commit: true` to replace the live registry.",
                ephemeral=True
            )

        # Commit safely
        path = FED_REGISTRY_FILE
        base = Path(path)
        ts = int(time.time())

        # Enter suspend so nothing else writes mid-swap
        REGISTRY_SUSPENDED = True

        # Backup current file (even if corrupt)
        try:
            if base.exists():
                shutil.copy2(base, base.with_suffix(f".preupload-{ts}.json"))
        except Exception:
            pass  # best effort

        # Atomic write of the new data
        try:
            # if you already have save_federal_registry() with atomic replace, use it:
            save_federal_registry(data)
        except Exception as e:
            REGISTRY_SUSPENDED = getattr(self, "registry_readonly", False)
            return await interaction.followup.send(f"❌ Failed to write new registry: {e}", ephemeral=True)

        # Reload into memory & exit panic
        try:
            with open(base, "r", encoding="utf-8") as f:
                self.federal_registry = json.load(f)
        except Exception as e:
            return await interaction.followup.send(
                f"⚠️ Wrote file, but reload failed: {e}\n"
                f"Registry on disk should be OK; consider `/government reload`.",
                ephemeral=True
            )

        self.registry_readonly = False
        REGISTRY_SUSPENDED = False

        # (Re)start tasks if you paused them in panic mode
        try:
            if hasattr(self, "bill_poll_sweeper") and not self.bill_poll_sweeper.is_running():
                self.bill_poll_sweeper.start()
            if hasattr(self, "bill_status_ticker") and not self.bill_status_ticker.is_running():
                self.bill_status_ticker.start()
        except Exception:
            pass

        await interaction.followup.send(
            "✅ Uploaded and swapped in the fixed registry.\n"
            "A backup of the previous file was saved alongside as `.preupload-<timestamp>.json`.\n"
            "Autosaves & tasks are enabled again.",
            ephemeral=True
        )


    @registry.command(
        name="dump",
        description="Send the raw federal registry JSON file(s) as attachments (read-only)."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        which="Which file to dump: live / bak / salvaged / all"
    )
    @app_commands.choices(which=[
        app_commands.Choice(name="Live (federal_registry.json)", value="live"),
        app_commands.Choice(name="Backup (.bak)", value="bak"),
        app_commands.Choice(name="Salvaged (.salvaged.json)", value="salvaged"),
        app_commands.Choice(name="All", value="all"),
    ])
    async def registry_dump(self, interaction: discord.Interaction, which: str = "live"):
        await interaction.response.defer(ephemeral=True, thinking=True)

        base = Path(FED_REGISTRY_FILE)
        paths: list[tuple[str, Path]] = []

        if which in ("live", "all"):
            paths.append((base.name, base))
        if which in ("bak", "all"):
            bak = Path(str(base) + ".bak")
            if bak.exists():
                paths.append((bak.name, bak))
        if which in ("salvaged", "all"):
            salv = base.with_suffix(".salvaged.json")
            if salv.exists():
                paths.append((salv.name, salv))

        if not paths:
            return await interaction.followup.send("❌ No matching files found to dump.", ephemeral=True)

        files: list[discord.File] = []
        errors: list[str] = []

        for name, p in paths:
            try:
                data = p.read_bytes()
                files.append(discord.File(io.BytesIO(data), filename=name))
            except Exception as e:
                errors.append(f"{name}: {e}")

        if not files and errors:
            return await interaction.followup.send("❌ " + " | ".join(errors), ephemeral=True)

        msg = "Here you go—download, fix locally, then run `/government registry repair commit:true` to apply."
        if errors:
            msg += "\n\n⚠️ Some files couldn’t be read: " + " | ".join(errors)

        await interaction.followup.send(content=msg, files=files, ephemeral=True)


    
    # --- replace your propose_legislation command with this version ---
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
        summary="(Only when using file) 1-2 sentence summary",
        purpose="(Only when using file) brief purpose statement",
        file="Upload .txt/.docx/.pdf to bypass the modal"
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
        summary: str | None = None,
        purpose: str | None = None,
        file: discord.Attachment | None = None,
    ):
        # chamber inference stays identical to your existing logic
        is_senator = any(r.id == SENATORS for r in interaction.user.roles)
        chamber = "Senate" if is_senator else "House"

        # guard for codification metadata like before
        if (codification or repealing) and (not code_title or not sections):
            return await interaction.response.send_message(
                "Because this is a codification/repeal, `code_title` and `sections` are required. Re-run with those fields.",
                ephemeral=True
            )

        # If no file, run your existing modal path (unchanged)
        if not file:
            modal = LegislativeProposalModal(
                title=title,
                type=type,
                joint=joint,
                chamber=chamber,
                sponsor=interaction.user,
                codification=codification,
                repealing=repealing,
                committee=committee,
                co_sponsors=co_sponsors,
                code_title=code_title,
                sections=sections,
            )
            return await interaction.response.send_modal(modal)

        # Otherwise, parse the file, then store bill with the SAME schema as the modal path
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            body_text = await extract_text_from_attachment(file)
        except Exception as e:
            return await interaction.followup.send(f"❌ Could not read the file: {e}", ephemeral=True)

        reg = self.federal_registry
        bills = ensure_bills_schema(reg)

        bill_id = next_bill_id(reg, chamber)

        co_list = []
        if co_sponsors:
            co_list = [p.strip() for p in str(co_sponsors).split(",") if p.strip()]

        struct = parse_bill_structure(str(body_text))
        has_sections = any(t.get("sections") for t in struct.get("titles", []))

        bill = {
            "id": bill_id,
            "title": title,
            "type": type,                         # "bill" | "resolution"
            "joint": bool(joint),
            "chamber": chamber,                   # "Senate" | "House"
            "sponsor_id": interaction.user.id,
            "co_sponsors": co_list,
            "committee": committee or "",
            "codification": bool(codification),
            "repealing": bool(repealing),
            "code_title": code_title or "",
            "sections": sections or "",
            "summary": (summary or "(summary omitted)"),
            "purpose": (purpose or "(purpose omitted)"),
            "text": str(body_text),
            "structure": struct if has_sections else None,
            "amendments": {},
            "status": "DRAFT",
            "created_at": discord.utils.utcnow().isoformat(),
            "message_id": None,
            "thread_id": None,
        }
        bills["items"][bill_id] = bill
        save_federal_registry(reg)

        kind = "Bill" if type == "bill" else "Resolution"
        joint_prefix = "Joint " if joint else ""
        await interaction.followup.send(
            f"✅ Saved draft {joint_prefix}{kind} **{bill_id}** — “{title}”.",
            ephemeral=True
        )

    @citizenship.command(name="apply", description="Open the citizenship application form")
    async def citizenship_apply(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CitizenshipApplicationModal(self, interaction.user))
    
    @citizenship.command(name="oath", description="Take the citizenship oath (after passing exam)")
    async def citizenship_oath(self, interaction: discord.Interaction):
        # optional guard: exam must be passed
        rec = _exam_bucket(self.federal_registry).get(str(interaction.user.id))
        if not rec or rec.get("passed") is not True:
            return await interaction.response.send_message("You must pass the exam before taking the oath.", ephemeral=True)

        view = OathView(self, interaction.user.id)
        text = (
            "**Oath of Citizenship**\n"
            "Do you solemnly swear to support the Constitution of the Spidey Republic, "
            "to obey its laws and the lawful orders of its courts, and to faithfully "
            "discharge the duties of citizenship?"
        )
        await interaction.response.send_message(text, view=view, ephemeral=True)

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
    
    async def code_section_autocomplete(self, interaction: discord.Interaction, current: str):
        ns = interaction.namespace
        title = getattr(ns, "title", None)
        chap = getattr(ns, "chap", None)
        if title is None or chap is None:
            return []
        sections = self.federal_registry.get("spidey_republic_code", {}).get(str(title), {}).get("chapters", {}).get(str(chap), {}).get("sections", {})
        def _numkey(k: str) -> int:
            digits = "".join(ch for ch in k if ch.isdigit())
            return int(digits) if digits else 10**9

        keys = sorted(sections.keys(), key=_numkey)

        cur = (current or "").lower()
        out = []
        for s in keys:
            short = (sections[s].get("short") or "").strip()
            label = f"{s} — {short}" if short else s
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label[:100], value=s))
            if len(out) >= 25:
                break
        return out

    @registry.command(name="view_code", description="View code sections from a chapter")
    @app_commands.autocomplete(title=code_title_autocomplete, chap=chapter_autocomplete, single_section=code_section_autocomplete, sec_start=code_section_autocomplete, sec_end=code_section_autocomplete)
    @app_commands.describe(
        title="Title key/number (e.g., 28)",
        chap="Chapter number (e.g., 13)",
        single_section="View a single section (e.g., 1291 or § 1291)",
        sec_start="Start at this section (e.g., 1291 or § 1291)",
        sec_end="End at this section (optional)"
    )
    async def view_code(
        self,
        interaction: discord.Interaction,
        title: str,
        chap: str,
        single_section: str | None = None,
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

        if single_section:
            single_num = sec_digits(single_section)
            if single_num == 0:
                return await interaction.response.send_message(f"Couldn’t parse section number from '{single_section}'.", ephemeral=True)
            start_num = end_num = single_num

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
    
    @registry.command(name="code_dump")
    @app_commands.checks.has_permissions(administrator=True)
    async def registry_code_dump(self, interaction: discord.Interaction):
        code = self.federal_registry.get("spidey_republic_code")
        if code is None:
            return await interaction.response.send_message(
                "No `spidey_republic_code` found in the registry.",
                ephemeral=True
            )

        payload = json.dumps(code, indent=4, ensure_ascii=False).encode("utf-8")
        fp = io.BytesIO(payload)

        await interaction.response.send_message(
            file=discord.File(fp, filename="src.json"),
            ephemeral=True  # you can set False if you want it public
        )
            

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

    @commands.command(name="citizenship_for_citizens_only", aliases=["cfco"])
    @commands.is_owner()
    async def citizenship_for_citizens_only(self, ctx: commands.Context):
        """Remove citizenship roles from non-citizens."""
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

        removed = 0
        await ctx.send("Starting citizenship cleanup…")

        for member in guild.members:
            if member.bot:
                continue
            # check if they have any citizenship role
            has_citizenship = any(r.id in CITIZENSHIP_IDS for r in member.roles)
            if not has_citizenship:
                continue

            # check if they have the Citizen role
            is_citizen = any(r.id == CITIZENSHIP_ROLE for r in member.roles)
            if is_citizen:
                continue

            # remove all citizenship roles
            roles_to_remove = [r for r in member.roles if r.id in CITIZENSHIP_IDS]
            try:
                await member.remove_roles(*roles_to_remove, reason="Citizenship for citizens only enforcement")
                removed += 1
                await asyncio.sleep(0.5)  # gentle rate-limit buffer; tune as needed
            except (discord.Forbidden, discord.HTTPException) as e:
                await ctx.send(f"Failed to remove citizenship roles from {member.mention}: {e}")

        await ctx.send(f"Done. Removed citizenship roles from {removed} members.")
    
    @commands.command(name="no_dual_citizenship", aliases=["ndc"])
    @commands.is_owner()
    async def no_dual_citizenship(self, ctx: commands.Context):
        """Ensure no member has more than one citizenship role."""
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

        fixed = 0
        await ctx.send("Starting dual citizenship cleanup…")

        for member in guild.members:
            if member.bot:
                continue
            # find all citizenship roles they have
            roles = [r for r in member.roles if r.id in CITIZENSHIP_IDS]
            role_len = len(roles)
            if role_len <= 1:
                continue  # no dual citizenship

            role_keep = random.randint(0, role_len - 1)
            # keep one, remove the rest
            roles_to_remove = roles[:role_keep] + roles[role_keep+1:]  # keep the one at role_keep index
            try:
                await member.remove_roles(*roles_to_remove, reason="No dual citizenship enforcement")
                await member.send("You held more than one citizenship role, so we have removed the extras. You may reapply for a different citizenship if you wish.\n\n")
                fixed += 1
                await asyncio.sleep(0.5)  # gentle rate-limit buffer; tune as needed
            except (discord.Forbidden, discord.HTTPException) as e:
                await ctx.send(f"Failed to remove citizenship roles from {member.mention}: {e}")

        await ctx.send(f"Done. Fixed dual citizenship for {fixed} members.")
    

    @citizenship.command(name="change_citizenship", description="Move to a different category")
    @app_commands.describe(new_citizenship="The citizenship role to move to")
    @app_commands.checks.has_role(CITIZENSHIP_ROLE)
    @app_commands.choices(new_citizenship=[
        app_commands.Choice(name="Commons", value="commons"),
        app_commands.Choice(name="Gaming", value="gaming"),
        app_commands.Choice(name="Spideyton, District of Parker", value="dp"),
        app_commands.Choice(name="Crazy Times", value="crazy_times"),
        app_commands.Choice(name="User Themed", value="user_themed"),
    ])
    async def change_citizenship(self, interaction: discord.Interaction, new_citizenship: str):
        # Optional global freeze (future election lockout)
        _ensure_citizenship_bucket(self.federal_registry)
        if self.federal_registry.get("election_active"):
            return await interaction.response.send_message(
                "Citizenship changes are temporarily disabled during the election period.",
                ephemeral=True
            )

        user = interaction.user
        # current citizenship roles the member holds (by id)
        current_roles = [r for r in user.roles if r.id in CITIZENSHIP_IDS]
        current_ids  = {r.id for r in current_roles}

        new_role_id = CITIZENSHIP.get(new_citizenship)
        if not new_role_id:
            return await interaction.response.send_message("Unknown citizenship.", ephemeral=True)

        if new_role_id in current_ids:
            return await interaction.response.send_message(
                f"You already have the **{new_citizenship.replace('_',' ').title()}** citizenship.",
                ephemeral=True
            )

        # Cooldown: once every 30 days
        bucket = self.federal_registry.setdefault("recent_citizenship_changes", {})
        last_ts = bucket.get(str(user.id)) or bucket.get(user.id)  # tolerate old key type
        last_dt = _parse_iso(last_ts) if isinstance(last_ts, str) else (last_ts if isinstance(last_ts, datetime) else None)
        if last_dt and (last_dt + timedelta(days=30) > datetime.now(UTC)):
            remaining = (last_dt + timedelta(days=30)) - datetime.now(UTC)
            days = remaining.days
            hours = remaining.seconds // 3600
            return await interaction.response.send_message(
                f"You can change citizenship again in **{days}d {hours}h**.",
                ephemeral=True
            )

        # Apply: remove old citizenship roles first, then add new one
        try:
            # remove any existing citizenship roles
            if current_roles:
                await user.remove_roles(*current_roles, reason="Citizenship change")
            # add the new one
            role = interaction.guild.get_role(new_role_id)
            if not role:
                return await interaction.response.send_message("Target role not found.", ephemeral=True)
            await user.add_roles(role, reason="Citizenship change")
        except (discord.Forbidden, discord.HTTPException) as e:
            return await interaction.response.send_message(f"Failed to change citizenship: {e}", ephemeral=True)

        # Persist cooldown as ISO string with string user-id key
        bucket[str(user.id)] = _now_iso()
        self.federal_registry["recent_citizenship_changes"] = bucket
        save_federal_registry(self.federal_registry)

        await interaction.response.send_message(
            f"✅ Your citizenship is now **{new_citizenship.replace('_',' ').title()}**.",
            ephemeral=True
        )

    @citizenship.command(name="residency_question_add", description="Add a residency question")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(question="The residency question to add")
    async def residency_question_add(self, interaction: discord.Interaction, question: str):
        if interaction.channel.id != STATE_DEPARTMENT_CHANNEL:
            return await interaction.response.send_message(
                "This command can only be used in the State Department channel (FOIA).",
                ephemeral=True
            )
        bank = self.federal_registry.setdefault("residency_questions", [])
        bank.append({
            "question": question,
            "added_by": interaction.user.id,
            "added_at": discord.utils.utcnow().isoformat()
        })
        save_federal_registry(self.federal_registry)
        await interaction.response.send_message(f"Added: {question}", ephemeral=False)

    @citizenship.command(name="residency_question_list", description="List residency questions")
    @app_commands.checks.has_permissions(administrator=True)
    async def residency_question_list(self, interaction: discord.Interaction):
        bank = self.federal_registry.get("residency_questions", [])
        if not bank:
            return await interaction.response.send_message("No residency questions found.", ephemeral=True)
        desc = "\n".join(f"{i+1}. {q['question']}" for i, q in enumerate(bank))
        embed = discord.Embed(title="Residency Questions", description=desc[:4000], color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @citizenship.command(name="residency_question_remove", description="Remove a residency question by its number")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        question_number="The number from the list",
        reason="Reason for removal (audit log)"
    )
    async def residency_question_remove(self, interaction: discord.Interaction, question_number: int, reason: str):
        if interaction.channel.id != STATE_DEPARTMENT_CHANNEL:
            return await interaction.response.send_message(
                "This command can only be used in the State Department channel (FOIA).",
                ephemeral=True
            )
        bank = self.federal_registry.get("residency_questions", [])
        if not bank or not (1 <= question_number <= len(bank)):
            return await interaction.response.send_message("Invalid question number.", ephemeral=True)
        removed = bank.pop(question_number - 1)
        save_federal_registry(self.federal_registry)
        await interaction.response.send_message(
            f"{interaction.user.display_name} removed: {removed['question']}\n\nReason: {reason}",
            ephemeral=False
        )

    async def is_citizen(self, member: discord.Member) -> bool:
        return any(r.id == CITIZENSHIP_ROLE for r in member.roles)

    async def is_resident(self, member: discord.Member) -> bool:
        return any(r.id == RESIDENTS for r in member.roles)

    async def category_citizenship(self, member: discord.Member) -> str | None:
        for key, role_id in CITIZENSHIP.items():
            if any(r.id == role_id for r in member.roles):
                return key
        return None

    async def visa_status(self, member: discord.Member) -> str:
        visas = self.federal_registry.setdefault("visas", {})
        info = visas.get(str(member.id))
        if not info:
            return "No visa record found."
        t = info.get("type", "Unknown")
        issued = info.get("issued", "Unknown")
        expiry = info.get("expiry_date", "Unknown")
        return f"Visa Type: {t}\nIssued On: {issued}\nExpiry Date: {expiry}"

    @citizenship.command(name="my_status", description="View your citizenship status and history")
    async def my_status(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Your Citizenship Status", color=discord.Color.blue())

        citizen = await self.is_citizen(interaction.user)
        resident = await self.is_resident(interaction.user)
        cat = await self.category_citizenship(interaction.user)

        if not citizen and not resident:
            visa_info = await self.visa_status(interaction.user)  # ← await!
            embed.add_field(name="Status", value="Non-citizen resident or visitor.", inline=False)
            embed.add_field(name="Visa Information", value=visa_info[:1024], inline=False)
        else:
            bits = []
            if citizen: bits.append("Citizen")
            if resident: bits.append("Resident")
            embed.add_field(name="Status", value=", ".join(bits), inline=False)
            if cat:
                info = CATEGORIES.get(cat)
                if info:
                    embed.add_field(name="Citizenship Category", value=info["name"], inline=False)

            # Last change (formatted)
            bucket = self.federal_registry.get("recent_citizenship_changes", {})
            last = bucket.get(str(interaction.user.id)) or bucket.get(interaction.user.id)
            dt = _parse_iso(last) if isinstance(last, str) else (last if isinstance(last, datetime) else None)
            if dt:
                embed.add_field(name="Last Citizenship Change", value=dt.strftime("%Y-%m-%d"), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def applicant_autocomplete(self, interaction: discord.Interaction, current: str):
        guild = interaction.guild
        if not guild:
            return []

        cur = (current or "").lower()

        # Prefer role.members over guild.members (lighter & more reliable in autocomplete)
        pending_role   = guild.get_role(PENDING_RESIDENT)
        applicant_role = guild.get_role(CITIZENSHIP_APPLICANT)

        candidates = set()
        if pending_role:
            candidates.update(pending_role.members)
        if applicant_role:
            candidates.update(applicant_role.members)

        # If empty, try to populate cache once
        if not candidates and not guild.chunked:
            try:
                await guild.chunk()  # hydrate member cache
                if pending_role:
                    candidates.update(pending_role.members)
                if applicant_role:
                    candidates.update(applicant_role.members)
            except Exception:
                pass

        out = []
        for m in sorted(candidates, key=lambda x: (x.display_name or x.name).lower()):
            tag = "Pending Resident" if (pending_role and pending_role in m.roles) else "Citizenship Applicant"
            label = f"{m.display_name} ({tag})"
            # match display, username, or global name
            names = [
                (m.display_name or "").lower(),
                (m.name or "").lower(),
                (getattr(m, "global_name", "") or "").lower(),
            ]
            if not cur or any(cur in n for n in names):
                out.append(app_commands.Choice(name=label[:100], value=str(m.id)))
            if len(out) >= 25:
                break

        return out




    @citizenship.command(
        name="immigration_decision",
        description="Approve or deny immigration (resident/citizen) and close the intake thread."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        stage="Which application you’re deciding",
        action="Decision",
        applicant="The applicant",
        category="If approving citizenship, optionally pick a category",
        reason="Optional reason (required for deny/conditional)"
    )
    @app_commands.choices(
        stage=[
            app_commands.Choice(name="Resident", value="resident"),
            app_commands.Choice(name="Citizen", value="citizen"),
        ],
        action=[
            app_commands.Choice(name="Approve", value="approve"),
            app_commands.Choice(name="Deny", value="deny"),
            app_commands.Choice(name="Conditional", value="conditional"),
        ],
        # optional category for citizenship approval
        category=[
            app_commands.Choice(name="Commons", value="commons"),
            app_commands.Choice(name="Gaming", value="gaming"),
            app_commands.Choice(name="Spideyton, District of Parker", value="dp"),
            app_commands.Choice(name="Crazy Times", value="crazy_times"),
            app_commands.Choice(name="User Themed", value="user_themed"),
        ]
    )
    @app_commands.autocomplete(applicant=applicant_autocomplete)
    async def immigration_decision(
        self,
        interaction: discord.Interaction,
        stage: str,
        action: str,
        applicant: str,
        category: str = None,
        reason: str = None,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # require a reason for non-approvals
        if action in ["deny", "conditional"] and not (reason and reason.strip()):
            return await interaction.followup.send("Please provide a reason for deny/conditional.", ephemeral=True)

        member = interaction.guild.get_member(int(applicant))
        if not member:
            return await interaction.followup.send("Applicant not found in the server.", ephemeral=True)
        applicant = member
        guild = interaction.guild
        pend = guild.get_role(PENDING_RESIDENT)
        res  = guild.get_role(RESIDENTS)
        cit  = guild.get_role(CITIZENSHIP_ROLE)
        cit_app = guild.get_role(CITIZENSHIP_APPLICANT)

        # Try to find intake thread for the applicant (created on join)
        intake_map = self.federal_registry.setdefault("residency_threads", {})
        info = (intake_map.get(str(applicant.id)) or {})
        thread_id = info.get("thread_id")
        thread = self.bot.get_channel(int(thread_id)) if thread_id else None

        # Build a note we’ll post to the thread if we can
        decision_line = f"**Decision:** {stage.title()} — {action.title()}"
        if reason:
            decision_line += f"\n**Note:** {reason.strip()}"

        # Perform role changes
        try:
            if stage == "resident":
                if action == "approve":
                    # remove Pending, add Resident
                    to_remove = [pend] if pend and pend in applicant.roles else []
                    to_add = [res] if res and (res not in applicant.roles) else []
                    if to_remove:
                        await applicant.remove_roles(*to_remove, reason="Residency approved")
                    if to_add:
                        await applicant.add_roles(*to_add, reason="Residency approved")

                elif action == "deny":
                    # keep Pending, no additions
                    pass

                elif action == "conditional":
                    # no role swap by default; you can tailor this to add a “Probationary” role if you create one
                    pass

            elif stage == "citizen":
                if action == "approve":
                    # Add Citizen, optionally category; remove Pending if present
                    to_remove = [cit_app] if cit_app and cit_app in applicant.roles else []
                    if to_remove:
                        await applicant.remove_roles(*to_remove, reason="Citizenship approved")
                    changes = []
                    if cit and cit not in applicant.roles:
                        changes.append(cit)
                    if category:
                        role_id = CITIZENSHIP.get(category)
                        r = guild.get_role(role_id) if role_id else None
                        if r and r not in applicant.roles:
                            changes.append(r)
                    if changes:
                        await applicant.add_roles(*changes, reason="Citizenship approved")
                    if pend and pend in applicant.roles:
                        await applicant.remove_roles(pend, reason="Citizenship approved")
                    # (Optionally) ensure Resident too — comment out if you want them mutually exclusive
                    if res and res not in applicant.roles:
                        try:
                            await applicant.add_roles(res, reason="Citizenship approved (base resident)")
                        except Exception:
                            pass

                elif stage == "citizen" and action == "deny":
                    if cit_app and cit_app in applicant.roles:
                        await applicant.remove_roles(cit_app, reason="Citizenship denied")

                    pass

                elif action == "conditional":
                    # no default role change
                    pass

        except (discord.Forbidden, discord.HTTPException) as e:
            return await interaction.followup.send(f"Role update failed: {e}", ephemeral=True)

        # Post & archive intake thread if present (always post the outcome)
        if thread:
            try:
                await thread.send(
                    f"{decision_line}\n\n— decided by {interaction.user.mention}",
                    allowed_mentions=discord.AllowedMentions(roles=False, users=True, everyone=False),
                )
                # Archive/lock on approve/deny; keep open on conditional
                if action in {"approve", "deny"}:
                    await thread.edit(archived=True, locked=True)
            except Exception:
                pass

        # Log to registry for audit
        logs = self.federal_registry.setdefault("immigration_actions", [])
        logs.append({
            "ts": _now_iso(),
            "moderator_id": interaction.user.id,
            "applicant_id": applicant.id,
            "stage": stage,
            "action": action,
            "category": (category or None),
            "reason": (reason.strip() if reason else None),
            "thread_id": (int(thread.id) if thread else None),
        })
        save_federal_registry(self.federal_registry)

        # Ack
        human = f"{stage.title()} {action.title()}"
        extra = f" (category: {category})" if (stage == "citizen" and action == "approve" and category) else ""
        state_channel = await interaction.guild.fetch_channel(STATE_DEPARTMENT_CHANNEL)
        if state_channel:
            await state_channel.send(f"{applicant.mention} has been processed: {human}{extra}.\n\n— decided by {interaction.user.mention}{' with reason: ' + reason if reason else ''}")
        await interaction.followup.send(f"✅ {applicant.mention}: {human}{extra}.", ephemeral=True)
        if action in {"deny", "conditional"} and stage == "resident":
            await member.send(f"Your application to join the Spidey Republic has been {action} for the following reasons:\n\n{reason}\n\nIf you have questions, please contact the State Department.")
            if action == "deny":
                await member.kick(reason="Citizenship application denied/conditional")
        else:
            await member.send(f"Congratulations! Your application to join the Spidey Republic has been {action}ed as a {stage}.\n\nWelcome!")



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
        cat_key = category
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
        article="Article (Arabic input)",
        amendment="Amendment (Arabic input)",
        section="Section number (Arabic)",
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

        style_val = (style if style else "irl")
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
        out.reverse() # shows most recent first
        return (out[:25])

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

        # Meta
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

        await interaction.response.send_message(embed=meta, ephemeral=False)

        raw_text = b.get("text") or ""
        if not raw_text.strip():
            return

        if len(raw_text) <= 4000:
            # single embed; bold headings with a 4000 budget
            body_txt = _bold_headings_single(raw_text).strip()
            if body_txt:
                e = discord.Embed(
                    title=f"{bill_id} — Text",
                    description=body_txt,
                    color=discord.Color.blurple()
                )
                await interaction.followup.send(embed=e, allowed_mentions=discord.AllowedMentions.none())
            return

        # long path: create a thread and post chunked messages
        # first, get the meta message we just sent
        try:
            meta_msg = await interaction.original_response()
        except Exception:
            meta_msg = None
        if not meta_msg:
            meta_msg = await interaction.followup.send(content=f"**{bill_id} — Full Text** (thread)", wait=True)

        thread = await meta_msg.create_thread(name=f"{bill_id} — Text")

        # bold headings across the **entire** body, then chunk to ≤2000 char messages
        # use the heading-preserving chunker with a big chunk size to get one big string
        full_bold = "".join(_bold_headings_preserve(raw_text, chunk_size=10**9))
        CHUNK = 1900
        parts = [full_bold[i:i+CHUNK] for i in range(0, len(full_bold), CHUNK)]

        await thread.send(
            f"Posting full text in **{len(parts)}** parts…",
            allowed_mentions=discord.AllowedMentions.none()
        )
        for i, part in enumerate(parts, start=1):
            await thread.send(
                content=f"*Part {i}/{len(parts)}*\n{part}",
                allowed_mentions=discord.AllowedMentions.none()
            )



    @legislature.command(name="docket", description="List active bills/resolutions by chamber")
    @app_commands.choices(chamber=[
        app_commands.Choice(name="Senate", value="Senate"),
        app_commands.Choice(name="House", value="House"),
    ])
    async def docket(self, interaction: discord.Interaction, chamber: str):
        items = self.federal_registry.get("bills", {}).get("items", {})
        # show DRAFT/INTRODUCED/IN_COMMITTEE/FLOOR; hide PASSED/FAILED/ENACTED by default
        active = [b for b in items.values() if b.get("chamber")==chamber and b.get("status") in {"DRAFT","INTRODUCED","IN_COMMITTEE","FLOOR"}]
        if not active:
            return await interaction.response.send_message(f"No active items in the {chamber}.", ephemeral=True)

        active.sort(key=lambda x: x["id"])
        desc = []
        for b in active[:15]:
            kind = "Bill" if b["type"] == "bill" else "Resolution"
            joint = " (Joint)" if b.get("joint") else ""
            desc.append(f"**{b['id']}** — {kind}{joint}: {b.get('title','')}  ·  *{b.get('status')}*")
        embed = discord.Embed(title=f"{chamber} Docket", description="\n".join(desc), color=discord.Color.purple())
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
        if op in {"replace", "delete", "insert_after"} and (not t_no or not s_no):
            return await interaction.response.send_message(
                "Target must be a section like **T1.S2** for this operation.", ephemeral=True
            )
        if op == "insert_end" and not t_no:
            return await interaction.response.send_message(
                "For **insert_end**, target must be a title like **T1**.", ephemeral=True
            )

        # fetch nodes (for ops that need an existing section)
        tnode = snode = None
        if s_no is not None:
            tnode, snode = _find_section(struct, t_no, s_no)
            if op != "insert_end" and not snode:
                return await interaction.response.send_message("Target section not found.", ephemeral=True)

        # validate new content where required
        if op in {"replace", "insert_after", "insert_end"}:
            if not body or not body.strip():
                return await interaction.response.send_message("Body is required for this operation.", ephemeral=True)

        # capture old text for preview/history (when applicable)
        old_heading = snode.get("heading") if snode else ""
        old_body = snode.get("body") if snode else ""

        # build amendment record (no mutations yet)
        amend_id = _next_amend_id(bill)
        amend = {
            "id": amend_id,
            "op": op,
            "target_id": f"T{t_no}" + (f".S{s_no}" if s_no is not None else ""),
            "title_no": t_no if op == "insert_end" else None,
            "new_heading": (section_heading or "").strip() if op in {"replace","insert_after","insert_end"} else "",
            "new_body": (body or "").strip() if op in {"replace","insert_after","insert_end"} else "",
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
        if op == "replace":
            ud = _mkdiff(old_body, amend["new_body"], ctx=3)
            preview = f"```diff\n{ud[:3500]}\n```" if ud else "(no textual changes)"
        elif op == "insert_after":
            preview = (
                f"Insert **after** T{t_no}.S{s_no}\n"
                + (f"**Heading:** {amend['new_heading']}\n\n" if amend['new_heading'] else "")
                + amend["new_body"][:1800]
            )
        elif op == "insert_end":
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
        if op == "replace" and len(preview) < 3900:
            embed.description += "\n\n" + preview
        else:
            embed.add_field(name="Preview", value=preview[:1024] if op != "replace" else preview[:1024], inline=False)

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
        reg = self.federal_registry
        committees = _get_committees_root(reg)

        ns = interaction.namespace
        chamber = getattr(ns, "chamber", None)
        # FIX: actually unwrap if it's a Choice
        if isinstance(chamber, app_commands.Choice):
            chamber = chamber.value
        if chamber not in {"senate", "house", "joint"}:
            return []

        cur = (current or "").lower()
        out: list[app_commands.Choice[str]] = []
        bucket = committees.get(chamber, {})

        for key, data in sorted(bucket.items(), key=lambda kv: kv[0]):
            label = (data.get("name") or key.replace("_", " ").title()).strip()
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label, value=key))
            subs = data.get("sub_committees") or {}
            for sk, sv in sorted(subs.items(), key=lambda kv: kv[0]):
                slabel = (sv.get("name") or sk.replace("_", " ").title()).strip()
                full = f"{label} → {slabel}"
                if not cur or cur in full.lower():
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
        bucket = committees.get(chamber, {})

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
            tz = "America/Los_Angeles"

        reg = self.federal_registry
        parent, node = _resolve_committee_node(reg, chamber, name)
        if not node:
            return await interaction.response.send_message("Committee not found.", ephemeral=True)

        if not (_user_is_committee_chair(interaction.guild, interaction.user, node) or _user_has_leadership_override(interaction.user)):
            return await interaction.response.send_message("Only the committee chair (or leadership) may schedule hearings.", ephemeral=True)

        dt_local = _build_aware_dt(date, time, tz)
        if not dt_local:
            return await interaction.response.send_message("Invalid date/time. Use date=YYYY-MM-DD and time like '6:00 pm' or '18:00'.", ephemeral=True)

        dt_utc = dt_local.astimezone(timezone.utc)
        node.setdefault("hearings", []).append({
            "title": title,
            "when": dt_utc.isoformat(),
            "status": "scheduled",
            "scheduled_by": interaction.user.id,
        })
        save_federal_registry(reg)

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
        # FIX: chamber is a str here
        embed.set_footer(text=f"{str(chamber).title()} committee")
        await interaction.response.send_message(embed=embed, ephemeral=True)



    # --- new helper: parent-committee autocomplete that respects the chosen chamber ---
    async def parent_committee_by_chamber_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete ONLY top-level committees for the chamber option in the same command."""
        reg = self.federal_registry
        committees = _get_committees_root(reg)

        ns = interaction.namespace
        chamber = getattr(ns, "chamber", None)
        if isinstance(chamber, app_commands.Choice):
            chamber = chamber.value
        if chamber not in {"senate", "house", "joint"}:
            return []

        cur = (current or "").lower()
        out: list[app_commands.Choice[str]] = []
        bucket = committees.get(chamber, {})
        for key, data in sorted(bucket.items(), key=lambda kv: kv[0]):
            label = (data.get("name") or key.replace("_", " ").title()).strip()
            if not cur or cur in label.lower():
                out.append(app_commands.Choice(name=label, value=key))
        return out[:25]


    @legislature.command(name="committee_manage", description="Create/delete committees; add/remove members; set chair; bulk-appoint")
    @app_commands.choices(chamber=[
        app_commands.Choice(name="Senate", value="senate"),
        app_commands.Choice(name="House", value="house"),
        app_commands.Choice(name="Joint", value="joint"),
    ])
    @app_commands.choices(action=[
        app_commands.Choice(name="Create committee", value="create"),
        app_commands.Choice(name="Delete committee", value="delete"),
        app_commands.Choice(name="Add member", value="add_member"),
        app_commands.Choice(name="Remove member", value="remove_member"),
        app_commands.Choice(name="Set chair", value="set_chair"),
        app_commands.Choice(name="Bulk add by role", value="bulk_add_role"),
    ])
    @app_commands.choices(committee_type=[
        app_commands.Choice(name="Standing", value="standing"),
        app_commands.Choice(name="Select", value="select"),
        app_commands.Choice(name="Joint", value="joint"),
        app_commands.Choice(name="Special", value="special"),
        app_commands.Choice(name="Ad hoc", value="ad_hoc"),
    ])
    @app_commands.autocomplete(
        # For operations targeting an existing committee/subcommittee
        name=committee_name_autocomplete,
        # For CREATE subcommittee parent selection (top-level only)
        parent_committee=parent_committee_by_chamber_autocomplete
    )
    @app_commands.describe(
        chamber="Body",
        action="What to do",
        # For CREATE/DELETE and for member operations targeting a specific (sub)committee
        name="Committee or subcommittee (autocomplete; for delete/member ops)",
        # CREATE fields:
        new_name="For CREATE: new committee name (ignored for other actions)",
        committee_type="For CREATE: type of committee (default standing)",
        chair="For CREATE/SET CHAIR: the chair",
        sub_committee="For CREATE: mark as a subcommittee",
        parent_committee="For CREATE(subcommittee): pick the parent (top-level only)",
        # Membership management:
        member="For add/remove/set chair: target user",
        role="For bulk add by role",
        as_chair="When adding: also make this member the chair",
        force="When removing: allow removing the current chair"
    )
    async def committee_manage(
        self,
        interaction: discord.Interaction,
        chamber: str,                      # keep as str in signature
        action: str,                       # keep as str in signature
        name: str | None = None,
        *,
        new_name: str | None = None,
        committee_type: str | None = None, # keep as str in signature
        chair: discord.Member | None = None,
        sub_committee: bool = False,
        parent_committee: str | None = None,
        member: discord.Member | None = None,
        role: discord.Role | None = None,
        as_chair: bool = False,
        force: bool = False,
    ):
        act = (_choice_val(action) or "").lower()
        ch  = (_choice_val(chamber) or "").lower()
        ctype = (_choice_val(committee_type) or "standing").lower()


        # perms: chamber leader or admin
        if not _is_chamber_leader(interaction.user, ch):
            return await interaction.response.send_message("Only the chamber leader may manage committees.", ephemeral=True)

        reg = self.federal_registry
        committees = _get_committees_root(reg)
        bucket = committees.setdefault(ch, {})

        # ---------- CREATE ----------
        if act == "create":
            ctype = (committee_type.value if isinstance(committee_type, app_commands.Choice) else (committee_type or "standing")).strip().lower()
            # If user selected 'Joint' type, normalize bucket to 'joint'
            target_bucket_key = "joint" if ctype == "joint" else ch
            bucket = committees.setdefault(target_bucket_key, {})

            if not new_name:
                return await interaction.response.send_message("Please provide `new_name` for the committee.", ephemeral=True)
            if not chair:
                return await interaction.response.send_message("Please specify a `chair` for the new committee.", ephemeral=True)

            key = new_name.strip().lower().replace(" ", "_")
            if sub_committee:
                if not parent_committee:
                    return await interaction.response.send_message("Select a `parent_committee` for a subcommittee.", ephemeral=True)
                parent_key = parent_committee.strip().lower()
                parent = bucket.get(parent_key)
                if not parent:
                    return await interaction.response.send_message("The specified parent committee does not exist in this chamber.", ephemeral=True)
                parent.setdefault("sub_committees", {})
                if key in parent["sub_committees"]:
                    return await interaction.response.send_message("A subcommittee with that name already exists under the parent.", ephemeral=True)
                parent["sub_committees"][key] = {
                    "name": new_name,
                    "type": ctype,
                    "chair_id": chair.id,
                    "members": [chair.id],
                    "created_at": discord.utils.utcnow().isoformat(),
                    "created_by": interaction.user.id,
                }
                save_federal_registry(reg)
                where = "Joint" if target_bucket_key == "joint" else target_bucket_key.title()
                return await interaction.response.send_message(f"✅ Created subcommittee **{new_name}** under **{parent.get('name','(parent)')}** ({where}).", ephemeral=True)
            else:
                if key in bucket:
                    return await interaction.response.send_message("A committee with that name already exists.", ephemeral=True)
                bucket[key] = {
                    "name": new_name,
                    "type": ctype,
                    "chair_id": chair.id,
                    "members": [chair.id],
                    "sub_committees": {},
                    "created_at": discord.utils.utcnow().isoformat(),
                    "created_by": interaction.user.id,
                }
                save_federal_registry(reg)
                where = "Joint" if target_bucket_key == "joint" else target_bucket_key.title()
                return await interaction.response.send_message(f"✅ Created committee **{new_name}** ({where}).", ephemeral=True)

        # For the rest, we need an existing target (except bulk_add_role which still needs name)
        if not name and act != "bulk_add_role":
            return await interaction.response.send_message("Please specify `name` (committee or subcommittee).", ephemeral=True)

        # Resolve committee or subcommittee for actions that target an existing node
        parent, node = _resolve_committee_node(reg, ch, name) if name else (None, None)

        # ---------- DELETE ----------
        if act == "delete":
            if not node:
                return await interaction.response.send_message("Committee not found.", ephemeral=True)
            if parent:
                # deleting a subcommittee
                parent_key, sub_key = name.split("::", 1)
                subs = parent.get("sub_committees") or {}
                subs.pop(sub_key, None)
                save_federal_registry(reg)
                return await interaction.response.send_message(f"🗑️ Deleted subcommittee **{node.get('name','(unnamed)')}**.", ephemeral=True)
            else:
                # deleting a top-level committee
                bucket.pop(name, None)
                save_federal_registry(reg)
                return await interaction.response.send_message(f"🗑️ Deleted committee **{(node or {}).get('name','(unnamed)')}**.", ephemeral=True)

        # ---------- ADD MEMBER ----------
        if act == "add_member":
            if not node or not member:
                return await interaction.response.send_message("Pick a committee and a member to add.", ephemeral=True)
            _add_member(node, member.id)
            if as_chair:
                node["chair_id"] = member.id
            save_federal_registry(reg)
            role_note = " (Chair)" if as_chair else ""
            return await interaction.response.send_message(f"✅ Appointed {member.mention}{role_note} to **{node.get('name','(unnamed)')}**.", ephemeral=True)

        # ---------- REMOVE MEMBER ----------
        if act == "remove_member":
            if not node or not member:
                return await interaction.response.send_message("Pick a committee and a member to remove.", ephemeral=True)
            chair_id = node.get("chair_id")
            if chair_id == member.id and not force:
                return await interaction.response.send_message("That member is the chair. Use `force=True` or set a new chair first.", ephemeral=True)
            members = set(node.get("members") or [])
            if member.id in members:
                members.remove(member.id)
                node["members"] = sorted(members)
            if chair_id == member.id:
                node["chair_id"] = None
            save_federal_registry(reg)
            return await interaction.response.send_message(f"✅ Removed {member.mention} from **{node.get('name','(unnamed)')}**.", ephemeral=True)

        # ---------- SET CHAIR ----------
        if act == "set_chair":
            if not node or not chair:
                return await interaction.response.send_message("Pick a committee and specify a `chair`.", ephemeral=True)
            node["chair_id"] = chair.id
            _add_member(node, chair.id)
            save_federal_registry(reg)
            return await interaction.response.send_message(f"✅ {chair.mention} set as Chair of **{node.get('name','(unnamed)')}**.", ephemeral=True)

        # ---------- BULK ADD BY ROLE ----------
        if act == "bulk_add_role":
            if not name or not role:
                return await interaction.response.send_message("Specify `name` (committee) and a `role` to bulk add.", ephemeral=True)
            if not node:
                return await interaction.response.send_message("Committee not found.", ephemeral=True)
            added = 0
            for m in role.members:
                if m.bot:
                    continue
                if _add_member(node, m.id):
                    added += 1
            save_federal_registry(reg)
            return await interaction.response.send_message(f"✅ Appointed **{added}** members from {role.mention} to **{node.get('name','(unnamed)')}**.", ephemeral=True)

        return await interaction.response.send_message("Unknown action.", ephemeral=True)

    
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
        bill_id="Target bill ID (required for all actions except docket/status listings)",
        hours="Poll duration (open_vote)",
        threshold="Vote threshold (open_vote/close_vote)",
        notify="DM eligible members the poll link (open_vote)"
    )
    async def report_bill(
        self,
        interaction: discord.Interaction,
        action: str,
        bill_id: str | None = None,
        hours: int = 24,
        threshold: str | None = None,
        notify: bool = False,
    ):
        act = action
        reg = self.federal_registry
        items = ensure_bills_schema(reg)["items"]

        # ---------- INTRODUCE ---------- 
        if act == "introduce":
            if not bill_id or bill_id not in items:
                return await interaction.response.send_message("Provide a valid DRAFT bill_id to introduce.", ephemeral=True)
            b = items[bill_id]
            if b.get("status") != "DRAFT":
                return await interaction.response.send_message("Only DRAFT bills can be introduced.", ephemeral=True)
            if not is_in_chamber(interaction.user, b.get("chamber", "")):
                return await interaction.response.send_message(f"Only {b.get('chamber','?')} members may introduce this bill.", ephemeral=True)

            b["status"] = "INTRODUCED"
            b["introduced_by"] = interaction.user.id
            b["introduced_at"] = discord.utils.utcnow().isoformat()
            mark_history(b, f"Introduced in {b['chamber']}", interaction.user.id)
            save_federal_registry(reg)

            chan = interaction.client.get_channel(chamber_channel_id(b["chamber"]))
            if chan:
                intro_embed = discord.Embed(
                    title="Bill Introduced",
                    description=f"**{b['id']}** — {b.get('title','')}",
                    color=discord.Color.blurple()
                )
                intro_embed.add_field(name="Chamber", value=b["chamber"], inline=True)
                intro_embed.add_field(name="Sponsor", value=f"<@{b.get('sponsor_id','')}>", inline=True)
                if b.get("summary"):
                    intro_embed.add_field(name="Summary", value=b["summary"][:1024], inline=False)
                await chan.send(embed=intro_embed)

            return await interaction.response.send_message(
                f"✅ Introduced **{b['id']}** — {b.get('title','')} in the **{b['chamber']}**.",
                ephemeral=False
            )

        # (unchanged) everything below still requires bill_id:
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
            if b["chamber"] == "house":
                chan = interaction.client.get_channel(chamber_channel_id(b["chamber"]))
            else:
                chan = interaction.client.get_channel(SENATE_VOTING_CHANNEL)
            if not chan:
                return await interaction.response.send_message("Chamber channel not found.", ephemeral=True)

            # poll
            q = _poll_question_for(b)
            p = discord.Poll(
                question=q,
                duration=timedelta(hours=hours),
                multiple=False
            )
            p.add_answer(text="Yea", emoji="✅")
            p.add_answer(text="Nay", emoji="❌")
            p.add_answer(text="Present", emoji="➖")

            role_id = REPRESENTATIVES if b["chamber"] == "house" else SENATORS
            role_mention = f"<@&{role_id}>"
            msg = await chan.send(f"{role_mention}, roll call is open:", poll=p, allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False))

            # quorum set-up (reuse your helper)
            eligible = await resolve_eligible_members(interaction.guild, chan, b["chamber"])
            quorum = quorum_required(len(eligible))

            b.setdefault("vote", {})
            b["vote"].update({
                "message_id": msg.id,
                "channel_id": chan.id,
                "opened_at": discord.utils.utcnow().isoformat(),
                "opened_by": interaction.user.id,
                "threshold": (threshold if threshold else "simple"),
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
            if b["chamber"] != "house":
                chan = interaction.client.get_channel(SENATE)    
            
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


    @usc.command(name="import", description="Import a USC Title XML (stores title, created date, chapters, sections)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(file="Upload a USLM USC Title XML file (e.g., Title 1)")
    @app_commands.describe(force="Rebuild this title even if it's already imported with the same file")
    async def usc_import(self, interaction: discord.Interaction, file: discord.Attachment, force: bool = False):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not file.filename.lower().endswith(".xml"):
            return await interaction.followup.send("Upload must be an **.xml** file.", ephemeral=True)

        try:
            xml_bytes = await file.read()
        except Exception:
            return await interaction.followup.send("Couldn’t read that attachment.", ephemeral=True)

        async with self.usc_lock:
            try:
                summary = await asyncio.to_thread(_usc_import_xml_bytes, USC_DB_FILE, xml_bytes, force)
            except Exception as e:
                return await interaction.followup.send(f"Import failed: `{e}`", ephemeral=True)

        emb = discord.Embed(
            title=f"USC Title {summary.get('title_num')} — {summary.get('heading') or ''}".strip(),
            description=f"**Status:** {summary.get('status')}\n"
                        f"**Created:** {summary.get('created_at') or 'Unknown'}\n"
                        f"**Chapters:** {summary.get('chapters')}\n"
                        f"**Sections:** {summary.get('sections')}",
        )
        emb.set_footer(text=f"sha256: {summary.get('sha256')[:12]}…")
        await interaction.followup.send(embed=emb, ephemeral=True)

    @usc.command(name="titles", description="List imported USC titles")
    async def usc_titles(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        rows = await asyncio.to_thread(_usc_db_list_titles, USC_DB_FILE)
        if not rows:
            return await interaction.followup.send("No USC titles imported yet. Use `/usc import`.", ephemeral=True)

        lines = []
        for r in rows:
            lines.append(f"Title {r['title_num']} — {r['heading']}")

        emb = discord.Embed(
            title="USC Titles",
            description="\n".join(lines) if lines else "—",
        )
        await interaction.followup.send(embed=emb)

    def _usc_db_get_title_meta(self, db_path: str, title_num: int) -> sqlite3.Row | None:
        _usc_db_init(db_path)
        conn = _usc_db_connect(db_path)
        try:
            return conn.execute(
                "SELECT title_num, heading, created_at, imported_at FROM usc_titles WHERE title_num=? LIMIT 1",
                (int(title_num),),
            ).fetchone()
        finally:
            conn.close()

    @usc.command(name="toc", description="Show the table of contents for a title (chapters)")
    @app_commands.describe(title="Title number (e.g., 1)")
    async def usc_toc(self, interaction: discord.Interaction, title: int):
        # Ack quickly, and do it ephemerally so the real output can be a clean channel post
        await interaction.response.defer(ephemeral=True, thinking=True)

        meta = await asyncio.to_thread(self._usc_db_get_title_meta, USC_DB_FILE, int(title))
        chapters = await asyncio.to_thread(_usc_db_get_chapters, USC_DB_FILE, int(title))
        if not chapters:
            return await interaction.followup.send("That title isn’t imported (or has no chapters).", ephemeral=True)

        by_parent: dict[int | None, list[sqlite3.Row]] = {}
        for ch in chapters:
            by_parent.setdefault(ch["parent_id"], []).append(ch)

        lines: list[str] = []

        def walk(parent_id: int | None, depth: int) -> None:
            for ch in by_parent.get(parent_id, []):
                indent = "    " * depth
                lines.append(f"{indent}CHAPTER {ch['num']} — {ch['heading']}")
                walk(int(ch["id"]), depth + 1)

        walk(None, 0)

        created = _usc_fmt_dt(meta["created_at"]) if meta else "Unknown"
        pages = _usc_chunk_lines(lines, limit=1700)

        view = USCTextPaginator(
            title=f"USC Title {title} — Table of Contents",
            pages=pages,
            meta=f"• Created: {created}",
        )

        if interaction.channel is None:
            # fallback (DM edge case): has to be a followup
            await interaction.followup.send(content=view.make_content(), view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(content=view.make_content(), view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)

    @usc.command(name="chapter", description="List sections in a chapter")
    @app_commands.describe(title="Title number", chapter="Chapter number (as shown in the TOC)")
    async def usc_chapter(self, interaction: discord.Interaction, title: int, chapter: str):
        # Ack fast so we never time out, and so we can post a clean channel message
        await interaction.response.defer(ephemeral=True, thinking=True)

        chap_id = await asyncio.to_thread(_usc_db_get_chapter_id, USC_DB_FILE, int(title), str(chapter))
        if not chap_id:
            return await interaction.followup.send("Couldn’t find that chapter in the DB.", ephemeral=True)

        secs = await asyncio.to_thread(_usc_db_get_sections_in_chapter, USC_DB_FILE, int(title), int(chap_id))
        if not secs:
            return await interaction.followup.send("No sections found for that chapter.", ephemeral=True)

        # Build lines
        lines = []
        for s in secs:
            head = s["heading"] or ""
            lines.append(f"§ {s['section_num']} — {head}")

        # Chunk + paginate (use your existing chunker)
        pages = _usc_chunk_lines(lines, limit=1700)

        # Call the paginator (THIS is the “how to call it properly”)
        view = USCTextPaginator(
            title=f"Title {title}, Chapter {chapter} — Sections",
            pages=pages
        )

        # Post as a normal channel message (no “click to see command” banner)
        if interaction.channel is None:
            await interaction.followup.send(content=view.make_content(), view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(content=view.make_content(), view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)

    @usc.command(name="section", description="View a USC section (statute text only)")
    @app_commands.describe(title="Title number", section="Section number (e.g., 7 or 112a)")
    async def usc_section(self, interaction: discord.Interaction, title: int, section: str):
        # Acknowledge command ephemerally so the real output can be a normal channel message.
        await interaction.response.defer(ephemeral=True, thinking=True)

        row = await asyncio.to_thread(_usc_db_get_section, USC_DB_FILE, int(title), str(section))
        if not row:
            return await interaction.followup.send("Section not found (is the title imported?).", ephemeral=True)

        header = f"{title} U.S.C. § {row['section_num']} — {row['heading'] or ''}".strip()
        where = ""
        if row["chapter_num"] and row["chapter_heading"]:
            where = f"Chapter {row['chapter_num']} — {row['chapter_heading']}"

        body = row["body_text"] or "(No statute text found.)"
        pages = _usc_chunk_codeblock(body)

        view = USCSectionPaginator(header=header, where=where, pages=pages)
        embed = view.make_embed()

        if interaction.channel is None:
            # Fallback (rare): we *must* use followup, so banner may appear.
            await interaction.followup.send(embed=embed, view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)

    @usc.command(name="cite", description="Lookup by citation like '1 USC 7'")
    @app_commands.describe(cite="Example: 1 USC 7 or 1 U.S.C. § 7")
    async def usc_cite(self, interaction: discord.Interaction, cite: str):
        await interaction.response.defer(thinking=True)

        m = _cite_re.match(cite or "")
        if not m:
            return await interaction.followup.send("Couldn’t parse that. Try like: `1 USC 7`.", ephemeral=True)

        title = int(m.group("title"))
        section = m.group("section")
        row = await asyncio.to_thread(_usc_db_get_section, USC_DB_FILE, title, section)
        if not row:
            return await interaction.followup.send("Not found (is that title imported?).", ephemeral=True)

        header = f"{title} U.S.C. § {row['section_num']} — {row['heading'] or ''}".strip()
        where = ""
        if row["chapter_num"] and row["chapter_heading"]:
            where = f"Chapter {row['chapter_num']} — {row['chapter_heading']}"

        body = row["body_text"] or "(No statute text found.)"
        pages = _usc_chunk_codeblock(body)

        view = USCSectionPaginator(header=header, where=where, pages=pages)
        embed = view.make_embed()

        if interaction.channel is None:
            # Fallback (rare): we *must* use followup, so banner may appear.
            await interaction.followup.send(embed=embed, view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)

    def _usc_db_cleanup_nonusc(self, db_path: str) -> int:
        conn = _usc_db_connect(db_path)
        try:
            bad_ids = [r["id"] for r in conn.execute(
                "SELECT id FROM usc_sections WHERE identifier IS NULL OR identifier NOT LIKE '/us/usc/%'"
            ).fetchall()]

            if not bad_ids:
                return 0

            conn.executemany("DELETE FROM usc_sections_fts WHERE rowid=?", [(i,) for i in bad_ids])
            conn.executemany("DELETE FROM usc_sections WHERE id=?", [(i,) for i in bad_ids])
            conn.commit()
            return len(bad_ids)
        finally:
            conn.close()
        
    @usc.command(name="cleanup", description="Remove non-USC/notes-only sections accidentally imported")
    @app_commands.checks.has_permissions(administrator=True)
    async def usc_cleanup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        async with self.usc_lock:
            try:
                removed = await asyncio.to_thread(self._usc_db_cleanup_nonusc, USC_DB_FILE)
            except Exception as e:
                return await interaction.followup.send(f"Cleanup failed: `{e}`", ephemeral=True)

        await interaction.followup.send(f"Cleanup complete. Removed **{removed}** bad sections.", ephemeral=True)
    
    def _usc_db_reindex_nodes_fts(self, db_path: str) -> int:
        conn = _usc_db_connect(db_path)
        try:
            conn.execute("DELETE FROM usc_nodes_fts;")
            conn.execute("""
                INSERT INTO usc_nodes_fts(rowid, title_num, node_type, num, heading)
                SELECT id, title_num, node_type, num, COALESCE(heading,'')
                FROM usc_nodes
            """)
            conn.commit()
            return int(conn.execute("SELECT COUNT(*) AS n FROM usc_nodes_fts").fetchone()["n"])
        finally:
            conn.close()
    

    @usc.command(name="reindex", description="Rebuild USC search indexes (chapters/headings)")
    @app_commands.checks.has_permissions(administrator=True)
    async def usc_reindex(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.usc_lock:
            n = await asyncio.to_thread(self._usc_db_reindex_nodes_fts, USC_DB_FILE)
        await interaction.followup.send(f"Reindexed chapter headings. Rows: **{n}**.", ephemeral=True)
    
    def _usc_db_search(self, db_path: str, query: str, title: int | None, limit_sections: int = 25, limit_chapters: int = 10):
        _usc_db_init(db_path)
        conn = _usc_db_connect(db_path)
        try:
            q = _usc_make_fts_query(query)
            if not q:
                return {"titles": {}, "counts": {"sections": 0, "chapters": 0}}

            # Sections
            sec_sql = """
            SELECT
            s.id,
            s.title_num,
            s.section_num,
            COALESCE(s.heading,'') AS heading,
            COALESCE(n.num,'') AS chapter_num,
            COALESCE(n.heading,'') AS chapter_heading,
            bm25(usc_sections_fts, 0.0, 0.0, 6.0, 1.0) AS rank,
            snippet(
            usc_sections_fts,
            2,
            (char(27) || '[1;33m'),
            (char(27) || '[0m'),
            '…',
            12
            ) AS hsnip,

            snippet(
            usc_sections_fts,
            3,
            (char(27) || '[1;33m'),
            (char(27) || '[0m'),
            '…',
            24
            ) AS bsnip
            FROM usc_sections_fts
            JOIN usc_sections s ON s.id = usc_sections_fts.rowid
            LEFT JOIN usc_nodes n ON n.id = s.node_id
            WHERE usc_sections_fts MATCH ?
            """
            params = [q]
            if title is not None:
                sec_sql += " AND s.title_num = ?"
                params.append(int(title))
            sec_sql += " ORDER BY rank LIMIT ?"
            params.append(int(limit_sections))
            sec_rows = conn.execute(sec_sql, params).fetchall()

            # Chapter headings (nodes)
            ch_sql = """
            SELECT
            n.id,
            n.title_num,
            n.node_type,
            COALESCE(n.num,'') AS num,
            COALESCE(n.heading,'') AS heading,
            bm25(usc_nodes_fts, 0.0, 0.0, 0.0, 1.0) AS rank,
            snippet(
            usc_nodes_fts,
            3,
            (char(27) || '[1;33m'),
            (char(27) || '[0m'),
            '…',
            16
            ) AS snip
            FROM usc_nodes_fts
            JOIN usc_nodes n ON n.id = usc_nodes_fts.rowid
            WHERE usc_nodes_fts MATCH ?
            AND n.node_type='chapter'
            """
            params = [q]
            if title is not None:
                ch_sql += " AND n.title_num = ?"
                params.append(int(title))
            ch_sql += " ORDER BY rank LIMIT ?"
            params.append(int(limit_chapters))
            ch_rows = conn.execute(ch_sql, params).fetchall()

            # Title headings for display
            title_nums = sorted({r["title_num"] for r in sec_rows} | {r["title_num"] for r in ch_rows})
            title_map = {}
            if title_nums:
                qmarks = ",".join("?" for _ in title_nums)
                for r in conn.execute(f"SELECT title_num, heading FROM usc_titles WHERE title_num IN ({qmarks})", title_nums):
                    title_map[int(r["title_num"])] = r["heading"]

            # Group results
            grouped = {}
            for tnum in title_nums:
                grouped[tnum] = {"title_heading": title_map.get(tnum, ""), "chapters": [], "sections": []}

            for r in ch_rows:
                grouped[int(r["title_num"])]["chapters"].append({
                    "num": r["num"],
                    "heading": r["heading"],
                    "snip": r["snip"] or r["heading"],
                })

            for r in sec_rows:
                hsnip = r["hsnip"] or r["heading"]
                bsnip = r["bsnip"] or ""
                grouped[int(r["title_num"])]["sections"].append({
                    "chapter_num": r["chapter_num"],
                    "chapter_heading": r["chapter_heading"],
                    "section_num": r["section_num"],
                    "heading": r["heading"],
                    "hsnip": hsnip,
                    "bsnip": bsnip,
                })

            return {
                "titles": grouped,
                "counts": {"sections": len(sec_rows), "chapters": len(ch_rows)}
            }
        finally:
            conn.close()
    
    @usc.command(name="search", description="Search the USC (headings prioritized)")
    @app_commands.describe(
        query="Search terms (use quotes for an exact phrase)",
        title="Optional: restrict to a title number"
    )
    async def usc_search(self, interaction: discord.Interaction, query: str, title: int | None = None):
        await interaction.response.defer(ephemeral=True, thinking=True)

        data = await asyncio.to_thread(self._usc_db_search, USC_DB_FILE, query, title)
        grouped = data["titles"]
        if not grouped:
            return await interaction.followup.send(f"Unable to find any results in the U.S.C. using `{query}`.{' Consider picking a different Title.' if title else ''}", ephemeral=False)

        # Build display lines
        lines: list[str] = []
        if title is not None:
            lines.append(f"Results for: {query} (Title {title})")
        else:
            lines.append(f"Results for: {query}")

        lines.append(f"Showing {data['counts']['chapters']} chapter hits, {data['counts']['sections']} section hits (top results).")
        lines.append("")

        for tnum in sorted(grouped.keys()):
            th = grouped[tnum]["title_heading"]
            lines.append(f"Title {tnum} — {th}".rstrip())
            lines.append("-" * 28)

            # chapter hits first (like your example)
            for ch in grouped[tnum]["chapters"][:10]:
                lines.append(f"CHAPTER {ch['num']} — {ch['snip']}")

            if grouped[tnum]["chapters"]:
                lines.append("")

            for s in grouped[tnum]["sections"][:25]:
                # Show section heading with highlights if present
                lines.append(f"§ {s['section_num']} — {s['hsnip']}")
                # If heading didn’t contain highlights, show a body snippet line
                if "**" not in (s["hsnip"] or "") and s["bsnip"]:
                    lines.append(f"    … {s['bsnip']}")
            lines.append("")
            lines.append("")

        pages = _usc_chunk_lines(lines, limit=1700)
        view = USCTextPaginator(title="USC Search Results", pages=pages)

        if interaction.channel is None:
            await interaction.followup.send(content=view.make_content(), view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(content=view.make_content(), view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)
    
    @src.command(name="import", description="Import Spidey Republic Code (SRC) JSON into SQLite")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(file="Upload src.json")
    async def src_import(self, interaction: discord.Interaction, file: discord.Attachment, force: bool = False):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not file.filename.lower().endswith(".json"):
            return await interaction.followup.send("Upload must be a **.json** file.", ephemeral=True)

        try:
            raw = await file.read()
        except Exception:
            return await interaction.followup.send("Couldn’t read that attachment.", ephemeral=True)

        async with self.src_lock:
            try:
                summary = await asyncio.to_thread(_src_import_json_bytes, SRC_DB_FILE, raw, force)
            except Exception as e:
                return await interaction.followup.send(f"SRC import failed: `{e}`", ephemeral=True)

        emb = discord.Embed(
            title="SRC Import Complete",
            description=(
                f"**Titles processed:** {summary['titles_processed']}\n"
                f"**Titles imported/updated:** {summary['titles_imported_or_updated']}\n"
                f"**Chapters:** {summary['chapters']}\n"
                f"**Sections:** {summary['sections']}"
            ),
        )
        emb.set_footer(text=f"sha256: {summary['sha256'][:12]}…")
        await interaction.followup.send(embed=emb, ephemeral=True)


    @src.command(name="titles", description="List imported SRC titles")
    async def src_titles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        rows = await asyncio.to_thread(_src_db_list_titles, SRC_DB_FILE)
        if not rows:
            return await interaction.followup.send("No SRC titles imported yet. Use `/government src import`.", ephemeral=True)

        lines = [f"Title {r['title_num']} — {r['heading']}" for r in rows]
        # post as normal channel message to avoid “click to see command” clutter
        pages = _chunk_lines(lines, limit=1700)
        content = f"**Imported SRC Titles**\n```text\n{pages[0]}\n```\n`Page 1/{len(pages)}`"
        if interaction.channel is None:
            return await interaction.followup.send(content, ephemeral=True)
        msg = await interaction.channel.send(content=content)
        if len(pages) > 1:
            await interaction.followup.send("Titles list is long—consider adding a paginator view like USC later.", ephemeral=True)
        else:
            await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)


    @src.command(name="toc", description="Show SRC table of contents (chapters) for a title")
    @app_commands.describe(title="Title number")
    async def src_toc(self, interaction: discord.Interaction, title: int):
        await interaction.response.defer(ephemeral=True, thinking=True)

        chaps = await asyncio.to_thread(_src_db_get_chapters, SRC_DB_FILE, int(title))
        if not chaps:
            return await interaction.followup.send("That SRC title isn’t imported (or has no chapters).", ephemeral=True)

        lines = [f"CHAPTER {c['num']} — {c['heading'] or ''}".rstrip() for c in chaps]
        pages = _chunk_lines(lines, limit=1700)

        content = f"**SRC Title {title} — Table of Contents**\n```text\n{pages[0]}\n```\n`Page 1/{len(pages)}`"
        if interaction.channel is None:
            return await interaction.followup.send(content, ephemeral=True)

        msg = await interaction.channel.send(content=content)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)


    @src.command(name="chapter", description="List sections in an SRC chapter")
    @app_commands.describe(title="Title number", chapter="Chapter number (as shown in the TOC)")
    async def src_chapter(self, interaction: discord.Interaction, title: int, chapter: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        chap_id = await asyncio.to_thread(_src_db_get_chapter_id, SRC_DB_FILE, int(title), str(chapter))
        if not chap_id:
            return await interaction.followup.send("Couldn’t find that chapter in SRC.", ephemeral=True)

        secs = await asyncio.to_thread(_src_db_get_sections_in_chapter, SRC_DB_FILE, int(title), int(chap_id))
        if not secs:
            return await interaction.followup.send("No sections found for that SRC chapter.", ephemeral=True)

        lines = [f"§ {s['section_num']} — {s['heading'] or ''}".rstrip() for s in secs]
        pages = _chunk_lines(lines, limit=1700)

        content = f"**SRC Title {title}, Chapter {chapter} — Sections**\n```text\n{pages[0]}\n```\n`Page 1/{len(pages)}`"
        if interaction.channel is None:
            return await interaction.followup.send(content, ephemeral=True)

        msg = await interaction.channel.send(content=content)
        if len(pages) > 1:
            await interaction.followup.send("Long chapter list—add the same button paginator you used for USC chapter when you’re ready.", ephemeral=True)
        else:
            await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)


    @src.command(name="section", description="View an SRC section")
    @app_commands.describe(title="Title number", section="Section number (e.g., 551 or § 551)")
    async def src_section(self, interaction: discord.Interaction, title: int, section: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        row = await asyncio.to_thread(_src_db_get_section, SRC_DB_FILE, int(title), str(section))
        if not row:
            return await interaction.followup.send("SRC section not found (is that title imported?).", ephemeral=True)

        header = f"SRC Title {title} § {row['section_num']} — {row['heading'] or ''}".strip()
        where = ""
        if row["chapter_num"]:
            where = f"Chapter {row['chapter_num']} — {row['chapter_heading'] or ''}".strip()

        body = (row["body_text"] or "").strip()
        if not body:
            body = "(No text stored for this section.)"

        body = _src_pretty_indent(body)

        pages = _usc_chunk_codeblock(body)  # same chunker you use for USC
        view = USCSectionPaginator(header=header, where=where, pages=pages)
        embed = view.make_embed()

        if interaction.channel is None:
            await interaction.followup.send(embed=embed, view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)
    
    def _src_db_reindent_all(self, db_path: str) -> int:
        conn = _src_db_connect(db_path)
        try:
            rows = conn.execute("SELECT id, body_text FROM src_sections").fetchall()
            updated = 0
            conn.execute("BEGIN;")
            for r in rows:
                old = r["body_text"] or ""
                new = _src_pretty_indent(old)
                if new != old:
                    conn.execute("UPDATE src_sections SET body_text=? WHERE id=?", (new, r["id"]))
                    updated += 1
            conn.commit()
            return updated
        finally:
            conn.close()
    
    @src.command(name="reindent", description="Re-indent stored SRC section text (fixes C/D roman indentation issue)")
    @app_commands.checks.has_permissions(administrator=True)
    async def src_reindent(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.src_lock:
            n = await asyncio.to_thread(self._src_db_reindent_all, SRC_DB_FILE)
        await interaction.followup.send(f"Re-indented **{n}** SRC sections.", ephemeral=True)

    @src.command(name="reindex", description="Rebuild SRC search indexes (chapters + sections)")
    @app_commands.checks.has_permissions(administrator=True)
    async def src_reindex(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.src_lock:
            res = await asyncio.to_thread(_src_db_reindex_fts, SRC_DB_FILE)
        await interaction.followup.send(
            f"Reindexed SRC. Nodes: **{res['nodes']}**, Sections: **{res['sections']}**.",
            ephemeral=True
        )
    
    @src.command(name="search", description="Search the S.R.C. (headings prioritized)")
    @app_commands.describe(query="Search terms (quotes for phrases)", title="Optional: restrict to title number")
    async def src_search(self, interaction: discord.Interaction, query: str, title: int | None = None):
        await interaction.response.defer(ephemeral=True, thinking=True)

        data = await asyncio.to_thread(_src_db_search, SRC_DB_FILE, query, title)
        grouped = data["titles"]
        if not grouped:
            return await interaction.followup.send("No matches found.", ephemeral=True)

        lines: list[str] = []
        if title is not None:
            lines.append(f"Results for: {query}")
            lines.append(f"(SRC Title {title})")
        else:
            lines.append(f"Results for: {query}")
        lines.append(f"Showing {data['counts']['chapters']} chapter hits, {data['counts']['sections']} section hits (top results).")
        lines.append("")

        for tnum in sorted(grouped.keys()):
            th = grouped[tnum]["title_heading"]
            lines.append(f"Title {tnum} — {th}".rstrip())
            lines.append("-" * 28)

            for ch in grouped[tnum]["chapters"][:10]:
                lines.append(f"CHAPTER {ch['num']} — {ch['snip']}")

            if grouped[tnum]["chapters"]:
                lines.append("")

            for s in grouped[tnum]["sections"][:25]:
                lines.append(f"§ {s['section_num']} — {s['hsnip']}")
                if "\x1b[" not in (s["hsnip"] or "") and s["bsnip"]:
                    lines.append(f"    … {s['bsnip']}")
            lines.append("")
            lines.append("")

        pages = _usc_chunk_lines(lines, limit=1600)  # keep headroom; ANSI codes add chars
        view = USCTextPaginator(title="SRC Search Results", pages=pages)

        if interaction.channel is None:
            await interaction.followup.send(content=view.make_content(), view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(content=view.make_content(), view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)

    @compare.command(name="section", description="Compare a USC section against an SRC section (ANSI diff).")
    @app_commands.describe(
        usc_title="USC title number",
        usc_section="USC section number (e.g., 552 or 1101)",
        src_title="SRC title number (defaults to USC title)",
        src_section="SRC section number (defaults to USC section)"
    )
    async def compare_section(
        self,
        interaction: discord.Interaction,
        usc_title: int,
        usc_section: str,
        src_title: int | None = None,
        src_section: str | None = None
    ):
        # Acknowledge ephemerally; post the real diff in-channel (same pattern as usc_section):contentReference[oaicite:3]{index=3}
        await interaction.response.defer(ephemeral=True, thinking=True)

        st = int(src_title) if src_title is not None else int(usc_title)
        ss = str(src_section) if src_section is not None else str(usc_section)

        # Lock order: USC then SRC (consistent; avoids deadlock risk)
        async with self.usc_lock:
            usc_row = await asyncio.to_thread(_usc_db_get_section, USC_DB_FILE, int(usc_title), str(usc_section))
        if not usc_row:
            return await interaction.followup.send("USC section not found (is that title imported?).", ephemeral=True)

        async with self.src_lock:
            src_row = await asyncio.to_thread(_src_db_get_section, SRC_DB_FILE, st, ss)
        if not src_row:
            return await interaction.followup.send("SRC section not found (is that title imported?).", ephemeral=True)

        usc_body = (usc_row["body_text"] or "").strip()
        src_body = (src_row["body_text"] or "").strip()

        # If you want SRC formatting normalized the same way you display it elsewhere,
        # uncomment this (only if you already have _src_pretty_indent in your file):
        # src_body = _src_pretty_indent(src_body)

        diff_lines, stats, ratio = _usc_src_unified_diff_lines(usc_body, src_body)

        title_line = (
            f"{usc_title} USC § {usc_row['section_num']} ↔ "
            f"SRC {st} § {src_row['section_num']}"
        )

        meta = (
            f"Similarity: {ratio*100:.1f}% · "
            f"+SRC: {stats['inserted']} · "
            f"-SRC: {stats['deleted']} · "
            f"repl blocks: {stats['replaced']}"
        )

        # ANSI codes add chars; keep extra headroom
        pages = _usc_chunk_lines(diff_lines, limit=1400)  # helper exists next to USCTextPaginator:contentReference[oaicite:4]{index=4}
        view = USCTextPaginator(title=title_line, pages=pages, meta=meta)  # renders ```ansi:contentReference[oaicite:5]{index=5}

        if interaction.channel is None:
            # fallback (rare): followup will show banner sometimes
            await interaction.followup.send(content=view.make_content(), view=view, ephemeral=False)
            return

        msg = await interaction.channel.send(content=view.make_content(), view=view)
        await interaction.followup.send(f"Posted: {msg.jump_url}", ephemeral=True)