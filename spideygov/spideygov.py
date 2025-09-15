from __future__ import annotations
import discord
from redbot.core import commands
from discord import app_commands
import json
import os
import re
import asyncio
import random


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FED_REGISTRY_FILE = os.path.join(BASE_DIR, "federal_registry.json")
SENATORS = 1327053499405701142
REPRESENTATIVES = 1327053334036742215
SENATE = 1302330234422562887
HOUSE = 1302330037365772380

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



class LegislativeProposalModal(discord.ui.Modal, title="Legislative Proposal"):
    def __init__(self, title: str, type: str, sponsor: discord.Member,
                 joint: bool=False, chamber: str | None=None,
                 codification: bool=False, repealing: bool=False,
                 committee: str|None=None, co_sponsors: str|None=None,
                 code_title: str|None=None, sections: str|None=None):
        super().__init__()
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
        await interaction.response.send_message("Proposal received (draft saved locally).", ephemeral=True)


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




class SpideyGov(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.federal_registry = load_federal_registry()
        self.registry_lock = asyncio.Lock()

    def cog_unload(self):
        save_federal_registry(self.federal_registry)

    government = app_commands.Group(name="government", description="Government related commands")

    @government.command(name="propose_legislation", description="Propose new legislation")
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


    @government.command(name="title_editor", description="Name a title for federal regulations")
    @app_commands.checks.has_any_role(SENATORS, REPRESENTATIVES)
    @app_commands.describe(
        title="The number of the Title",
        description="A brief description of the Title",
        replacing_desc="Replacing an existing desc?"
    )
    async def title_editor(self, interaction: discord.Interaction, title: int, description: str, replacing_desc: bool = False):
        if str(title) in self.federal_registry and not replacing_desc:
            return await interaction.response.send_message(f"Title {title} already exists in the federal registry.", ephemeral=True)
        self.federal_registry.setdefault("spidey_republic_code", {})
        node = self.federal_registry.setdefault("spidey_republic_code", {}).setdefault(str(title), {"description":"", "chapters": {}})
        node["description"] = description

        save_federal_registry(self.federal_registry)
        await interaction.response.send_message(f"Title {title} - '{description}' has been {'added to' if not replacing_desc else 'updated for'} the federal registry.", ephemeral=True)

    async def code_title_autocomplete(self, interaction: discord.Interaction, current: str):
        titles = self.federal_registry.get("spidey_republic_code", {})
        return [app_commands.Choice(name=f"{t} — {titles[t]['description']}", value=t)
                for t in titles if current.lower() in t.lower()]


    @government.command(name="chapter_editor", description="Name a chapter for federal regulations")
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
        titles = self.federal_registry.get("spidey_republic_code", {})
        chapters = titles.get(str(title), {}).get("chapters", {}) if title else {}
        return [app_commands.Choice(name=f"{c} — {chapters[c].get('description','')}", value=c)
                for c in chapters if current.lower() in str(c).lower()]


    @government.command(name="code_upload_chapter", description="Upload one chapter (safe, previewed)")
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

    @government.command(name="view_code", description="View code sections from a chapter")
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
    
    @government.command(name="view_category_info", description="View info about a category")
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
    async def view_category_info(self, interaction: discord.Interaction, category: app_commands.Choice[str]):
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
        citizenship = [m for m in interaction.guild.members if CITIZENSHIP_IDS.intersection(r.id for r in m.roles)] if interaction.guild else []
        embed.add_field(name="Total Citizens", value=str(len(citizenship)), inline=False)
        categories = self.federal_registry.setdefault("categories", {})
        categories.setdefault(cat_key, {})
        governor = categories[cat_key].get("governor")
        if governor:
            member = interaction.guild.get_member(governor) if interaction.guild else None
            governor_name = member.display_name if member else f"User ID {governor}"
            embed.add_field(name="Governor", value=governor_name, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)