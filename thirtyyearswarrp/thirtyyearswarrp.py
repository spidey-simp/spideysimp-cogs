from __future__ import annotations
import json, os
from collections import defaultdict
from typing import Dict, Any, List, Tuple

import discord
from discord import app_commands
from redbot.core import commands

from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import random, math

from copy import deepcopy

def deep_merge(base: dict, overlay: dict) -> dict:
    out = deepcopy(base)
    for k, v in (overlay or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


GM_ID = 684457913250480143

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FILE = os.path.join(BASE_DIR, "static.json")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
SEED_FILE = os.path.join(BASE_DIR, "seed_dynamic.json")


RELIGION_COLORS = {
    "Protestant": "#1f77b4",
    "Catholic": "#be9200",
    "Muslim": "#04811b",
}

SCHEMA_VERSION = 1  # bump when you add new keys with special handling

def ensure_root_meta(dynamic: Dict[str, Any]):
    meta = dynamic.setdefault("_meta", {})
    if "schema_version" not in meta:
        meta["schema_version"] = SCHEMA_VERSION
    if "bootstrap_done" not in meta:
        meta["bootstrap_done"] = False


def load_json(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}




def save_json(file_path: str, data: Dict[str, Any]) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

modifier_key_defaults = {
    "owner_id": None,                 # Discord user ID of the player (or None for NPCs)

    # Economy
    "treasury": 100,
    "debt": 0,
    "income_base": 30,                 # flat income before modifiers
    "upkeep_base": 15,                 # flat admin/upkeep
    "net_revenue_last_turn": 0,        # computed each EoT (for UI only)
    "harvest": 100,

    # Internal
    "stability": 0,
    "civil_unrest": 0,
    "war_support": 0,                  # will/mood to keep fighting
    "war_exhaustion": 0,               # fatigue from fighting

    # Force readiness & empire management
    "organization": 70,                # avg troop organization (0–100)
    "overextension": 0,                # admin strain score (see formula below)

    # Demography
    "population": 0,
    "manpower": 0,
    "manpower_recovery": 5,          # per-turn manpower recovery rate (% of max)

    # Religion mix (%)
    "religion": {"Catholic": 0, "Protestant": 0, "Muslim": 0},

    # Production & forces
    "build_points": 3,                 # per-turn generic production
    "build_focus": "balanced",         # naval | siege | army | economy | religion | balanced
    "unit_pool": {                     # standing forces
        "infantry": 0, "cavalry": 0, "artillery": 0,
        "warships": 0, "galleys": 0, "transports": 0
    },
    "merc_pool": {                     # mercenaries tracked separately
        "infantry": 0, "cavalry": 0, "artillery": 0
    },
    "merc_unpaid_strikes": 0,          # consecutive turns you couldn’t pay merc upkeep
    "queue": [],
    "recruitment_cap_land": 3,      # max land units you can recruit per turn
    "recruitment_cap_naval": 2,     # max naval units you can recruit per turn
    "general_average_skill": 0,        # 0–10
    "admiral_average_skill": 0,        # 0–10

    # Stances & special mandates
    "military_posture": "balanced",    # strength | efficiency | hunker_down | siege_warfare | balanced
    "papal_charge_active": False,      # only for Catholics, toggled by GM
    "papal_charge_turns": 0,           # remaining turns of charge

    # Soft power & meta
    "papal_favor": 0,                  # 0–100 (Catholics care)
    "hre_standing": 0,                 # −100…100 (claim to Emperor, goodwill)
    "prestige": 0,                     # −100…100
    # (Optional inputs for overextension)
    "non_core_regions": 0,                   # your count of non-core regions
    "core_regions": 0,                 # how many are your cores
    "colonial_holdings": 0,
    "admin_cap": 6,                     # how many regions before strain
    # Leadership & legitimacy
    "council_competence": 50,      # 0–100; Richelieu-style brains = more efficient state
    "sovereign_authority": 60,     # 0–100; monarchy legitimacy / republican authority analog

    # Defense & logistics
    "fort_network": 1,             # 0..5 aggregate fortification level (national)
    "logistics": 0,                # - attrition / - org loss on movement (simple buff)

    # Force management
    "force_cap": 12,               # soft cap for total standing land units (incl. mercs)

    # Catholic hooks
    "excommunicated": False,       # toggle by GM/Pope events (affects diplomacy/UI)

    # War economy feedback
    "blockade_pressure_last_turn": 0,  # 0–100 computed each EoT; hits income/exhaustion

    # Elastic narrative flags (future events won’t need schema changes)
    "event_flags": {},              # dict of toggles/counters, e.g. {"cathedral_build":2}
    "temporary_national_spirits": [], #list of dicts
    "new_history": {},

    "landlocked": False,
}

MODIFIER_CAPS = {
  "stability_base": 0,
  "war_support_base": 0,
  "growth_rates": {
    "religion_base": 0.0,
    "religion_cap_per_turn": 2.0
  },
  "rolls": {
    "success_threshold": 50,
    "extreme_margin": 25
  },
  "caps": {
    "stability_min": -50,
    "stability_max": 50,
    "war_support_min": -20,
    "war_support_max": 100,
    "civil_unrest_min": 0,
    "civil_unrest_max": 20,
    "war_exhaustion_min": 0,
    "war_exhaustion_max": 100,
    "logistics_min": -10,
    "logistics_max": 10
  }

}


def coerce_value(key: str, raw: str):
        """Turn a slash-command string into the right python type based on key."""
        raw = raw.strip()
        # Try JSON first (so users can pass {"Catholic":90,"Protestant":10,"Muslim":0})
        try:
            val = json.loads(raw)
            return val
        except Exception:
            pass
        # Try numbers/bools
        if raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw  # fallback to string

def ensure_country_defaults(static: Dict[str, Any], dynamic: Dict[str, Any], country_key: str):
        if country_key not in dynamic:
            dynamic[country_key] = {}
        for k, default in modifier_key_defaults.items():
            if k not in dynamic[country_key]:
                # Deep copy dict defaults so we don't share references
                dynamic[country_key][k] = json.loads(json.dumps(default))

def make_religion_pie(rel_mix: Dict[str, float]) -> BytesIO:
    """Return a PNG pie chart buffer from a {religion: percent} dict."""
    labels, sizes, colors = [], [], []
    total = sum(max(0, float(v)) for v in rel_mix.values()) or 1.0
    for name, val in rel_mix.items():
        v = max(0.0, float(val))
        pct = 100.0 * v / total
        if pct <= 0.1:
            continue  # hide tiny slivers
        labels.append(f"{name} ({pct:.0f}%)")
        sizes.append(pct)
        colors.append(RELIGION_COLORS.get(name, "#888888"))

    # avoid empty chart
    if not sizes:
        labels, sizes, colors = ["No Data"], [100], ["#666666"]

    fig, ax = plt.subplots(figsize=(4.8, 4.8), dpi=200)
    wedges, _ = ax.pie(sizes, labels=None, colors=colors, startangle=90, wedgeprops=dict(width=0.5))
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8)
    ax.axis('equal')

    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf
