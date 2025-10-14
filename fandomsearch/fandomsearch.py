from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote, urlparse

import discord
from discord import app_commands
from redbot.core import commands
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FANDOMS_FILE = os.path.join(BASE_DIR, "fandoms.json")

STYLE_FANDOM = "fandom"
STYLE_ROOT = "root"

def load_file() -> dict:
    if not os.path.exists(FANDOMS_FILE):
        return {}

    with open(FANDOMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_file(data):
    """Save the federal registry to a JSON file."""
    with open(FANDOMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def _build_exact_url(base: str, style: str, title: str, section: str | None = None) -> str:
    slug = _slugify(title)
    # Both styles append /Title; fandom bases typically end with /wiki
    url = f"{base}/{slug}"
    if section:
        url += f"#{_slugify(section.replace(' ', '_'))}"
    return url

def _build_go_search_url(base: str, style: str, query: str) -> str:
    from urllib.parse import quote
    if style == "fandom":
        # Fandom-style works fine with Special:Search + go=Go
        return f"{base}/Special:Search?query={quote(query)}&go=Go"
    # ROOT/Paradox-style: use index.php?search=... (most compatible)
    # Optional: add &title=Special:Search to force the special page context.
    return f"{base}/index.php?search={quote(query)}&title=Special%3ASearch"
 

def _normalize_base_link(url: str) -> str:
    url = url.strip()
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.startswith("https://"):
        raise ValueError("Base link must start with https://")
    parts = urlparse(url)
    if not parts.netloc:
        raise ValueError("Base link must include a valid host (e.g., https://starwars.fandom.com/wiki)")
    return url.rstrip("/")

def _slugify(title: str) -> str:
    # MediaWiki uses underscores; keep (), _, :, /, - unescaped for readability.
    title = title.strip().replace(" ", "_")
    return quote(title, safe="()_:/-")

# ---------- The Cog ----------
class FandomSearch(commands.Cog):
    """Scalable Fandom link searcher with autocomplete and JSON persistence."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.fandoms = load_file()

    def _get_entry(self, key: str) -> dict | None:
        """Return a normalized entry dict {'base': str, 'style': 'fandom'|'root'} or None."""
        raw = self.fandoms.get(key)
        if raw is None:
            return None
        if isinstance(raw, str):
            # backward-compat: old entries are assumed fandom-style
            return {"base": raw.rstrip("/"), "style": STYLE_FANDOM}
        base = _normalize_base_link(raw.get("base", ""))
        style = raw.get("style", STYLE_FANDOM)
        if style not in (STYLE_FANDOM, STYLE_ROOT):
            style = STYLE_FANDOM
        return {"base": base, "style": style}

    fandom = app_commands.Group(name="fandom", description="fandom link searches")

    async def _fandom_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        current = (current or "").lower()
        keys = list(self.fandoms.keys())
        if current:
            keys = [k for k in keys if current in k.lower()]
        return [app_commands.Choice(name=k.title(), value=k) for k in keys[:25]]

    @fandom.command(name="upload_link", description="Upload the base link for a new fandom search.")
    @app_commands.describe(
        fandom="The fandom key (e.g., 'starwars', 'lotr', 'fallout')",
        base_link="The base link (https://...), e.g., https://starwars.fandom.com/wiki or https://hoi4.paradoxwikis.com",
        not_fandom="Toggle ON for non-Fandom/MediaWiki roots (e.g., Paradox wikis with no /wiki)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def upload_link(self, interaction: discord.Interaction, fandom: str, base_link: str, not_fandom: bool = False):
        try:
            key = fandom.strip().lower().replace(" ", "")
            if not key:
                raise ValueError("Fandom key cannot be empty.")
            base = _normalize_base_link(base_link)
        except ValueError as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)

        style = STYLE_ROOT if not_fandom else STYLE_FANDOM
        self.fandoms[key] = {"base": base, "style": style}
        save_file(self.fandoms)
        await interaction.response.send_message(
            f"✅ Saved **{key}** → {base}  *(style: {style})*", ephemeral=True
        )

    @fandom.command(name="remove", description="Remove a fandom mapping.")
    @app_commands.describe(fandom="The fandom key to remove")
    @app_commands.autocomplete(fandom=_fandom_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_link(self, interaction: discord.Interaction, fandom: str):
        key = fandom.strip().lower().replace(" ", "")
        if key in self.fandoms:
            del self.fandoms[key]
            save_file(self.fandoms)
            await interaction.response.send_message(f"🗑️ Removed **{key}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No mapping for **{key}**.", ephemeral=True)

    # --- list command: show style cleanly ---
    @fandom.command(name="list", description="List configured fandom base links.")
    async def list_links(self, interaction: discord.Interaction):
        if not self.fandoms:
            return await interaction.response.send_message("No fandoms configured yet.", ephemeral=True)

        lines = []
        for k in sorted(self.fandoms.keys()):
            entry = self._get_entry(k)
            if not entry:
                continue
            style = entry["style"]
            emoji = "🌌" if style == STYLE_FANDOM else "📚"
            lines.append(f"- **{k}** {emoji} *(style: {style})* → {entry['base']}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


    # --- search command: branch on style, single response ---
    @fandom.command(name="search", description="Link a page from a configured fandom wiki.")
    @app_commands.describe(
        fandom="Which fandom wiki to use (autocomplete)",
        query="Page title or search terms",
        exact="If true, link the exact title; otherwise use best-match redirect",
        section="Optional section anchor for exact links (e.g., 'Biography')",
    )
    @app_commands.autocomplete(fandom=_fandom_autocomplete)
    async def search(
        self,
        interaction: discord.Interaction,
        fandom: str,
        query: str,
        exact: bool = False,
        section: Optional[str] = None,
    ):
        key = fandom.strip().lower().replace(" ", "")
        entry = self._get_entry(key)
        if not entry:
            return await interaction.response.send_message(
                f"⚠️ Fandom **{key}** is not configured. Use `/fandom upload_link` first.",
                ephemeral=True,
            )

        base, style = entry["base"], entry["style"]
        if exact:
            url = _build_exact_url(base, style, query, section)
            return await interaction.response.send_message(url)

        preface = ""
        if section:
            preface = "ℹ️ Sections only apply to exact links. Using fuzzy search without #section.\n"
        url = _build_go_search_url(base, style, query)
        await interaction.response.send_message(f"{preface}{url}")
