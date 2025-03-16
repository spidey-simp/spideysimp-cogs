import discord
import json
import os
from datetime import datetime
from discord.ext import commands
from redbot.core import commands, bank
import pytz
from PIL import Image, ImageDraw, ImageFont
import asyncio


DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data")
CORPORATIONS_FILE = os.path.join(DATA_DIR, "corporations.json")

def load_corporations():
    timezone = pytz.timezone("US/Pacific")
    if os.path.exists(CORPORATIONS_FILE):
        with open(CORPORATIONS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}  # Start with an empty registry.
        save_corporations(data)
    
    for comp_name, comp in data.items():
        if ("CEO" not in comp or comp["CEO"] is None) and "owner" in comp:
            comp["CEO"] = comp["owner"]
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
    for comp_name, comp in data.items():
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

class Corporations(commands.Cog):
    """A cog for managing user corporations.
    
    This cog allows company owners to view and update their corporation's details.
    Future expansion could include managing employees, setting salaries, and more.
    """
    def __init__(self, bot):
        self.bot = bot
        # Load corporations data into an in-memory dictionary.
        self.data = load_corporations()
    
    def cog_unload(self):
        save_corporations(self.data)
    
    @commands.hybrid_command(name="corpindex", with_app_command=True, description="List all registered corporations.")
    async def corpindex(self, ctx: commands.Context):
        if not self.data:
            await ctx.send("No corporations are registered yet.")
            return

        embed = discord.Embed(title="Registered Corporations", color=discord.Color.gold())
        for corpname, comp in self.data.items():
            embed.add_field(
                name=corpname,
                value=f"CEO: <@{comp['CEO']}>\nLand: {comp.get('land', 'None')}\nOffice: {comp.get('office', 'Not built')}",
                inline=False
            )
        await ctx.send(embed=embed)
    
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
    async def buyland(self, ctx: commands.Context, company: str, land_option: str):
        """
        Purchase land from a predefined list.
        Valid options are the keys of LAND_OPTIONS.
        Once purchased, the corporation record is updated.
        """
        company = company.strip()
        land_option = land_option.strip()
        if land_option not in LAND_OPTIONS:
            await ctx.send("Invalid land option. Please choose from: " + ", ".join(LAND_OPTIONS.keys()))
            return
        comp = self.data[company]
        if comp["CEO"] != str(ctx.author.id) and not ctx.author.guild_permissions.administrator:
            await ctx.send("You do not own that corporation.")
            return
        
        if comp.get("land"):
            await ctx.send("This corporation already owns land.")
            return


        cost = LAND_OPTIONS[land_option]["cost"]
        if not await bank.can_spend(ctx.author, cost):
            await ctx.send(f"You don't have enough credits to purchase this land (cost: {cost} credits).")
            return

        await bank.withdraw_credits(ctx.author, cost)
        comp["land"] = land_option
        comp["land_details"] = LAND_OPTIONS[land_option]
        comp["employee_cap"] = LAND_OPTIONS[land_option]["base_employee_cap"]
        save_corporations(self.data)
        await ctx.send(f"Congratulations! {company} has purchased **{land_option}** for {cost} credits as its HQ land.")
    
    @commands.hybrid_command(name="buyoffice", with_app_command=True, description="Purchase an office building for your corporation.")
    async def buyoffice(self, ctx: commands.Context, company: str, office_size: str):
        """
        Purchase an office building for your corporation.
        The office_size (e.g., 'small', 'medium', 'large') determines the cost, 
        construction time, and the additional employee cap.
        Note: Your corporation must have purchased land first.
        """

        company = company.strip()
        office_size = office_size.lower().strip()
        if company not in self.data:
            await ctx.send("That company is not registered.")
            return
        comp = self.data[company]
        if not comp.get("land"):
            await ctx.send("You must purchase land first using /buyland.")
            return
        if comp.get("hq_built"):
            await ctx.send("You have already built an office building.")
            return

        office_options = {
            "small": {"cost": 20000, "build_time": 10, "additional_employee_cap": 10},
            "medium": {"cost": 50000, "build_time": 20, "additional_employee_cap": 25},
            "large": {"cost": 100000, "build_time": 30, "additional_employee_cap": 50}
        }

        if office_size not in office_options:
            await ctx.send("Invalid office size. Options: small, medium, large.")
            return
        
        option = office_options[office_size]

        # Multiply cost by the development cost multiplier from the land.
        multiplier = comp["land_details"]["development_cost_multiplier"]
        total_cost = int(option["cost"] * multiplier)
        if not await bank.can_spend(ctx.author, total_cost):
            await ctx.send(f"You don't have enough credits to purchase a {office_size} office (cost: {total_cost} credits).")
            return

        await bank.withdraw_credits(ctx.author, total_cost)
        await ctx.send(f"Your {office_size} office building purchase has been initiated. Construction will take {option['build_time']} seconds.")
        
        # Simulate construction time delay.
        await asyncio.sleep(option["build_time"])
        
        comp["hq_built"] = True
        comp["employee_cap"] += option["additional_employee_cap"]
        comp["office"] = office_size
        save_corporations(self.data)
        await ctx.send(f"Construction complete! Your office building is now built. Your corporation's employee cap has increased by {option['additional_employee_cap']} to {comp['employee_cap']} employees.")
    
    @commands.hybrid_command(name="publiccorpinfo", with_app_command=True, description="View public details of a corporation.")
    async def publiccorpinfo(self, ctx: commands.Context, company: str):
        """
        Show public info for a given corporation.
        This command displays limited details that are safe for everyone to see.
        """
        company = company.strip()
        if company not in self.data:
            await ctx.send("That corporation is not registered in the system.")
            return
        comp = self.data[company]
        # Display only public information:
        msg = f"**Corporation: {company}**\n"
        msg += f"Category: {comp.get('category', 'N/A')}\n"
        msg += f"Location: {comp.get('land', 'Not set')}\n"
        msg += f"Office: {comp.get('office', 'Not built')}\n"
        msg += f"Employee Cap: {comp.get('employee_cap', 'N/A')}\n"
        msg += f"Date Registered: {comp.get('date_registered', 'N/A')}\n"
        await ctx.send(msg)

    
    @commands.hybrid_command(name="companyinfo", with_app_command=True, description="View your corporation's details.")
    async def companyinfo(self, ctx: commands.Context, company: str = None):
        """
        Show detailed info for a given company.
        If no company is specified, display the corporation for the caller.
        """
        # If no company name is provided, assume the caller's company.
        if company:
            company = company.strip()
            if company not in self.data:
                await ctx.send("That company is not registered.")
                return

            comp = self.data[company]
            if comp["CEO"] != str(ctx.author.id) and not ctx.author.guild_permissions.administrator:
                await ctx.send("You do not own that corporation. Use the publiccorpinfo command to see info about that company.")
                return
            corp = self.data[company]
            msg = f"**Company Information for {corp.get('name', 'Unnamed Corporation')}**\n"
            msg += f"CEO: <@{corp.get('CEO', 'N/A')}>\n"
            msg += f"Category: {corp.get('category', 'N/A')}\n"
            msg += f"Land: {corp.get('land', 'None')}\n"
            msg += f"Office: {corp.get('office', 'Not built')}\n"
            msg += f"Employee Cap: {corp.get('employee_cap', 'N/A')}\n"
            msg += f"Busy Season Modifier: {corp.get('busy_season', 'N/A')}\n"
            msg += f"Date Registered: {corp.get('date_registered', 'N/A')}\n"
            await ctx.send(msg)
        else:
            owned = [name for name, comp in self.data.items() if comp["CEO"] == str(ctx.author.id)]
            if not owned:
                await ctx.send("You do not own any registered corporations.")
                return
            msg = "**Your Registered Corporations:**\n" + "\n".join(owned)
            await ctx.send(msg)
    