# --- VIEW: show a country summary + religion pie ---------------------------

def fuzz_numeric(val: float | int, low_pct: int = 5, high_pct: int = 5) -> tuple[float, float]:
        """Return a (low, high) fuzzy band around val by ±% for non-owners."""
        # guard against zero: fuzz a tiny visible band
        base = float(val) if isinstance(val, (int, float)) else 0.0
        min_variation = random.uniform(-low_pct/100.0, -0.01)
        max_variation = random.uniform(0.01,  high_pct/100.0)
        low  = base * (1.0 + min_variation)
        high = base * (1.0 + max_variation)
        # keep ordering sane if base < 0
        lo, hi = (min(low, high), max(low, high))
        return (lo, hi)

def mask_value_for_viewer(val: Any) -> str:
        """Human-friendly masking for non-owners."""
        if isinstance(val, (int, float)):
            lo, hi = fuzz_numeric(val, 5, 5)
            # format smartly (ints stay ints, small floats to 1dp)
            def fmt(x):
                if abs(x) >= 1000:
                    return f"{int(round(x)):,}"
                if abs(x - int(x)) < 1e-6:
                    return f"{int(x)}"
                return f"{x:.1f}"
            return f"{fmt(lo)}–{fmt(hi)}"
        if isinstance(val, str):
            return "Unknown"
        if isinstance(val, dict):
            # fuzz dict of numerics (like religion breakdown)
            items = []
            for k, v in val.items():
                if isinstance(v, (int, float)):
                    lo, hi = fuzz_numeric(v, 5, 5)
                    items.append(f"{k}: ~{int(round((lo+hi)/2))}")
            return ", ".join(items) if items else "Unknown"
        return "Unknown"

