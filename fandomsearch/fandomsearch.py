from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote

import discord
from discord import app_commands
from redbot.core import commands
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FANDOMS_FILE = os.path.join(BASE_DIR, "fandoms.json")


def load_file() -> dict:
    if not os.path.exists(FANDOMS_FILE):
        return {}

    with open(FANDOMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_file(data):
    """Save the federal registry to a JSON file."""
    with open(FANDOMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def _normalize_base_link(url: str) -> str:
    """
    Expect something like:
      https://starwars.fandom.com/wiki
    We'll:
      - enforce https://
      - strip trailing slashes
      - ensure it ends with /wiki
    """
    url = url.strip()
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.startswith("https://"):
        raise ValueError("Base link must start with https://")

    url = url.rstrip("/")
    if not url.lower().endswith("/wiki"):
        url += "/wiki"
    return url

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
        base_link="The fandom link with https:// and pointing to /wiki",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def upload_link(self, interaction: discord.Interaction, fandom: str, base_link: str):
        try:
            key = fandom.strip().lower().replace(" ", "")
            if not key:
                raise ValueError("Fandom key cannot be empty.")
            base = _normalize_base_link(base_link)
        except ValueError as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)

        # Overwrite or create
        self.fandoms[key] = base
        save_file(self.fandoms)
        await interaction.response.send_message(
            f"✅ Saved **{key}** → {base}", ephemeral=True
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

    @fandom.command(name="list", description="List configured fandom base links.")
    async def list_links(self, interaction: discord.Interaction):
        if not self.fandoms:
            return await interaction.response.send_message("No fandoms configured yet.", ephemeral=True)
        lines = [f"- **{k}** → {self.fandoms.get(k)}" for k in sorted(self.fandoms.keys())]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @fandom.command(name="search", description="Link a page from a configured fandom wiki.")
    @app_commands.describe(
        fandom="Which fandom wiki to use (autocomplete)",
        query="Page title or search terms",
        exact="If true, link the exact title",
        section="Optional section anchor for exact links",
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
        base = self.fandoms.get(key)
        if not base:
            return await interaction.response.send_message(
                f"⚠️ Fandom **{key}** is not configured. Use `/fandom upload_link` first.",
                ephemeral=True,
            )

        if exact:
            url = f"{base}/{_slugify(query)}"
            if section:
                url += f"#{_slugify(section.replace(' ', '_'))}"
            await interaction.response.send_message(url)
            return

        # Fuzzy search: one combined response to avoid double-responding
        preface = ""
        if section:
            preface = "ℹ️ Sections only apply to exact links. Using fuzzy search without #section.\n"
        url = f"{base}/Special:Search?query={quote(query)}&go=Go"
        await interaction.response.send_message(f"{preface}{url}")