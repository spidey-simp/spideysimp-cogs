import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Select
from redbot.core.bot import Red
from redbot.core import commands, Config, bank
import humanize
import os
import json
from datetime import datetime, timedelta, timezone
import shutil

registration_fee = 5000
renewal_fee = 2000

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def migrate_corporations_file(old_file, new_file):
    if os.path.exists(old_file):
        print(f"Migrating corporations file from {old_file} to {new_file}...")
        # This will copy the file and preserve metadata.
        shutil.copy2(old_file, new_file)
        print("Migration complete.")
        return True
    else:
        print("Old corporations file does not exist; nothing to migrate.")
        return False
    
DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data")

class TaxTypeSelect(View):
    def __init__(self, ctx, treasury, callback):
        super().__init__()
        self.ctx = ctx
        self.treasury = treasury
        self.transaction_type = None
        self.callback = callback
    
    @discord.ui.select(
        placeholder = "Select transaction type. . .",
        options=[
            discord.SelectOption(label="Income Tax", value="income"),
            discord.SelectOption(label="Sales Tax", value="sales"),
            discord.SelectOption(label="Gift Tax", value="gift")
        ]
    )
    async def select_transaction_type(self, interaction, select):
        self.transaction_type = select.values[0]
        await interaction.response.send_message(f"You selected: {self.transaction_type}. Now enter the amount.", ephemeral=True)
        await self.callback(self.transaction_type)


