import discord
import json
import os
from datetime import datetime
from discord.ext import commands
from redbot.core import commands, bank
import pytz
from PIL import Image, ImageDraw, ImageFont
import asyncio

# Path for corporations registry file.
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
CORPORATIONS_FILE = os.path.join(BASE_DIR, "corporations.json")

def load_corporations():
    timezone = pytz.timezone("US/Pacific")
    if os.path.exists(CORPORATIONS_FILE):
        with open(CORPORATIONS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}  # Start with an empty registry.
        save_corporations(data)
    # Migration: Ensure each company has the expected fields.
    default_fields = {
        "category": "general",       # e.g., tech, retail, healthcare, etc.
        "office_purchased": False,   # Whether the company has purchased HQ space
        "CEO": None,                 # Owner's Discord user id (as string)
        "employees": 0,
        "busy_season": 1.0,          # Multiplier for seasonal performance; default is neutral.
        "date_registered": str(datetime.now(timezone)),
        "land": None,
        "office": None
    }
    for symbol, comp in data.items():
        for field, default in default_fields.items():
            if field not in comp:
                comp[field] = default
    save_corporations(data)
    return data

def save_corporations(data):
    with open(CORPORATIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

LAND_OPTIONS = {
    "Your Parents' Garage": {
        "cost": 500,  # very low cost
        "developable_land": 0,
        "development_cost_multiplier": 1.0,
        "base_employee_cap": 2,
        "description": "The humble beginnings! Your parents offered to pay—but there's no developable land here. Limited capacity for growth."
    },
    "Undeveloped Marsh Land": {
        "cost": 30000,  # relatively low cost compared to island land
        "developable_land": 50,
        "development_cost_multiplier": 1.5,
        "base_employee_cap": 20,
        "description": "Cheap land with a lot of potential—but also many challenges, such as flooding, mosquitoes, and high development costs."
    },
    "Idealistic Island": {
        "cost": 90000,  # higher cost than marsh even with same developable land
        "developable_land": 50,
        "development_cost_multiplier": 1.5,
        "base_employee_cap": 50,
        "description": "A picturesque island offering unique charm. Pros: Scenic views and lifestyle perks. Cons: Isolation and higher purchase cost."
    },
    "Industrial Valley": {
        "cost": 120000,
        "developable_land": 300,
        "development_cost_multiplier": 0.75,
        "base_employee_cap": 100,
        "description": "A rugged industrial area famous for low regulations and abundant materials. Pros: Cost-effective operations. Cons: Less attractive for top talent."
    },
    "Coastal Capital": {
        "cost": 200000,
        "developable_land": 400,
        "development_cost_multiplier": 1.0,
        "base_employee_cap": 150,
        "description": "A bustling coastal metropolis with prestige and excellent connectivity—but at a premium price."
    },
    "Suburban Sprawl": {
        "cost": 80000,
        "developable_land": 200,
        "development_cost_multiplier": 1.2,
        "base_employee_cap": 60,
        "description": "A sprawling suburban area offering a balance between cost and growth potential. Pros: Affordable and spacious. Cons: Moderate infrastructure."
    },
    "Downtown Core": {
        "cost": 180000,
        "developable_land": 350,
        "development_cost_multiplier": 1.3,
        "base_employee_cap": 130,
        "description": "Prime downtown real estate with excellent connectivity and prestige—but space is limited and costs are high."
    },
    "Rural Retreat": {
        "cost": 40000,
        "developable_land": 100,
        "development_cost_multiplier": 0.8,
        "base_employee_cap": 30,
        "description": "A quiet rural area with very low costs but a limited talent pool and fewer amenities."
    },
    "Mountain Foothills": {
        "cost": 60000,
        "developable_land": 120,
        "development_cost_multiplier": 1.0,
        "base_employee_cap": 40,
        "description": "Scenic land in the mountain foothills with moderate development challenges and a unique environment."
    }
}

CORPORATION_DATA = {}

class Corporations(commands.Cog):
    """A cog for managing user corporations.

    This cog allows company owners to view and update their corporation's details.
    Future expansion could include managing employees, setting salaries, and more.
    """
    def __init__(self, bot):
        self.bot = bot
        self.data = load_corporations()
    
    def cog_unload(self):
        save_corporations(self.data)
    
    @commands.hybrid_command(name="landoptions", with_app_command=True, description="View available HQ land options for your corporation.")
    async def landoptions(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Available HQ Land Options",
            description="Each option has its own cost and potential for development. Costs vary depending on location and land quality.",
            color=discord.Color.blue()
        )
        for name, details in LAND_OPTIONS.items():
            embed.add_field(
                name=f"{name} - Cost: {details['cost']} credits",
                value=f"Developable Land: {details['developable_land']} units\nMultiplier: {details['development_cost_multiplier']}\nBase Employee Cap: {details['base_employee_cap']}\nDescription: {details['description']}",
                inline=False
            )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="buyland", with_app_command=True, description="Purchase land for your corporation's HQ.")
    async def buyland(self, ctx: commands.Context, land_option: str):
        """
        Purchase land from a predefined list.
        Valid options are the keys of LAND_OPTIONS.
        Once purchased, the corporation record is updated.
        """
        land_option = land_option.strip()
        if land_option not in LAND_OPTIONS:
            await ctx.send("Invalid land option. Please choose from: " + ", ".join(LAND_OPTIONS.keys()))
            return

        # Check if the user already has a corporation with purchased land.
        corp = CORPORATION_DATA.get(str(ctx.author.id))
        if corp and corp.get("land"):
            await ctx.send("Your corporation already owns land.")
            return

        # For simplicity, assume the cost is proportional to the developable_land value.
        cost = LAND_OPTIONS[land_option]["developable_land"] * 1000  # e.g., 1,000 credits per unit of developable land
        if not await bank.can_spend(ctx.author, cost):
            await ctx.send(f"You don't have enough credits to purchase this land (cost: {cost} credits).")
            return

        await bank.withdraw_credits(ctx.author, cost)
        # Save the purchased land info in the corporation's record.
        CORPORATION_DATA[str(ctx.author.id)] = {
            "land": land_option,
            "land_details": LAND_OPTIONS[land_option],
            "hq_built": False,
            "office_building": None,
            "employee_cap": LAND_OPTIONS[land_option]["base_employee_cap"]
        }
        await ctx.send(f"Congratulations! You have purchased **{land_option}** for {cost} credits as your corporation's land.")

    @commands.hybrid_command(name="buyoffice", with_app_command=True, description="Purchase an office building for your corporation.")
    async def buyoffice(self, ctx: commands.Context, office_size: str):
        """
        Purchase an office building for your corporation.
        The office_size (e.g., 'small', 'medium', 'large') determines the cost, 
        construction time, and the additional employee cap.
        Note: Your corporation must have purchased land first.
        """
        # Check if the corporation exists and has land.
        corp = CORPORATION_DATA.get(str(ctx.author.id))
        if not corp or "land" not in corp:
            await ctx.send("You must purchase land first using /buyland.")
            return
        if corp.get("hq_built"):
            await ctx.send("You have already built an office building.")
            return

        # Define office sizes with parameters.
        office_options = {
            "small": {"cost": 20000, "build_time": 10, "additional_employee_cap": 10},
            "medium": {"cost": 50000, "build_time": 20, "additional_employee_cap": 25},
            "large": {"cost": 100000, "build_time": 30, "additional_employee_cap": 50}
        }
        office_size = office_size.lower().strip()
        if office_size not in office_options:
            await ctx.send("Invalid office size. Options: small, medium, large.")
            return

        option = office_options[office_size]
        # Multiply cost by the development cost multiplier from the land.
        multiplier = corp["land_details"]["development_cost_multiplier"]
        total_cost = int(option["cost"] * multiplier)
        if not await bank.can_spend(ctx.author, total_cost):
            await ctx.send(f"You don't have enough credits to purchase a {office_size} office (cost: {total_cost} credits).")
            return

        await bank.withdraw_credits(ctx.author, total_cost)
        await ctx.send(f"Your {office_size} office building purchase has been initiated. Construction will take {option['build_time']} seconds.")
        
        # Simulate construction time delay.
        await asyncio.sleep(option["build_time"])
        
        corp["hq_built"] = True
        # Increase the employee cap by the additional cap from the office building.
        corp["employee_cap"] += option["additional_employee_cap"]
        corp["office_building"] = office_size
        await ctx.send(f"Construction complete! Your office building is now built. Your corporation's employee cap has increased by {option['additional_employee_cap']} to {corp['employee_cap']} employees.")


    @commands.hybrid_command(name="companyinfo", with_app_command=True, description="View your corporation's details.")
    async def companyinfo(self, ctx: commands.Context, company: str):
        """
        Show detailed info for a given company.
        The company parameter should be the company's symbol or name.
        """
        company = company.strip()
        if company not in self.data:
            await ctx.send("That company is not registered in the system.")
            return

        comp = self.data[company]
        msg = f"**Company Information for {comp['name']} ({company})**\n"
        msg += f"Category: {comp['category']}\n"
        msg += f"CEO: {comp['CEO']}\n"
        msg += f"Headquarters: {comp['hq'] if comp['hq'] else 'Not set'}\n"
        msg += f"Office Purchased: {'Yes' if comp['office_purchased'] else 'No'}\n"
        msg += f"Employees: {comp['employees']}\n"
        msg += f"Busy Season Modifier: {comp['busy_season']}\n"
        msg += f"Date Registered: {comp['date_registered']}\n"
        await ctx.send(msg)
    
    @commands.hybrid_command(name="sethq", with_app_command=True, description="Set your corporation's headquarters location.")
    async def sethq(self, ctx: commands.Context, company: str, location: str):
        """
        Set or update the headquarters location for your company.
        Only the CEO or an admin can do this.
        """
        company = company.strip()
        if company not in self.data:
            await ctx.send("That company is not registered.")
            return

        comp = self.data[company]
        user_is_admin = ctx.author.guild_permissions.administrator
        if str(ctx.author.id) != str(comp.get("CEO")) and not user_is_admin:
            await ctx.send("You don't own that company! You can't change its headquarters!")
            return

        comp["hq"] = location
        save_corporations(self.data)
        await ctx.send(f"Headquarters for {comp['name']} has been set to: {location}")
    
    @commands.hybrid_command(name="buyhq", with_app_command=True, description="Purchase an office space for your corporation (simulated).")
    async def buyhq(self, ctx: commands.Context, company: str):
        """
        Purchase an office space for your company. Once purchased, this might provide benefits
        (e.g., improved NPC interactions, employee morale boosts, etc.).
        Only the CEO or an admin can perform this action.
        """
        company = company.strip()
        if company not in self.data:
            await ctx.send("That company is not registered.")
            return

        comp = self.data[company]
        user_is_admin = ctx.author.guild_permissions.administrator
        if str(ctx.author.id) != str(comp.get("CEO")) and not user_is_admin:
            await ctx.send("You don't own that company!")
            return

        if comp["office_purchased"]:
            await ctx.send("Office space has already been purchased for this company.")
            return

        # For now, we assume the office space costs a fixed amount (e.g., 50,000 credits).
        office_cost = 50000
        if not await bank.can_spend(ctx.author, office_cost):
            await ctx.send("You don't have enough credits to purchase office space.")
            return

        await bank.withdraw_credits(ctx.author, office_cost)
        comp["office_purchased"] = True
        save_corporations(self.data)
        await ctx.send(f"{comp['name']} has successfully purchased its headquarters!")
    
    @commands.hybrid_command(name="editcompany", with_app_command=True, description="Edit details for your corporation.")
    async def editcompany(self, ctx: commands.Context, company: str, field: str, new_value: str):
        """
        Edit a company's detail.
        
        Editable fields might include: name, category, daily_volume, employees, CEO, location, dividend_yield, busy_season.
        Note: Some fields (like stock price, price_history, total_shares, etc.) are not editable here.
        
        Only the CEO or an admin can edit a company.
        """
        company = company.strip()
        if company not in self.data:
            await ctx.send("That company is not registered.")
            return
        
        comp = self.data[company]
        user_is_admin = ctx.author.guild_permissions.administrator
        if str(ctx.author.id) != str(comp.get("CEO")) and not user_is_admin:
            await ctx.send("You don't own that company! You can't edit it!")
            return

        # Define which fields are editable by the CEO.
        editable_fields = ["name", "category", "daily_volume", "employees", "CEO", "location", "dividend_yield", "busy_season"]
        if field not in editable_fields:
            await ctx.send("That field is not editable via this command.")
            return

        # Convert types if necessary.
        if field in ["daily_volume", "employees"]:
            try:
                new_value = int(new_value)
            except ValueError:
                await ctx.send("Please provide a valid integer for that field.")
                return
        elif field in ["dividend_yield", "busy_season"]:
            try:
                new_value = float(new_value)
            except ValueError:
                await ctx.send("Please provide a valid number for that field.")
                return
        
        # Special handling for dividend_yield (if desired, you can add shareholder reaction logic here).
        # For now, we'll allow the change.
        comp[field] = new_value
        save_corporations(self.data)
        await ctx.send(f"Updated {field} for {comp['name']} to {new_value}.")