# ----- Topic choices -----
TOPIC_CHOICES = [
    app_commands.Choice(name="Overview", value="overview"),
    app_commands.Choice(name="Politics", value="politics"),
    app_commands.Choice(name="Religion", value="religion"),
    app_commands.Choice(name="Military", value="military"),
    app_commands.Choice(name="Economy", value="economy"),
    app_commands.Choice(name="Spirits", value="spirits"),
    app_commands.Choice(name="History", value="history"),
]

def get_all_spirits(static_c: Dict[str, Any], dyn: Dict[str, Any]) -> list[dict]:
    """Combine static national_spirits with dynamic temporary_national_spirits."""
    static_list = static_c.get("national_spirits", []) or []
    temp_list   = dyn.get("temporary_national_spirits", []) or []
    # Tag each with a source for display clarity
    out = []
    for s in static_list:
        s2 = dict(s)
        s2["_source"] = "static"
        out.append(s2)
    for s in temp_list:
        s2 = dict(s)
        s2.setdefault("visible", True)
        s2["_source"] = "temporary"
        out.append(s2)
    return out

def render_spirits_embed(country_name: str, spirits: list[dict], is_owner: bool) -> discord.Embed:
    e = discord.Embed(title=f"{country_name} – National Spirits", color=discord.Color.purple())
    if not spirits:
        e.description = "No active national spirits."
        return e

    def fmt_effect(eff: dict) -> str:
        # keep it short, we just show the gist
        phase = eff.get("phase", "?")
        scope = eff.get("scope", "?")
        key   = eff.get("key", "?")
        op    = eff.get("op", "?")
        val   = eff.get("value", "?")
        return f"`{phase}` · `{scope}` · **{key} {op} {val}**"

    for s in spirits:
        if not s.get("visible", True) and not is_owner:
            # hide invisible spirits from non-owners
            continue
        name = s.get("name", "Unnamed")
        src  = s.get("_source", "static")
        desc = s.get("description", "")
        tags = s.get("tags", [])
        effects = s.get("effects", [])
        suffix = " (Temporary)" if src == "temporary" else ""
        block = []
        if desc: block.append(desc)
        if tags: block.append(f"*Tags:* `{', '.join(tags)}`")
        if effects:
            shown = [fmt_effect(eff) for eff in effects[:5]]
            block.append("\n".join(shown))
            if len(effects) > 5:
                block.append(f"…and {len(effects) - 5} more effects")
        e.add_field(name=f"**{name}**{suffix}", value="\n".join(block) or "—", inline=False)
    return e

def render_history_embed(country_name: str, static_c: Dict[str, Any], dyn: Dict[str, Any], max_entries:int=10) -> discord.Embed:
    e = discord.Embed(title=f"{country_name} – History", color=discord.Color.dark_teal())
    # merge static history + dynamic new_history
    h_static = static_c.get("history", {}) or {}
    h_dyn    = dyn.get("new_history", {}) or {}
    # keys can be year strings; try sorting numerically then lexicographically
    items = []
    for k, v in {**h_static, **h_dyn}.items():
        try:
            yr = int(str(k).split()[0])
        except:
            yr = 0
        items.append((yr, str(k), v))
    items.sort(key=lambda t: (t[0], t[1]))
    if not items:
        e.description = "No recorded history."
        return e
    lines = [f"**{k}** — {v}" for _, k, v in items[-max_entries:]]
    e.description = "\n".join(lines)
    return e