class Treasury(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=81293821983)
        self.config.register_guild(
            sales_tax = 5,
            income_tax = 10,
            gift_tax = 5,
            treasury_balance = 0
        )
        self.tax_file = os.path.join(BASE_DIR, "taxes.json")
        self.corporations_file = os.path.join(DATA_DIR, "corporations.json")
        self.load_taxes()
        self.load_corporations()
        self.corp_migration()
        self.auto_renew_corporations.start()
    

    def corp_migration(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        new_taxes_file = os.path.join(DATA_DIR, "taxes.json")
        migrate_corporations_file(self.tax_file, new_taxes_file)
        # Update the file path so future loads/saves use the centralized file:
        self.tax_file = new_taxes_file
        # Reload corporations from the new file:
        self.load_taxes()
        
    def cog_unload(self):
        self.auto_renew_corporations.stop()
    
    @tasks.loop(hours=24)
    async def auto_renew_corporations(self):
        now = datetime.now(timezone.utc)
        for company_name, corp in self.corporations.items():
            if corp.get("auto_renew", False):
                renewal_due = datetime.fromisoformat(corp["renewal_due"])
                if now >= renewal_due:
                    success, message = await self.renew_corporation(company_name)
                    owner = corp["owner"]
                    try:
                        user = await self.bot.fetch_user(owner)
                        if success:
                            await user.send(f"Your corporation '{company_name}' has been auto-renewed. {message}")
                        else:
                            await user.send(f"Auto-renewal failed for '{company_name}': {message}")
                    except Exception:
                        pass
    
    def load_taxes(self):
        try:
            with open(self.tax_file, "r") as file:
                self.taxes = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
                self.taxes = {"sales_tax": 5, "income_tax": 10, "gift_tax": 5, "treasury_balance": 0}
                self.save_taxes()
        
    def save_taxes(self):
        with open(self.tax_file, "w") as file:
            json.dump(self.taxes, file, indent=4)
    
    def load_corporations(self):
        try:
            with open(self.corporations_file, "r") as file:
                self.corporations = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.corporations = {}
            print(f"Loading corporations from: {self.corporations_file}")
            self.save_corporations()
    
    def save_corporations(self):
        with open(self.corporations_file, "w") as file:
            json.dump(self.corporations, file, indent=4)
    
    async def register_corporation(self, owner: discord.Member, company_name: str, ctx: commands.Context):
        if company_name in self.corporations:
            return False, "A corporation with this name already exists."
        
        await ctx.send(f"Registering your corporation will cost {registration_fee} credits, and you'll be charged a monthly renewal fee of {renewal_fee} credits to maintain corporate status.\nWould you like to proceed? (yes/no)")

        try:
            msg = await self.bot.wait_for("message", check=lambda m: m.author==ctx.author and m.channel==ctx.channel, timeout=30)
        except Exception:
            return False, "Registration timed out."
        if msg.content.lower() not in ["yes", "y"]:
            return False, "Registration canceled by user."
        
        if not await bank.can_spend(owner, registration_fee):
            return False, "Insufficient funds to pay the registration fee."
        
        await bank.withdraw_credits(owner, registration_fee)
        renewal_data = datetime.now(timezone.utc) + timedelta(days=30)
        self.corporations[company_name] = {
            "owner": owner.id,
            "registered_on": datetime.now(timezone.utc).isoformat(),
            "renewal_due": renewal_data.isoformat(),
            "status": "Active",
            "auto_renew": False
        }
        self.save_corporations()
        return True, f"Corporation '{company_name}' successfully registered! Next renewal due: {renewal_data.strftime('%Y-%m-%d')}"

    async def renew_corporation(self, company_name: str):
        """Processes the renewal fee for a corp"""
        if company_name not in self.corporations:
            return False, "Corporation not found."
        
        corp = self.corporations[company_name]
        owner = corp["owner"]
        renewal_due = datetime.fromisoformat(corp["renewal_due"])
        now = datetime.now(timezone.utc)

        if now < renewal_due:
            remaining = (renewal_due - now).total_seconds() /(30 * 24 * 3600)
            fee = int(renewal_fee * remaining)
        else:
            fee = renewal_fee

        if not await bank.can_spend(owner, fee):
            return False, "Insufficient funds for renewal."
        
        await bank.withdraw_credits(owner, fee)
        new_renewal_date = datetime.now(timezone.utc) + timedelta(days=30)
        corp["renewal_due"] = new_renewal_date.isoformat()
        self.save_corporations()
        return True, f"{company_name} successfully renewed! Next renewal due: {new_renewal_date.strftime('%Y-%m-%d')}"

    async def check_expired_corporations(self, ctx):
        now = datetime.now(timezone.utc)
        revoked_corps = []
        for company_name, details in self.corporations.items():
            renewal_due = datetime.fromisoformat(details["renewal_due"])
            if renewal_due < now and details["status"] == "Active":
                details["status"] = "Revoked"
                revoked_corps.append((company_name, details["owner"]))
        self.save_corporations()

        for corp, owner in revoked_corps:
            user = discord.utils.get(ctx.guild.members, name=owner)
            if user:
                await user.send(f"Your corporation '{corp}' has been revoked due to non-payment of the license renewal fee.")
            
        if revoked_corps:
            await ctx.send("The following corporations have been revoked due to non-payment: " + ", ".join([corp for corp, _ in revoked_corps]))
        else:
            await ctx.send("No corporations were revoked.")


    async def deposit_treasury(self, credits: int):
        balance = self.taxes.get("treasury_balance", 0)
        balance += credits
        self.taxes["treasury_balance"] = balance
        self.save_taxes()
    
    async def process_transaction(self, sender: discord.Member, receiver: discord.Member, amount: int, transaction_type: str):
        tax_rate = self.taxes.get(f"{transaction_type}_tax", 0)

        tax_amount = (amount * tax_rate) // 100
        net_amount = amount - tax_amount

        await bank.withdraw_credits(sender, amount)
        await bank.deposit_credits(receiver, net_amount)
        await self.deposit_treasury(tax_amount)
        return net_amount, tax_amount
    
    @commands.command(name="toggle_autorenew")
    async def toggle_autorenew(self, ctx:commands.Context):
        """Toggle auto-renewal for your corporation."""
        user_id = ctx.author.id
        owned_corps = [corp_name for corp_name, details in self.corporations.items() if details["owner"] == user_id]
        if not owned_corps:
            await ctx.send("You don't own any corporations.")
            return
        
        options = [discord.SelectOption(label=corp, value=corp) for corp in owned_corps]

        class CorpSelect(discord.ui.Select):
            def __init__(self, options):
                super().__init__(placeholder="Select your corporation...", min_values=1, max_values=1, options=options)
            
            async def callback(self, interaction: discord.Interaction):
                self.view.selected = self.values[0]
                await interaction.response.send_message(f"You selected **{self.values[0]}**.", ephemeral=True)
                self.view.stop()
        class CorpSelectView(discord.ui.View):
            def __init__(self, options):
                super().__init__(timeout=60)
                self.selected = None
                self.add_item(CorpSelect(options))
        
        view = CorpSelectView(options)
        await ctx.send("Please select the corporation for which you want to toggle auto-renewal:", view=view)
        await view.wait()
        if view.selected is None:
            await ctx.send("No corporation selected. Operation canceled.")
            return
        
        corp_name = view.selected
        corp = self.corporations[corp_name]
        if corp is None:
            await ctx.send("Corporation not found. Operation canceled.")
            return
        
        current = corp.get("auto_renew", False)
        corp["auto_renew"] = not current
        self.save_corporations()
        status = "enabled" if corp["auto_renew"] else "disabled"
        await ctx.send(f"Auto-renewal has been {status} for {corp_name}.")

    @commands.command(name="transfer")
    async def transfer(self, ctx, recipient: discord.Member, amount: int):
        """Prompts user to select a transaction type and ensures proper taxation."""
        if ctx.author == recipient:
            await ctx.send("Why are you trying to send money to yourself silly?")
            return
        view = TaxTypeSelect(ctx, self, callback=None)
        await ctx.send("Please select a transaction type:", view=view)
        await view.wait()

        if view.transaction_type:
            net_amount, tax_amount = await self.process_transaction(ctx.author, recipient, amount, view.transaction_type)
            await ctx.send(f"Transaction successful! {recipient} receives {net_amount} credits with {tax_amount} deducted.")
        else:
            await ctx.send("Transaction canceled.")
    
    @commands.command(name="set_tax")
    @commands.admin_or_permissions(administrator=True)
    async def set_tax(self, ctx):
        """Prompts user to select a tax type and set a new rate."""
        async def get_new_rate(tax_type):
            tax_key = f"{tax_type}_tax"
            await ctx.send("Enter the new tax rate (as a percentage):")
            try:
                msg = await self.bot.wait_for("message", check=lambda m:m.author == ctx.author, timeout=30)
                rate = int(msg.content)
                if rate < 0 or rate > 100:
                    await ctx.send("Invalid input. Please enter a number between 0 and 100.")
                    return
                self.taxes[tax_type] = rate
                self.save_taxes()
                await ctx.send(f"{tax_type.replace('_', ' ').title()} updated to {rate}%.")
            except ValueError:
                await ctx.send("Invalid input. Please enter a valid number.")
            except TimeoutError:
                await ctx.send("Time expired. Tax update canceled.")
        view = TaxTypeSelect(ctx, self, callback=get_new_rate)
        await ctx.send("Please select the tax type you want to update:", view=view)
    
    @commands.command(name="governmentspending", alias=["govsp"])
    @commands.admin_or_permissions(administrator=True)
    async def governmentspending(self, ctx, recipient: discord.Member, amount: int):
        """Allows the government to spend from the treasury without taxation."""
        treasury_balance = self.taxes.get("treasury_balance", 0)
        if amount > treasury_balance:
            await ctx.send("Insufficient funds in the treasury.")
            return
        
        self.taxes["treasury_balance"] -= amount
        self.save_taxes()

        await bank.deposit_credits(recipient, amount)
        await ctx.send(f"Government spending approved! {recipient} has received {amount} credits from the treasury.")
    
    @app_commands.command(name="treasury")
    @app_commands.describe(option="Select what information you want to view.")
    @app_commands.choices(option=[
        app_commands.Choice(name="Treasury Balance", value="balance"),
        app_commands.Choice(name="Tax Rates", value="taxes"),
    ])
    async def treasury(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        """Displays treasury balance or tax rates based on user selection."""
        if option.value == "balance":
            balance = self.taxes.get("treasury_balance", 0)
            await interaction.response.send_message(f"The current Treasury balance is: {humanize.intcomma(balance)} credits.")
        elif option.value == "taxes":
            income_tax = self.taxes.get("income_tax", 0)
            sales_tax = self.taxes.get("sales_tax", 0)
            gift_tax = self.taxes.get("gift_tax", 0)
            await interaction.response.send_message(
                f"Current Tax Rates:\nIncome Tax: {income_tax}%\nSales Tax: {sales_tax}%\nGift Tax: {gift_tax}%"
            )
    
    @commands.hybrid_command(name="registercorp", with_app_command=True, description="Register your corporation with a fee and monthly renewal.")
    async def registercorp(self, ctx: commands.Context, company_name: str):
        """Register your corporation. This will cost a registration fee and set a monthly renewal fee to maintain corporate status."""
        result, message = await self.register_corporation(ctx.author, company_name, ctx)
        await ctx.send(message)
    
    @commands.command(name="renewcorp")
    async def renewcorp(self, ctx:commands.Context, company_name: str):
        """If your company doesn't auto-renew, then you can do it manually using this command."""
        result, message = await self.renew_corporation(company_name)
        await ctx.send(message)
    
    @commands.command(name="checkexpiredcorps")
    @commands.admin_or_permissions(administrator=True)
    async def checkexpiredcorps(self, ctx:commands.Context):
        """To check monthly what corporations have expired."""
        await self.check_expired_corporations(ctx)