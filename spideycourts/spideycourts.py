import asyncio
import discord
from discord import app_commands, tasks
from redbot.core import commands
import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COURT_FILE = os.path.join(BASE_DIR, 'courts.json')

SUPREME_COURT_CHANNEL_ID = 1302331990829174896
FIRST_CIRCUIT_CHANNEL_ID = 1400567992726716583
GEN_CHAT_DIST_CT_CHANNEL_ID = 1401700220181549289
GEN_SWGOH_DIST_CT_CHANNEL_ID = 1401721949134258286
PUBLIC_SQUARE_DIST_CT_CHANNEL_ID = 1401722584566861834
FED_JUDICIARY_ROLE_ID = 1401712141584826489
FED_CHAMBERS_CHANNEL_ID = 1401812137780838431

VENUE_CHANNEL_MAP = {
    "gen_chat": GEN_CHAT_DIST_CT_CHANNEL_ID,
    "swgoh": GEN_SWGOH_DIST_CT_CHANNEL_ID,
    "public_square": PUBLIC_SQUARE_DIST_CT_CHANNEL_ID,
    "first_circuit": FIRST_CIRCUIT_CHANNEL_ID,
    "ssc": SUPREME_COURT_CHANNEL_ID
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
            max_length=100
        )
        self.additional_defendants = discord.ui.TextInput(
            label="Additional Defendants (optional)",
            placeholder="Enter additional defendants (semi-colon separated)...",
            style=discord.TextStyle.short,
            max_length=100
        )
        self.complaint_text = discord.ui.TextInput(
            label="Complaint Text",
            placeholder="Enter the facts and legal basis for your complaint...",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=True
        )
        self.add_item(self.complaint_text)

    async def on_submit(self, interaction: discord.Interaction):
        venue_channel_id = VENUE_CHANNEL_MAP.get(self.venue)
        if not venue_channel_id:
            await interaction.response.send_message("❌ Invalid venue selected.", ephemeral=True)
            return

        extra_plaintiffs_raw = self.additional_plaintiffs.value
        extra_plaintiffs = [p.strip() for p in extra_plaintiffs_raw.split(';') if p.strip()]
        extra_defendants_raw = self.additional_defendants.value
        extra_defendants = [d.strip() for d in extra_defendants_raw.split(';') if d.strip()]

        court_data = self.bot.get_cog("SpideyCourts").court_data
        case_number = f"1:{interaction.created_at.year % 100:02d}-cv-{len(court_data)+1:06d}-{JUDGE_INITS.get(self.venue, 'SS')}"

        court_data[case_number] = {
            "plaintiff": self.plaintiff.id,
            "additional_plaintiffs": extra_plaintiffs,
            "defendant": self.defendant.id,
            "additional_defendants": extra_defendants,
            "counsel_for_plaintiff": interaction.user.id,
            "venue": self.venue,
            "judge": JUDGE_VENUES.get(self.venue, {}).get("name", "SS"),
            "judge_id": JUDGE_VENUES.get(self.venue, {}).get("id", 684457913250480143),
            "filings": [
                {
                    "entry": 1,
                    "document_type": "Complaint",
                    "author": interaction.user.name,
                    "content": self.complaint_text.value,
                    "timestamp": interaction.created_at.isoformat()
                }
            ]
        }

        save_json(COURT_FILE, court_data)

        # Try to send the summary message to the correct channel
        venue_channel = self.bot.get_channel(venue_channel_id)
        summary = (
            f"📁 **New Complaint Filed**\n"
            f"**Case Number:** `{case_number}`\n"
            f"**Plaintiff:** {self.plaintiff.mention}"
        )

        if extra_plaintiffs:
            summary += f"\n**Additional Plaintiffs:** {', '.join(extra_plaintiffs)}"

        summary += f"\n**Defendant:** {self.defendant.mention}"

        if extra_defendants:
            summary += f"\n**Additional Defendants:** {', '.join(extra_defendants)}"

        summary += f"\nFiled by: {interaction.user.mention}"

        await venue_channel.send(summary)


        await interaction.response.send_message(
            f"✅ Complaint filed successfully under case number `{case_number}`.",
            ephemeral=True
        )



class SpideyCourts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.court_data = load_json(COURT_FILE)
        self.show_applicants.start()
    
    def cog_unload(self):
        """Stop the daily task when the cog is unloaded."""
        self.show_applicants.cancel()
    
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

                    try:
                        plaintiff_user = await self.bot.fetch_user(int(case_data["plaintiff"]))
                        plaintiff_name = plaintiff_user.name
                    except Exception:
                        pass

                    try:
                        defendant_user = await self.bot.fetch_user(int(case_data["defendant"]))
                        defendant_name = defendant_user.name
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

        