def add_politics_fields(e: discord.Embed, dyn: dict, is_owner: bool, mask) -> None:
    def show(lbl, key, inline=True):
        val = dyn.get(key)
        e.add_field(name=lbl, value=(val if is_owner else mask(val)), inline=inline)

    show("Papal Favor", "papal_favor")
    show("HRE Standing", "hre_standing")
    show("Prestige", "prestige")
    show("Sovereign Authority", "sovereign_authority")
    show("Council Competence", "council_competence")
    show("Excommunicated", "excommunicated")
    show("Military Posture", "military_posture")

def add_military_fields(e: discord.Embed, dyn: dict, is_owner: bool, mask) -> None:
    show = lambda lbl, key, inline=True: e.add_field(name=lbl, value=(dyn.get(key) if is_owner else mask(dyn.get(key))), inline=inline)
    show("Organization", "organization")
    show("Force Cap", "force_cap")
    show("Generals (avg)", "general_average_skill")
    show("Admirals (avg)", "admiral_average_skill")
    # Unit pools
    up = dyn.get("unit_pool", {})
    mp = dyn.get("merc_pool", {})
    if up:
        e.add_field(name="Standing Forces", value=", ".join(f"{k}:{v}" for k,v in up.items()), inline=False)
    if mp:
        e.add_field(name="Mercenaries", value=", ".join(f"{k}:{v}" for k,v in mp.items()), inline=False)

def add_economy_fields(e: discord.Embed, dyn: dict, is_owner: bool, mask) -> None:
    show = lambda lbl, key, inline=True: e.add_field(name=lbl, value=(dyn.get(key) if is_owner else mask(dyn.get(key))), inline=inline)
    show("Treasury", "treasury")
    show("Debt", "debt")
    show("Last Turn Net", "net_revenue_last_turn")
    show("Income (base)", "income_base")
    show("Upkeep (base)", "upkeep_base")
    show("Harvest", "harvest")
    show("Blockade Pressure (last)", "blockade_pressure_last_turn")
    # Admin/overextension bits:
    show("Overextension", "overextension")
    show("Core Regions", "core_regions")
    show("Non-Core Regions", "non_core_regions")
    show("Colonial Holdings", "colonial_holdings")
    show("Admin Capacity", "admin_cap")

def add_religion_fields(e: discord.Embed, rel_mix: dict, is_owner: bool, mask) -> None:
    if is_owner:
        parts = [f"{k}: {int(v)}%" for k, v in rel_mix.items() if v]
        if parts:
            e.add_field(name="Breakdown", value=", ".join(parts), inline=False)
    else:
        e.add_field(name="Summary", value=mask(rel_mix) or "Unknown", inline=False)

def bootstrap_from_seed(static: Dict[str, Any], dynamic: Dict[str, Any], seed: Dict[str, Any]) -> list[str]:
    applied = []
    seed_c = (seed or {}).get("countries", {})
    for ckey, overrides in seed_c.items():
        if ckey not in static.get("countries", {}):
            continue
        dyn = dynamic.get(ckey)
        if dyn and dyn.get("_bootstrap_done"):
            continue
        base = deepcopy(modifier_key_defaults)
        seeded = deep_merge(base, overrides or {})
        dynamic[ckey] = deep_merge(seeded, dyn or {})  # dynamic wins if present
        dynamic[ckey]["_bootstrap_done"] = True
        applied.append(ckey)
    return applied


# ---- Tunables (top-level) ----
ADMIN_CAP_MIN = 6
ADMIN_CAP_MAX = 25

CORE_TO_CAP = 0.25              # +1 cap per 4 core regions
COLONIAL_TO_CAP_PENALTY = 1/12  # −1 cap per 12 colonial holdings
COLONIAL_TO_NONCORE = 1/3       # every 3 colonial holdings counts as +1 effective non-core

