from __future__ import annotations

import discord
from discord import app_commands
from redbot.core import commands, bank
import math
import random
import json, os
import re
from datetime import datetime
from discord import Embed, Colour, ForumChannel
from discord.utils import get


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ECONOMY_FILE = os.path.join(BASE_DIR, "economy.json")

MALL_FOUNTAIN_CHANNEL = 1436117462075572254
CORP_BULLETIN_CHANNEL = 1436117555713544204
CRAWL_STREET_CHANNEL = 1436122373232267367

def load_economy_data() -> dict:
    if not os.path.exists(ECONOMY_FILE):
        return {}
    with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_economy_data(data: dict) -> None:
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

async def get_forum(guild: discord.Guild, forum_id: int) -> ForumChannel | None:
    ch = guild.get_channel(forum_id)
    return ch if isinstance(ch, ForumChannel) else None

def build_recruit_embed(name, category, par_value, auth_common, auth_pref, founder, thread_url=None):
    e = Embed(
        title=f"Recruiting for {name}",
        description=f"Category: **{category}**\nPar Value: **{par_value}**\n"
                    f"Authorized Shares — Common: **{auth_common}** | Preferred: **{auth_pref or 0}**",
                    color=Colour.yellow(),
                    timestamp=datetime.now()
    )
    e.set_footer(text="12 S.R.C. §§ 21–23 recruiting notice")
    if thread_url:
        e.add_field(name="Discuss / Subscribe", value=f"[Crawl Street Thread]({thread_url})", inline=False)
    e.add_field(name="Founder", value=founder.mention, inline=True)
    return e

async def post_recruit_announcements(bot, guild, assoc, founder, cap_table_text):
    forum = await get_forum(guild, CRAWL_STREET_CHANNEL)
    if not forum:
        raise RuntimeError("Crawl Street is not a forum channel.")

    # Create forum post
    post_title = f"{assoc['name']} — Application Thread (Category {assoc['category']})"
    content = (f"**Summary**: {assoc.get('summary','(no summary provided)')}\n"
               f"**Par Value**: {assoc['par_value']}\n"
               f"**Authorized**: Common {assoc['auth_common']}, "
               f"Preferred {assoc.get('auth_pref',0)}\n\n"
               "Use `/bank association join` to subscribe shares.\n"
               "Bylaws may be added with `/bank association bylaws set`.")
    # Optional: apply tags if you've created them in the forum
    applied_tags = [t for t in forum.available_tags if t.name == "Recruiting"]
    thread = await forum.create_thread(name=post_title, content=content, applied_tags=applied_tags or None)

    # Pin a Cap Table message
    cap_msg = await thread.send(content=cap_table_text)
    await cap_msg.pin()

    # Cross-post to Corporate Bulletin
    bulletin = guild.get_channel(CORP_BULLETIN_CHANNEL)
    embed = build_recruit_embed(
        assoc["name"], assoc["category"], assoc["par_value"],
        assoc["auth_common"], assoc.get("auth_pref"), founder, thread_url=thread.thread.jump_url
    )
    bulletin_msg = await bulletin.send(embed=embed)

    # Optional: link-drop in Mall Fountain
    fountain = guild.get_channel(MALL_FOUNTAIN_CHANNEL)
    await fountain.send(f"🕷️ New bank application posted: {thread.thread.jump_url}")

    # Persist ids back to your DB
    return {
        "forum_post_id": thread.thread.id,
        "cap_msg_id": cap_msg.id,
        "bulletin_msg_id": bulletin_msg.id
    }

def render_cap_table(subscriptions, par_value):
    # subscriptions: list of {user, class, shares}
    total_common = sum(s["shares"] for s in subscriptions if s["class"] == "common")
    total_pref   = sum(s["shares"] for s in subscriptions if s["class"] == "preferred")
    holders = sorted(subscriptions, key=lambda s: s["shares"], reverse=True)[:10]
    lines = [f"**Cap Table (Top Holders)**",
             *(f"- {s['user'].mention}: {s['shares']} {s['class']} (est. {s['shares']*par_value} SC)"
               for s in holders),
             "",
             f"**Totals** — Common: **{total_common}** | Preferred: **{total_pref}** | "
             f"Par Value: **{par_value} SC**"]
    return "\n".join(lines)

