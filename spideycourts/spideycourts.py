import asyncio
import discord
from discord import app_commands
from discord.ext import tasks
from redbot.core import commands
import json
import os
import datetime


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

        new_msg = await channel.send(message)

        # Save new message ID
        system_data["last_ongoing_cases_msg_id"] = new_msg.id
        save_json(SYSTEM_FILE, system_data)


    
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

        docket_text = f"**Docket for Case {plaintiff_name} v. {defendant_name}, {case_number}**\n\n"
        docket_text += f"**Counsel for Plaintiff:** <@{case_data.get('counsel_for_plaintiff', 'Unknown')}>\n"
        docket_text += f"**Counsel for Defendant:** <@{case_data.get('counsel_for_defendant', 'Unknown')}>\n"
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
                    dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts = dt.strftime("%m/%d/%y")
                except Exception:
                    pass
            
            exhibits = []
            for ex in doc.get("exhibits", []):
                ex_link = f"https://discord.com/channels/{interaction.guild.id}/{ex['channel_id']}/{ex['file_id']}"
                exhibits.append(f"  ↳ Exhibit {ex['exhibit_number']}: [{ex['text']}]({ex_link})\n")

            filings.append(
                f"**[{doc.get('entry', 1)}] [{doc.get('document_type', 'Unknown')}]({link})** by {doc.get('author', 'Unknown')} on {ts}\n"
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

    def extract_command_option(self, interaction: discord.Interaction, name: str):
        for opt in interaction.data.get("options", []):
            if opt.get("name") == name:
                return opt.get("value")
        return None


    async def docket_entry_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for docket entry numbers."""
        matches = []
        case_number = ""
        case_number = self.extract_command_option(interaction, "case_number")
        case_data = self.court_data.get(case_number)

        if not case_data:
            return matches

        filings = case_data.get("filings", [])
        for doc in filings:
            if doc.get("author_id") == interaction.user.id:
                entry_num = doc.get("entry")
                if entry_num and str(entry_num).startswith(current):
                    matches.append(app_commands.Choice(name=f"{doc.get('document_type', 'Unknown')} #{entry_num}", value=str(entry_num)))

            if len(matches) >= 25:
                break

        return matches

    @court.command(name="file_exhibit", description="File an exhibit to an existing document")
    @app_commands.describe(
        case_number="Case number (e.g., 1:25-cv-000001-SS)",
        docket_entry="Docket entry number",
        exhibit_desc="Text description of the exhibit",
        exhibit_file="File to upload as an exhibit"
    )
    @app_commands.autocomplete(case_number=case_autocomplete, docket_entry=docket_entry_autocomplete)
    async def file_exhibit(self, interaction:discord.Interaction, case_number: str, docket_entry: int, exhibit_desc: str, exhibit_file: discord.Attachment):
        """File an exhibit to an existing document."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        case_data = self.court_data.get(case_number)
        if not case_data:
            await interaction.followup.send("❌ Case not found.", ephemeral=True)
            return

        filings = case_data.get("filings", [])
        for doc in filings:
            if doc.get("entry") == docket_entry:
                # Save the file to the exhibits channel
                exhibits_channel = self.bot.get_channel(EXHIBITS_CHANNEL_ID)
                if not exhibits_channel:
                        await interaction.followup.send("❌ Exhibits channel not found.", ephemeral=True)
                        return
                
                doc.setdefault("exhibits", [])
                exhibit_num = len(doc["exhibits"]) + 1
                exhibit_msg = await exhibits_channel.send(
                    f"Exhibit #{exhibit_num} for Case {case_number}, Docket Entry #{docket_entry}:\n{exhibit_desc}",
                    file=await exhibit_file.to_file()
                )

                doc["exhibits"].append( {
                    "exhibit_number": f"{docket_entry}-{exhibit_num}",
                    "text": exhibit_desc,
                    "file_url": exhibit_msg.attachments[0].url,
                    "file_id": exhibit_msg.id,
                    "channel_id": exhibits_channel.id,
                    "submitted_by": interaction.user.id,
                    "timestamp": str(datetime.datetime.now().isoformat())
                }
                )

                save_json(COURT_FILE, self.court_data)
                await interaction.followup.send(f"✅ Exhibit #{exhibit_num} filed successfully for Docket Entry #{docket_entry}.", ephemeral=True)
                return

        await interaction.followup.send("❌ Docket entry not found.", ephemeral=True)

    @court.command(name="backfill_author_ids", description="Patch old filings by resolving and saving missing author IDs.")
    @app_commands.checks.has_role(FED_JUDICIARY_ROLE_ID)
    async def backfill_author_ids(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        updated_count = 0
        failed = []

        for case_num, case_data in self.court_data.items():
            if not isinstance(case_data, dict) or "filings" not in case_data:
                continue

            for doc in case_data["filings"]:
                if "author" in doc and "author_id" not in doc:
                    username = doc["author"]
                    member = discord.utils.find(lambda m: m.name == username, interaction.guild.members)
                    if member:
                        doc["author_id"] = member.id
                        updated_count += 1
                    else:
                        failed.append((case_num, doc.get("entry", "?"), username))

        save_json(COURT_FILE, self.court_data)

        response = f"✅ Added `author_id` to {updated_count} filings."
        if failed:
            response += f"\n⚠️ Failed to resolve {len(failed)} docs:\n" + "\n".join(
                [f"• Case {cn}, Entry {e}: '{u}'" for cn, e, u in failed]
            )

        await interaction.followup.send(response, ephemeral=True)
