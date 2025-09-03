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
            max_length=4000,
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
    
    async def resolve_party_entry(guild: discord.Guild, entry: str):
        """Attempt to resolve a party string into a user ID. Fallback to string."""
        name = entry.strip().lstrip("@")
        for member in guild.members:
            if member.name == name or member.display_name == name:
                return member.id
        return name  # fallback to raw string
    
    def format_party(guild: discord.Guild, party):
        if isinstance(party, int):
            member = guild.get_member(party)
            return member.mention if member else f"<@{party}>"
        return party

class DocumentFilingModal(discord.ui.Modal, title="File another document"):
    def __init__(self, bot, case_number:str, case_dict:dict, related_docs:str=None):
        super().__init__()
        self.bot = bot
        self.case_number = case_number
        self.case_dict = case_dict
        if related_docs:
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
        venue = self.case_dict.get("venue")
        channel_id = VENUE_CHANNEL_MAP.get(venue)
        court_channel = self.bot.get_channel(channel_id)
        message = await court_channel.send(
            f"**{self.doc_title.value} - {self.case_number}**\n\n{self.doc_contents.value}"
        )

        new_doc["message_id"] = message.id
        new_doc["channel_id"] = message.channel.id

        save_json(COURT_FILE, self.bot.get_cog("SpideyCourts").court_data)

        await interaction.response.send_message(f"✅ Document filed as docket entry #{entry_num}.", ephemeral=True)

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

        # Try deleting the previous message
        system_data = load_json(SYSTEM_FILE)
        last_msg_id = system_data.get("last_ongoing_cases_msg_id")
        if last_msg_id:
            try:
                old_msg = await channel.fetch_message(last_msg_id)
                await old_msg.delete()
            except discord.NotFound:
                pass  # Already deleted or never sent

        # Compose new message
        ongoing_cases = [
            case_number for case_number, data in self.court_data.items()
            if data.get('status') != 'closed'
        ]
        if not ongoing_cases:
            return

        message = "**Ongoing Court Cases:**\n"
        for case_number in ongoing_cases:
            case_data = self.court_data[case_number]
            guild = channel.guild
            try:
                plaintiff = await guild.fetch_member(case_data["plaintiff"])
                defendant = await guild.fetch_member(case_data["defendant"])
                plaintiff_name = plaintiff.display_name
                defendant_name = defendant.display_name
            except Exception:
                plaintiff_name = str(case_data["plaintiff"])
                defendant_name = str(case_data["defendant"])

            latest = case_data['filings'][-1] if case_data.get('filings') else {}
            message += f"- `{plaintiff_name}` v. `{defendant_name}`, {case_number} (Most recent: {latest.get('document_type', 'Unknown')})\n"

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
        await interaction.response.send_message("Your application has been submitted and is pending review.", ephemeral=True)
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

        case_data = self.court_data[case_number]
        if not case_data:
            await interaction.response.send_message("No case data found for that case number.", ephemeral=True)
            return
        
        related_doc_reqs = ["motion", "response", "reply", "countermotion", "amended", "supplemental"]
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
        if defendant.id not in valid_parties:
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

    
    @court.command(name="order", description="Issue an Order / Opinion (and optionally resolve a motion).")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        case_number="Case number (e.g., 1:25-cv-000001-SS)",
        order_type="Order, Opinion, or Opinion & Order",
        text="Body of the order/opinion",
        related_entry="Optional: Docket entry this resolves (e.g., a motion)",
        outcome="Optional: Result (Granted, Denied, Partial, Other)"
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
        text: str,
        related_entry: int | None = None,
        outcome: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        # Post to venue
        venue_id = VENUE_CHANNEL_MAP.get(case.get("venue"))
        venue_ch = self.bot.get_channel(venue_id)
        if not venue_ch:
            return await interaction.followup.send("❌ Venue channel not found.", ephemeral=True)

        header = f"**{order_type.value} — {case_number}**"
        if related_entry:
            header += f"\n(Related to Entry {related_entry}" + (f", Outcome: {outcome.value})" if outcome else ")")

        msg = await venue_ch.send(f"{header}\n\n{text}")

        # Add to docket
        filings = case.setdefault("filings", [])
        entry = len(filings) + 1
        filings.append({
            "entry": entry,
            "document_type": order_type.value,
            "author": interaction.user.name,
            "author_id": interaction.user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": msg.id,
            "channel_id": venue_ch.id,
            "related_docs": ([related_entry] if related_entry else []),
            "content": (f"Outcome: {outcome.value}" if outcome else None)
        })

        # If resolving a motion, mark it resolved (non-breaking; ignored if not found)
        if related_entry:
            for d in filings:
                if d.get("entry") == related_entry:
                    d["resolved"] = True
                    if outcome:
                        d["ruling_outcome"] = outcome.value
                    break

        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ {order_type.value} filed as docket entry #{entry}.", ephemeral=True)


    @court.command(name="enter_judgment", description="Enter final judgment and close the case.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    @app_commands.describe(
        case_number="Case number",
        text="Judgment text (e.g., Dismissed with prejudice; costs to Plaintiff)"
    )
    @app_commands.autocomplete(case_number=case_autocomplete)
    async def enter_judgment(self, interaction: discord.Interaction, case_number: str, text: str):
        await interaction.response.defer(ephemeral=True)

        case = self.court_data.get(case_number)
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)

        steps = self.bot.get_channel(COURT_STEPS_CHANNEL_ID)
        msg = None
        if steps:
            msg = await steps.send(f"⚖️ **Judgment Entered**\n\n`{case_number}`\n{text}")

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
            "content": text
        })

        case["status"] = "closed"
        save_json(COURT_FILE, self.court_data)
        await interaction.followup.send(f"✅ Judgment entered (Entry {entry}). Case marked **closed**.", ephemeral=True)

    
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