COMPETENCE_TO_CAP = 1/12        # baseline 50
AUTHORITY_TO_CAP  = 1/12        # baseline 60
STABILITY_TO_CAP  = 1/20

def compute_admin_cap(core_regions:int, colonial_holdings:int,
                      council_competence:int, sovereign_authority:int,
                      stability:int) -> int:
    base = round(core_regions * CORE_TO_CAP)
    comp_bonus = round((council_competence - 50) * COMPETENCE_TO_CAP)
    auth_bonus = round((sovereign_authority - 60) * AUTHORITY_TO_CAP)
    stab_bonus = round(stability * STABILITY_TO_CAP)
    colonial_pen = int(colonial_holdings * COLONIAL_TO_CAP_PENALTY)  # floor
    cap = base + comp_bonus + auth_bonus + stab_bonus - colonial_pen
    return max(ADMIN_CAP_MIN, min(ADMIN_CAP_MAX, cap))

def compute_overextension(non_core_regions:int, colonial_holdings:int,
                          admin_cap:int) -> int:
    effective_non_core = non_core_regions + int((colonial_holdings * COLONIAL_TO_NONCORE + 0.9999))  # ceil
    return max(0, effective_non_core - admin_cap)

def recompute_capacity_block(self, country_key:str) -> None:
    dyn = self.dynamic_data[country_key]
    # Pull inputs (use defaults if missing)
    core_regions        = int(dyn.get("core_regions", 0))
    non_core_regions    = int(dyn.get("non_core_regions", 0))
    colonial_holdings   = int(dyn.get("colonial_holdings", 0))
    council_competence  = int(dyn.get("council_competence", 50))
    sovereign_authority = int(dyn.get("sovereign_authority", 60))
    stability           = int(dyn.get("stability", 0))

    admin_cap = compute_admin_cap(core_regions, colonial_holdings,
                                  council_competence, sovereign_authority, stability)
    overext   = compute_overextension(non_core_regions, colonial_holdings, admin_cap)

    # Store for UI; treat as ephemeral (always overwritten by this function)
    dyn["admin_cap"]     = admin_cap
    dyn["overextension"] = overext

def bootstrap_recompute_all(self) -> None:
    for c in self.static_data.get("countries", {}):
        if c in self.dynamic_data:
            recompute_capacity_block(self, c)