class SpideyEconomy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.economy_data = load_economy_data()
    
    async def cog_unload(self) -> None:
        save_economy_data(self.economy_data)

    
    bank = app_commands.Group(name="bank", description="Bank related commands")
    credit = app_commands.Group(name="credit", description="Credit related commands", parent=bank)
    manage = app_commands.Group(name="manage", description="Manage your bank accounts", parent=bank)
    association = app_commands.Group(name="association", description="Bank association commands", parent=bank)


    @credit.command(name="score", description="Get your credit score")
    async def credit_score(self, interaction: discord.Interaction) -> None:
        user_id = str(interaction.user.id)
        self.economy_data.setdefault(user_id, {"credit_score": {"SpideyFax": random.randint(650, 750), "EclipseUnion": random.randint(650, 750), "ExperiLego": random.randint(650, 750)},
                                               "credit_age": datetime.now().isoformat()})
        credit_score = self.economy_data[user_id]["credit_score"]
        count = 0
        for bureau in credit_score:
            count += credit_score[bureau]
        average_score = count / len(credit_score)
        await interaction.response.send_message(f"Your credit score is: `{average_score}`\n"
                                                "Bureau Scores:\n"
                                                f"  SpideyFax: {credit_score['SpideyFax']}\n"
                                                f"  EclipseUnion: {credit_score['EclipseUnion']}\n"
                                                f"  ExperiLego: {credit_score['ExperiLego']}", ephemeral=True)
    
    @bank.command(name="total_balance", description="Get your total bank balance across all accounts")
    async def total_balance(self, interaction: discord.Interaction) -> None:
        user_id = str(interaction.user.id)
        self.economy_data.setdefault(user_id, {"accounts": {}})
        accounts = self.economy_data[user_id]["accounts"]
        account_values = []
        if accounts:
            for account, info in accounts.items():
                total_balance += info.get("balance", 0)
                bank_company=info.get("company", "Unnamed Account")
                type=info.get("type", "Unknown Type")
                account_values.append(f"{bank_company} ({type} Account): ${info.get('balance', 0):,.2f}")
        bank_balance = await bank.get_balance(interaction.user)
        account_values.append(f"Non-Bank Balance: ${bank_balance:,.2f}")
        total_balance = bank_balance
        await interaction.response.send_message(f"Your total bank balance is: ${total_balance:,.2f}\n"
                                                "Account Details:\n"
                                                f"  {'\n  '.join(account_values)}", ephemeral=True)
    
    async def account_autocomplete(self, interaction: discord.Interaction, current:str):
        current = current.lower()
        user_id = str(interaction.user.id)
        self.economy_data.setdefault(user_id, {"accounts": {}})
        accounts = self.economy_data[user_id]["accounts"]
        if not accounts:
            return []
        choices = []
        red_balance = await bank.get_balance(interaction.user)
        choices.append(app_commands.Choice(name=f"Non-Bank Balance: ${red_balance:,.2f}", value="non_bank"))
        for account, info in accounts.items():
            bank_company = info.get("company", "Unnamed Account")
            type = info.get("type", "Unknown Type")
            balance = info.get("balance", 0)
            if current in bank_company.lower():
                title = f"{bank_company} ({type} Account) - Balance: ${balance:,.2f}"
                choices.append(app_commands.Choice(name=title, value=account))
        return choices[:25]
    
    async def pull_funds(self, member: discord.Member, amount: float) -> bool:
        """Try to cover `amount` first from Red non-bank balance, then from user's bank accounts.
        Returns True if fully covered and deducts balances in-place."""
        remaining = float(amount)
        # 1) Try Red bank (non-bank balance)
        red_bal = await bank.get_balance(member)
        use_red = min(red_bal, remaining)
        if use_red > 0:
            await bank.withdraw(member, use_red)
            remaining -= use_red
            if remaining <= 0:
                return True

        # 2) Waterfall across user's own accounts (sorted by biggest balance first)
        uid = str(member.id)
        user = self.economy_data.setdefault(uid, {"accounts": {}})
        accts = user["accounts"]
        for acct_id, info in sorted(accts.items(), key=lambda kv: kv[1].get("balance", 0), reverse=True):
            bal = info.get("balance", 0.0)
            if bal <= 0:
                continue
            take = min(bal, remaining)
            info["balance"] = bal - take
            remaining -= take
            if remaining <= 0:
                return True
        return False


    @manage.command(name="open_bank", description="Open a bank corporation.")
    @app_commands.describe(company="The name of the bank corporation", type="Such as LLC, Inc., etc.", bank_type="The primary type of banking services offered", category="The Category to form it in.", funding_account="The account to fund the opening.")
    @app_commands.choices(type=[
        app_commands.Choice(name="LLC", value="llc"),
        app_commands.Choice(name="Inc.", value="inc"),
        app_commands.Choice(name="Credit Union", value="credit_union"),
        app_commands.Choice(name="Savings & Loan", value="savings"),
        app_commands.Choice(name="Community Bank", value="community_bank"),
    ],
    category=[
        app_commands.Choice(name="Commons", value="commons"),
        app_commands.Choice(name="Gaming", value="gaming"),
        app_commands.Choice(name="Crazy Times", value="crazy_times"),
        app_commands.Choice(name="User-Themed", value="user_themed"),
    ],
    bank_type=[
        app_commands.Choice(name="Retail Banking", value="retail"),
        app_commands.Choice(name="Commercial Banking", value="commercial"),
        app_commands.Choice(name="Investment Banking", value="investment"),
        app_commands.Choice(name="Private Banking", value="private"),
    ]
    )
    @app_commands.autocomplete(funding_account=account_autocomplete)
    async def open_bank(self, interaction: discord.Interaction, company: str, type: str="inc", bank_type: str="retail", category: str="commons", funding_account: str="non_bank") -> None:
        founder = interaction.user
        MIN_EQUITY = 5_000.0  # charter capital requirement

        # Check total liquid funds first (non-bank + owned accounts)
        uid = str(founder.id)
        user = self.economy_data.setdefault(uid, {"accounts": {}})
        accts = user["accounts"]
        red_bal = await bank.get_balance(founder)
        sub_bal = sum(a.get("balance", 0.0) for a in accts.values())
        if red_bal + sub_bal < MIN_EQUITY:
            return await interaction.followup.send(
                f"You need at least ${MIN_EQUITY:,.2f} in equity to charter a bank. "
                f"Current available: ${red_bal + sub_bal:,.2f}.", ephemeral=True
            )

        # Pull funds (waterfall)
        ok = await self.pull_funds(founder, MIN_EQUITY)
        if not ok:
            return await interaction.followup.send("Could not collect the charter capital.", ephemeral=True)

        # Create bank entity
        banks = self.economy_data.setdefault("banks", {})
        bank_id = re.sub(r"[^A-Za-z0-9]+", "_", company).strip("_").lower()
        if bank_id in banks:
            return await interaction.followup.send("A bank with that name already exists.", ephemeral=True)

        banks[bank_id] = {
            "name": company,
            "type": type,
            "category": category,
            "bank_type": bank_type,
            "owners": {uid: 1.0},  # 100% founder ownership (adjust if you add IPO)
            "tier1_capital": MIN_EQUITY,
            "reserves": MIN_EQUITY,   # credited at SCB
            "deposits": 0.0,
            "loans": 0.0,
            "created_at": datetime.utcnow().isoformat()
        }
        # Also open the founder a checking acct at the new bank (optional)
        user["accounts"][f"{bank_id}:checking"] = {"company": company, "type": "checking", "balance": 0.0}

        save_economy_data(self.economy_data)
        await interaction.followup.send(
            f"🏦 **{company}** chartered!\n"
            f"- Tier 1 Capital: ${MIN_EQUITY:,.2f}\n- Reserves: ${MIN_EQUITY:,.2f}\n"
            f"- Reserve requirement & lending limits now apply.",
            ephemeral=True
        )
                
