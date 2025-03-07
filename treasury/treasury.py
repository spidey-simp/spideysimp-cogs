import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
from redbot.core.bot import Red
from redbot.core import commands, Config, bank
import humanize
import os
import json
from datetime import datetime, timedelta, timezone

CORPORATIONS_FILE = "corporations.json"

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
            discord.SelectOption(label="Income Tax", value="income_tax"),
            discord.SelectOption(label="Sales Tax", value="sales_tax"),
            discord.SelectOption(label="Gift Tax", value="gift_tax")
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
        self.tax_file = "taxes.json"
        self.load_taxes()
        self.load_corporations()
    
    def load_taxes(self):
        try:
            with open(self.tax_file, "r") as file:
                self.taxes = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
                self.taxes = {"sales_tax": 5, "income_tax": 10, "gift_tax": 5, "treasury_balance": 0}
                self.save_taxes()
        
    def save_taxes(self):
        with open(self.tax_file, "w") as file:
            json.dummp(self.taxes, file, indent=4)
    
    def load_corporations(self):
        try:
            with open(CORPORATIONS_FILE, "r") as file:
                self.corporations = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.corporations = {}
            self.save_corporations()
    
    def save_corporations(self):
        with open(CORPORATIONS_FILE, "w") as file:
            json.dump(self.corporations, file, indent=4)
    
    async def register_corporation(self, owner: str, company_name: str):
        if company_name in self.corporations:
            return False, "A corporation with this name already exists."
        
        renewal_data = datetime.now(timezone.utc) + timedelta(days=30)
        self.corporations[company_name] = {
            "owner": owner,
            "registered_on": datetime.now(timezone.utc).isoformat(),
            "renewal_due": renewal_data.isoformat(),
            "status": "Active"
        }
        self.save_corporations()
        return True, f"Corporation '{company_name}' successfully registered! Next renewal due: {renewal_data.strftime('%Y-%m-%d')}"

    async def renew_corporation(self, company_name: str):
        """Processes the renewal fee for a corp"""
        if company_name not in self.corporations:
            return False, "Corporation not found."
        
        owner = self.corporations[company_name]["owner"]
        renewal_fee = 2000

        if not await bank.can_spend(owner, renewal_fee):
            return False, "Insufficient funds for renewal."
        
        await bank.withdraw_credits(owner, renewal_fee)
        new_renewal_date = datetime.now(timezone.utc) + timedelta(days=30)
        self.corporations[company_name]["renewal_due"] = new_renewal_date.isoformat()
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
    
    async def process_transaction(self, sender: str, receiver: str, amount: int, transaction_type: str):
        tax_rate = self.taxes.get(f"{transaction_type}_tax", 0)

        tax_amount = (amount * tax_rate) // 100
        net_amount = amount - tax_amount

        await bank.withdraw_credits(sender, amount)
        await bank.deposit_credits(receiver, net_amount)
        await self.deposit_treasury(tax_amount)
        return net_amount, tax_amount

    @commands.command(name="transfer")
    async def transfer(self, ctx, recipient: str, amount: int):
        """Prompts user to select a transaction type and ensures proper taxation."""
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
    async def governmentspending(self, ctx, recipient: str, amount: int):
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
    