class ThirtyYearsWarRP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.static_data = load_json(STATIC_FILE)

        self.dynamic_data = load_json(DATA_FILE)
        bootstrap_recompute_all(self)

    async def cog_unload(self):
        save_json(DATA_FILE, self.dynamic_data)
    
    tyw = app_commands.Group(name="tyw", description="Commands related to the Thirty Years' War RP.")
    gm = app_commands.Group(name="gm", description="Game Master commands.", parent=tyw, default_permissions=discord.Permissions(administrator=True))
    view = app_commands.Group(name="view", description="View game data.", parent=tyw)

    async def country_name_autocomplete(self, interaction:discord.Interaction, current:str) -> List[app_commands.Choice[str]]:
        choices = [
            app_commands.Choice(name=country, value=country)
            for country in self.static_data.get("countries", {}).keys()
            if current.lower() in country.lower()
        ]
        return choices[:25]
    
    async def data_key_autocomplete(self, interaction:discord.Interaction, current:str) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=key.title(), value=key)
            for key in modifier_key_defaults.keys()
            if current.lower() in key.lower()
        ][:25]


    # --- GM: initialize dynamic data from static -------------------------------

    @gm.command(name="init", description="Initialize data.json with defaults for any missing countries/keys.")
    @app_commands.checks.has_permissions(administrator=True)
    async def gm_init(self, interaction: discord.Interaction):
        static_countries = self.static_data.get("countries", {})
        for ckey in static_countries.keys():
            ensure_country_defaults(self.static_data, self.dynamic_data, ckey)
        save_json(DATA_FILE, self.dynamic_data)
        await interaction.response.send_message("✅ Initialized dynamic data for all countries.", ephemeral=True)

    # --- GM: set a key on a country -------------------------------------------

    @gm.command(name="country_data_set", description="Set or update country data manually.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(country="Country key (matches static.json)", key="Data key to set (e.g., treasury, stability, religion)", value="Value (number/bool/string or JSON for dicts)")
    @app_commands.autocomplete(country=country_name_autocomplete, key=data_key_autocomplete)
    async def gm_country_data_set(self, interaction: discord.Interaction, country: str, key: str, value: str):
        static_countries = self.static_data.get("countries", {})
        if country not in static_countries:
            return await interaction.response.send_message(f"❌ Unknown country key: `{country}`", ephemeral=True)

        ensure_country_defaults(self.static_data, self.dynamic_data, country)

        if key not in modifier_key_defaults:
            return await interaction.response.send_message(f"❌ Unknown key `{key}`. Valid: {', '.join(modifier_key_defaults.keys())}", ephemeral=True)

        coerced = coerce_value(key, value)

        # Merge for dict-types (e.g., religion), overwrite otherwise
        if isinstance(modifier_key_defaults[key], dict):
            if not isinstance(coerced, dict):
                return await interaction.response.send_message("❌ For dict keys (e.g., `religion`) provide JSON like `{\"Catholic\":90,\"Protestant\":10}`.", ephemeral=True)
            self.dynamic_data[country][key].update(coerced)
        else:
            self.dynamic_data[country][key] = coerced

        save_json(DATA_FILE, self.dynamic_data)
        pretty = json.dumps(self.dynamic_data[country][key], indent=2) if isinstance(self.dynamic_data[country][key], dict) else self.dynamic_data[country][key]
        await interaction.response.send_message(f"✅ `{country}` `{key}` set to:\n```{pretty}```", ephemeral=True)

    

    @view.command(name="country", description="View a country by topic (overview, politics, religion, military, economy, spirits, history).")
    @app_commands.describe(country="Country key to view", topic="Which topic to view")
    @app_commands.autocomplete(country=country_name_autocomplete)
    @app_commands.choices(topic=TOPIC_CHOICES)
    async def view_country(self, interaction: discord.Interaction, country: str, topic: app_commands.Choice[str] = None):
        static_c = self.static_data.get("countries", {}).get(country)
        if not static_c:
            return await interaction.response.send_message(f"❌ Unknown country key: `{country}`", ephemeral=True)

        ensure_country_defaults(self.static_data, self.dynamic_data, country)
        dyn = self.dynamic_data.get(country, {})

        is_owner = (interaction.user.id == dyn.get("owner_id")) or interaction.user.id == GM_ID
        chosen = (topic.value if topic else "overview")

        # Base embed shell
        base = discord.Embed(
            title=static_c.get("name", country),
            description=static_c.get("description", "No description."),
            color=discord.Color.gold()
        )
        leader = static_c.get("leader", {}) or {}
        if static_c.get("flag"): base.set_thumbnail(url=static_c["flag"])
        if leader.get("image"):  base.set_image(url=leader["image"])
        base.add_field(name="Leader", value="**{} {}**".format(leader.get('title','').strip(), leader.get('name','').strip()).strip(), inline=True)
        base.add_field(name="Government", value=static_c.get("government","Unknown"), inline=True)
        base.add_field(name="State Religion", value=static_c.get("religion","Unknown"), inline=True)

        embeds = [base]
        files = []

        # convenient alias
        mask = mask_value_for_viewer

        if chosen == "overview":
            # a little of everything + religion pie
            # Quick stats
            def show(lbl, key, inline=True):
                val = dyn.get(key, 0)
                embeds[0].add_field(name=lbl, value=(val if is_owner else mask(val)), inline=inline)
            show("Treasury", "treasury")
            show("Stability", "stability")
            show("War Support", "war_support")
            show("War Exhaustion", "war_exhaustion")
            show("Organization", "organization")
            show("Overextension", "overextension")

            # Religion pie card
            e_relig = discord.Embed(title="Religion Mix", color=discord.Color.blue())
            rel_mix = dyn.get("religion", {"Catholic": 0, "Protestant": 0, "Muslim": 0})
            pie_buf = make_religion_pie(rel_mix)
            pie_file = discord.File(pie_buf, filename="religion_pie.png")
            e_relig.set_image(url="attachment://religion_pie.png")
            add_religion_fields(e_relig, rel_mix, is_owner, mask)
            files.append(pie_file)
            embeds.append(e_relig)

            # Spirits summary
            spirits = get_all_spirits(static_c, dyn)
            embeds.append(render_spirits_embed(static_c.get("name", country), spirits[:6], is_owner))

        elif chosen == "politics":
            e = discord.Embed(title=f"{static_c.get('name', country)} – Politics", color=discord.Color.green())
            add_politics_fields(e, dyn, is_owner, mask)
            embeds.append(e)

        elif chosen == "religion":
            e = discord.Embed(title=f"{static_c.get('name', country)} – Religion", color=discord.Color.blue())
            rel_mix = dyn.get("religion", {"Catholic": 0, "Protestant": 0, "Muslim": 0})
            pie_buf = make_religion_pie(rel_mix)
            pie_file = discord.File(pie_buf, filename="religion_pie.png")
            e.set_image(url="attachment://religion_pie.png")
            add_religion_fields(e, rel_mix, is_owner, mask)
            files.append(pie_file)
            embeds.append(e)

        elif chosen == "military":
            e = discord.Embed(title=f"{static_c.get('name', country)} – Military", color=discord.Color.red())
            add_military_fields(e, dyn, is_owner, mask)
            embeds.append(e)

        elif chosen == "economy":
            e = discord.Embed(title=f"{static_c.get('name', country)} – Economy", color=discord.Color.dark_gold())
            add_economy_fields(e, dyn, is_owner, mask)
            embeds.append(e)

        elif chosen == "spirits":
            spirits = get_all_spirits(static_c, dyn)
            embeds.append(render_spirits_embed(static_c.get("name", country), spirits, is_owner))

        elif chosen == "history":
            embeds.append(render_history_embed(static_c.get("name", country), static_c, dyn, max_entries=20))

        else:
            # fallback to overview
            pass

        await interaction.response.send_message(embeds=embeds, files=files, ephemeral=True)


    # --- VIEW: raw dynamic json for a country (debug) --------------------------

    @view.command(name="raw", description="Debug: show raw dynamic data for a country.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(country="Country key")
    @app_commands.autocomplete(country=country_name_autocomplete)
    async def view_raw(self, interaction: discord.Interaction, country: str):
        ensure_country_defaults(self.static_data, self.dynamic_data, country)
        pretty = json.dumps(self.dynamic_data.get(country, {}), indent=2, ensure_ascii=False)
        await interaction.response.send_message(f"```json\n{pretty}\n```", ephemeral=True)

    @gm.command(name="bootstrap", description="ONE-TIME import of initial per-country state from seed_dynamic.json")
    @app_commands.checks.has_permissions(administrator=True)
    async def gm_bootstrap(self, interaction: discord.Interaction):
        ensure_root_meta(self.dynamic_data)
        if self.dynamic_data["_meta"].get("bootstrap_done"):
            return await interaction.response.send_message("⚠️ Bootstrap already completed. Aborting.", ephemeral=True)

        try:
            seed = load_json(SEED_FILE)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Failed to load seed: {e}", ephemeral=True)

        applied = bootstrap_from_seed(self.static_data, self.dynamic_data, seed)

        # backfill & flag
        for ckey in self.static_data.get("countries", {}):
            ensure_country_defaults(self.static_data, self.dynamic_data, ckey)
            self.dynamic_data[ckey].setdefault("_bootstrap_done", True)

        # ⬇️ recompute after seed is applied
        bootstrap_recompute_all(self)

        self.dynamic_data["_meta"]["bootstrap_done"] = True
        save_json(DATA_FILE, self.dynamic_data)
        await interaction.response.send_message(f"✅ Bootstrap complete for: {', '.join(applied) or 'no specific countries (defaults only)'}", ephemeral=True)

