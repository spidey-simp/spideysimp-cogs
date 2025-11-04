from __future__ import annotations
import asyncio
from typing import Dict, List, Optional, Tuple
import discord
from discord import app_commands
from discord.ext.commands import BucketType
from redbot.core import commands
from aiohttp import ClientSession, ClientTimeout
import wordfreq

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

CANON_POS = {
"noun": "noun",
"verb": "verb",
"adjective": "adjective",
"adverb": "adverb",
"pronoun": "pronoun",
"preposition": "preposition",
"conjunction": "conjunction",
"interjection": "interjection",
"determiner": "determiner",
"numeral": "numeral",
# common alternates from wiktionary/api
"article": "determiner",
"proper noun": "noun",
"adjective satellite": "adjective",
}

def normalize_pos(pos: str) -> str:
    p = (pos or "").strip().lower()
    return CANON_POS.get(p, p)

def title(s: str) -> str:
    return s[:1].upper() + s[1:]


class Dictionary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        try:
            self._wordlist = wordfreq.top_n_list('en', 60000)
        except Exception:
            self.common_words = set()
    
    async def cog_load(self):
        self.session = ClientSession(timeout=ClientTimeout(total=12))

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_definition(self, word: str) -> Optional[dict | list]:
        assert self.session is not None
        try:
            async with self.session.get(API_URL.format(word=word)) as resp:
                if resp.status == 200:
                    return await resp.json()
        # Surface structured errors when present
                try:
                    return {"error": await resp.json()}
                except Exception:  
                    return {"error": {"title": f"HTTP {resp.status}", "message": "Request failed."}}
        except asyncio.TimeoutError:
            return {"error": {"title": "Timeout", "message": "Dictionary lookup took too long."}}
        except Exception as e:
            return {"error": {"title": "Error", "message": str(e)}}
                
    def fold_entries(self, data: list) -> Tuple[Dict[str, List[dict]], List[dict], List[str]]:
        """Return (by_pos, phonetics, sources).
        by_pos maps canonical pos -> list of {'definition': str, 'example': Optional[str]}
        phonetics is the concatenated phonetics arrays from entries
        sources is a list of sourceUrls
        """
        by_pos: Dict[str, List[dict]] = {}
        phonetics: List[dict] = []
        sources: List[str] = []


        for entry in data:
            phonetics.extend(entry.get("phonetics", []) or [])
            for url in entry.get("sourceUrls", []) or []:
                if url not in sources:
                    sources.append(url)
            for meaning in entry.get("meanings", []) or []:
                pos = normalize_pos(meaning.get("partOfSpeech", "other"))
                defs = meaning.get("definitions", []) or []
                for d in defs:
                    item = {"definition": d.get("definition", ""), "example": d.get("example")}
                    by_pos.setdefault(pos, []).append(item)
        return by_pos, phonetics, sources
    
    def _format_def_lines(
        self,
        defs: list[dict],
        *,
        start_index: int = 1,
        style: str = "numbers",      # "numbers" or "bullets"
        examples: int = 2,           # how many examples to inline
        max_chars: int = 1000        # stay under Discord field cap
    ) -> tuple[str, int]:
        lines: list[str] = []
        idx = start_index
        for i, d in enumerate(defs):
            prefix = f"{idx}. " if style == "numbers" else "• "
            line = f"{prefix}{d['definition']}"
            if i < examples and d.get("example"):
                ex = d["example"].strip()
                if len(ex) > 140:
                    ex = ex[:137] + "…"
                line += f"\n    _e.g., {ex}_"
            tentative = "\n".join(lines + [line])
            if len(tentative) > max_chars:
                break
            lines.append(line)
            idx += 1
        return "\n".join(lines), idx

    
    def build_summary_embed(
        self,
        word: str,
        by_pos: Dict[str, List[dict]],
        phonetics: List[dict],
        sources: List[str],
        pos_filter: Optional[str] = None,
        per_pos_limit: int = 8,
        ) -> discord.Embed:
        e = discord.Embed(title=f"Definition of {word}", color=discord.Color.blurple())


        # phonetic + one audio
        text_phon = next((p.get("text") for p in phonetics if p.get("text")), None)
        audio = next((p.get("audio") for p in phonetics if p.get("audio")), None)
        if text_phon:
            e.add_field(name="Pronunciation", value=text_phon, inline=False)
        if audio:
            e.add_field(name="Audio", value=audio, inline=False)


        keys = [pos_filter] if pos_filter else sorted(by_pos.keys())
        added_any = False
        for pos in keys:
            defs = by_pos.get(pos, [])
            if not defs:
                continue
            added_any = True
            shown = defs[:per_pos_limit]
            value, _ = self._format_def_lines(
                shown, start_index=1, style="numbers", examples=2, max_chars=1000
            )
            extra = len(defs) - len(shown)
            if extra > 0:
                value += f"\n(+{extra} more)"
            e.add_field(name=title(pos), value=value or "—", inline=False)


        if not added_any:
            e.description = "No definitions found for the requested part of speech."


        if sources:
            e.set_footer(text="Source: " + ", ".join(sources[:2]))

        return e

    def build_pages(
        self,
        word: str,
        by_pos: Dict[str, List[dict]],
        phonetics: List[dict],
        sources: List[str],
        pos_filter: Optional[str] = None,
        budget: int = 5200,
        max_fields: int = 20,
        defs_per_field: int = 8,
    ) -> List[discord.Embed]:
        pages: List[discord.Embed] = []

        # One-time top info for the very first page only
        def apply_top_info(embed: discord.Embed, first_page: bool) -> None:
            if first_page:
                text_phon = next((p.get("text") for p in phonetics if p.get("text")), None)
                audio = next((p.get("audio") for p in phonetics if p.get("audio")), None)
                if text_phon:
                    embed.add_field(name="Pronunciation", value=text_phon, inline=False)
                if audio:
                    embed.add_field(name="Audio", value=audio, inline=False)
            if sources:
                embed.set_footer(text="Source: " + ", ".join(sources[:2]))

        pos_keys = [pos_filter] if pos_filter else sorted(by_pos.keys())
        first = True
        for pos in pos_keys:
            defs = by_pos.get(pos, [])
            if not defs:
                continue

            chunk_fields: List[Tuple[str, str]] = []
            char_count = 0
            fields_used = 0

            def flush() -> None:
                nonlocal chunk_fields, char_count, fields_used, first
                if not chunk_fields:
                    return
                embed = discord.Embed(title=f"{word} — {title(pos)}", color=discord.Color.blurple())
                for name, value in chunk_fields:
                    embed.add_field(name=name, value=value, inline=False)
                apply_top_info(embed, first)
                pages.append(embed)
                chunk_fields, char_count, fields_used = [], 0, 0
                first = False

            index = 1
            # Make fields of defs_per_field items
            for i in range(0, len(defs), defs_per_field):
                items = defs[i:i + defs_per_field]
                value, index = self._format_def_lines(
                    items, start_index=index, style="numbers", examples=0, max_chars=1000
                )
                name = f"{title(pos)} {i // defs_per_field + 1}"

                need = len(name) + len(value)
                if fields_used + 1 > max_fields or char_count + need > budget:
                    flush()
                chunk_fields.append((name, value))
                fields_used += 1
                char_count += need

            flush()

        if not pages:
            pages.append(discord.Embed(description="No definitions found."))
        return pages

    
    class DefinitionPaginator(discord.ui.View):
        def __init__(self, pages: List[discord.Embed], *, timeout: float = 120):
            super().__init__(timeout=timeout)
            self.pages = pages
            self.i = 0
            # Build a pos jump selector when many pages exist
            if len(pages) > 5:
                opts = []
                for idx, p in enumerate(pages[:25]):
                    label = p.title or f"Page {idx+1}"
                    if len(label) > 100:
                        label = label[:97] + "…"
                    opts.append(discord.SelectOption(label=label, value=str(idx)))
                self.add_item(Dictionary.PageSelect(opts, self))


        async def update(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=self.pages[self.i], view=self)

        @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
        async def prev(self, _, interaction: discord.Interaction):
            self.i = (self.i - 1) % len(self.pages)
            await self.update(interaction)


        @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
        async def next(self, _, interaction: discord.Interaction):
            self.i = (self.i + 1) % len(self.pages)
            await self.update(interaction)


        async def on_timeout(self) -> None:
            for child in self.children:
                child.disabled = True
    
    class PageSelect(discord.ui.Select):
        def __init__(self, options: List[discord.SelectOption], pager: "Dictionary.DefinitionPaginator"):
            super().__init__(placeholder="Jump to page…", options=options, min_values=1, max_values=1)
            self.pager = pager


        async def callback(self, interaction: discord.Interaction):
            try:
                self.pager.i = int(self.values[0])
            except Exception:
                pass
            await self.pager.update(interaction)



    # --- Autocomplete ---
    async def word_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        q = (current or "").lower()
        if not q:
            # common misspells / tricky words as seed
            picks = self._wordlist[:25]
        else:
            picks = [w for w in self._wordlist if w.lower().startswith(q)]
            picks = sorted(picks)[:25]
        return [app_commands.Choice(name=w, value=w) for w in picks]

    POS_CHOICES = [
        app_commands.Choice(name="noun", value="noun"),
        app_commands.Choice(name="verb", value="verb"),
        app_commands.Choice(name="adjective", value="adjective"),
        app_commands.Choice(name="adverb", value="adverb"),
        app_commands.Choice(name="pronoun", value="pronoun"),
        app_commands.Choice(name="preposition", value="preposition"),
        app_commands.Choice(name="conjunction", value="conjunction"),
        app_commands.Choice(name="interjection", value="interjection"),
        app_commands.Choice(name="determiner", value="determiner"),
        app_commands.Choice(name="numeral", value="numeral"),
        ]


    MODE_CHOICES = [
        app_commands.Choice(name="summary", value="summary"),
        app_commands.Choice(name="full", value="full"),
        ]
    
    
    

    @app_commands.command(name="define", description="Look up an English word with optional POS filter and paging.")
    @app_commands.describe(
        word="Word to define",
        pos="Filter by part of speech",
        mode="summary = one embed; full = multiple pages",
        truncate="When full: use a paginator instead of sending many embeds",
        max_embeds="If truncate is False, limit how many embeds are sent (1–5)",
        )
    @app_commands.choices(pos=POS_CHOICES, mode=MODE_CHOICES)
    @app_commands.autocomplete(word=word_autocomplete)
    async def define(
        self,
        interaction: discord.Interaction,
        word: str,
        pos: Optional[str] = None,
        mode: str = "summary",
        truncate: bool = True,
        max_embeds: int = 3,
    ) -> None:
        await interaction.response.defer(thinking=True)
        word_l = word.strip().lower()
        if not word_l:
            await interaction.followup.send("Please provide a word.")
            return


        # clamp max_embeds
        try:
            max_embeds = max(1, min(int(max_embeds), 5))
        except Exception:
            max_embeds = 3


        data = await self.fetch_definition(word_l)
        if not data:
            await interaction.followup.send("Lookup failed.")
            return


        # Error shape
        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            title = err.get("title", "Error")
            msg = err.get("message") or err.get("resolution") or "No details provided."
            embed = discord.Embed(title=title, description=msg, color=discord.Color.red())
            await interaction.followup.send(embed=embed)
            return


        # Parse list of entries
        by_pos, phonetics, sources = self.fold_entries(data) # type: ignore[arg-type]
        pos_filter = normalize_pos(pos) if pos else None
        if pos_filter:
            # filter to selected pos only
            by_pos = {k: v for (k, v) in by_pos.items() if normalize_pos(k) == pos_filter}
            if not any(by_pos.values()):
                await interaction.followup.send(f"No definitions found for part of speech: **{pos_filter}**.")
                return


        if mode == "summary":
            embed = self.build_summary_embed(word_l, by_pos, phonetics, sources, pos_filter=pos_filter)
            await interaction.followup.send(embed=embed)
            return


        # Full mode
        pages = self.build_pages(word_l, by_pos, phonetics, sources, pos_filter=pos_filter)


        if truncate or len(pages) > 5:
            # Use paginator (always better UX for many pages)
            if len(pages) == 1:
                await interaction.followup.send(embed=pages[0])
                return
            view = self.DefinitionPaginator(pages)
            await interaction.followup.send(embed=pages[0], view=view)
            return


        # Non-truncated: send up to max_embeds pages, then point to paginator if more
        to_send = pages[:max_embeds]
        for idx, em in enumerate(to_send, start=1):
            # annotate page count when sending multiple
            em.set_footer(text=(em.footer.text or "") + (f" • Page {idx}/{len(pages)}"))
            await interaction.followup.send(embed=em)
        if len(pages) > len(to_send):
            await interaction.followup.send(
            f"There are **{len(pages) - len(to_send)}** more page(s). Rerun with `mode: full` (default) to use the paginator.")

    # --- Prefix command (quick summary) ---
    @commands.command(name="define", aliases=["def"])
    @commands.cooldown(3, 10, BucketType.user)
    async def define_prefix(self, ctx: commands.Context, *, query: str):
        """
        Quick prefix lookup: `!define <word>` or `!define <word> <pos>`
        Returns a concise embed. For full results, use /define.
        """
        q = (query or "").strip()
        if not q:
            await ctx.send("Usage: !define <word> [part-of-speech]")
            return
        parts = q.split()
        word = parts[0]
        pos_filter: Optional[str] = None
        if len(parts) > 1:
            pf = normalize_pos(" ".join(parts[1:]))
            # accept either canonical or known alternates
            if pf in CANON_POS.values() or pf in CANON_POS.keys():
                pos_filter = CANON_POS.get(pf, pf)
        data = await self.fetch_definition(word.lower())
        if not data:
            await ctx.send("Lookup failed.")
            return
        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            title = err.get("title", "Error")
            msg = err.get("message") or err.get("resolution") or "No details provided."
            await ctx.send(embed=discord.Embed(title=title, description=msg, color=discord.Color.red()))
            return
        by_pos, phonetics, sources = self.fold_entries(data) # type: ignore[arg-type]
        if pos_filter:
            by_pos = {k: v for (k, v) in by_pos.items() if normalize_pos(k) == pos_filter}
            if not any(by_pos.values()):
                await ctx.send(f"No definitions found for part of speech: **{pos_filter}**.")
                return
        embed = self.build_summary_embed(
            word, by_pos, phonetics, sources, pos_filter=pos_filter, per_pos_limit=5
        )
        # Nudge toward the richer UI for deep dives
        hint = f"Use `/define word:{word}`"
        if pos_filter:
            hint += f" `pos:{pos_filter}`"
        hint += " `mode: full` for all definitions."
        try:
            # If there's room, add a More field; otherwise append to description
            embed.add_field(name="More", value=hint, inline=False)
        except Exception:
            if embed.description:
                embed.description += f"{hint}"
            else:
                embed.description = hint
        await ctx.send(embed=embed)