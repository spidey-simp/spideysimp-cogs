import discord
from discord import app_commands
import json
import os
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from redbot.core import commands, bank, Config
import pytz
from PIL import Image, ImageDraw, ImageFont
import asyncio
import humanize
import random, math


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
        "name": None,
        "category": "general",       # e.g., tech, retail, healthcare, etc.
        "office_purchased": False,   # Whether the company has purchased HQ space
        "CEO": None,                 # Owner's Discord user id (as string)
        "employees": 0,
        "busy_season": 1.0,          # Multiplier for seasonal performance; default is neutral.
        "date_registered": str(datetime.now(timezone)),
        "land": None,
        "office": None,
        "balance": 0,
        "randd_skill": 0,
        "employees": {},
        "active_projects": []
    }
    for comp_name, comp in data.items():
        for field, default in default_fields.items():
            if field == "name":
                comp[field] = comp_name
            if field not in comp:
                comp[field] = default
    save_corporations(data)
    return data

def save_corporations(data):
    with open(CORPORATIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

STATE_OPTIONS = {
    "Auroria": {
        "description": "A vibrant coastal state with a high cost of living and a booming tech sector.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Undeveloped Marsh Land",
            "Coastal Capital",
            "Suburban Sprawl",
            "Downtown Core"
        ],
        "land_cost_modifier": 1.5,
        "property_tax": 2.0,
        "minimum_wage": 15,
        "population": 10000000,
        "population_density": 1200,
        "infrastructure_spending": "High",
        "coastal": True,
        "median_salary": 70000,
        "natural_disaster_chance": 0.1
    },
    "Deltora": {
        "description": "A rural, landlocked state known for its expansive farmlands and affordable land prices.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Undeveloped Marsh Land",
            "Industrial Valley",
            "Suburban Sprawl",
            "Rural Retreat",
            "Mountain Foothills"
        ],
        "land_cost_modifier": 0.8,
        "property_tax": 1.2,
        "minimum_wage": 10,
        "population": 5000000,
        "population_density": 50,
        "infrastructure_spending": "Low",
        "coastal": False,
        "median_salary": 40000,
        "natural_disaster_chance": 0.2
    },
    "Neonix": {
        "description": "A modern, urbanized coastal state with high property taxes and a booming tech sector.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Downtown Core",
            "Suburban Sprawl",
            "Coastal Capital"
        ],
        "land_cost_modifier": 2.0,
        "property_tax": 3.0,
        "minimum_wage": 20,
        "population": 15000000,
        "population_density": 5000,
        "infrastructure_spending": "Very High",
        "coastal": True,
        "median_salary": 90000,
        "natural_disaster_chance": 0.05
    },
    "Veridia": {
        "description": "A green, sustainability-focused state with moderate costs and a mix of urban and rural areas.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Undeveloped Marsh Land",
            "Idealistic Island",  # Only available in states that allow coastal or island options.
            "Industrial Valley",
            "Rural Retreat",
            "Mountain Foothills"
        ],
        "land_cost_modifier": 1.0,
        "property_tax": 1.5,
        "minimum_wage": 12,
        "population": 8000000,
        "population_density": 200,
        "infrastructure_spending": "Medium",
        "coastal": False,
        "median_salary": 60000,
        "natural_disaster_chance": 0.15
    },
    "Caldora": {
        "description": "A highly industrialized, densely populated coastal state with premium land prices and robust infrastructure.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Coastal Capital",
            "Downtown Core",
            "Suburban Sprawl",
            "Industrial Valley"
        ],
        "land_cost_modifier": 2.5,
        "property_tax": 3.5,
        "minimum_wage": 22,
        "population": 20000000,
        "population_density": 6000,
        "infrastructure_spending": "Very High",
        "coastal": True,
        "median_salary": 100000,
        "natural_disaster_chance": 0.08
    }
}


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

office_options = {
    "hole-in-the-wall": {
        "cost": 100000,
        "build_time": 10,
        "additional_employee_cap": 50,
        "land_usage": 0,
        "description": "A modest, cramped space in an existing facility, with minimal new construction."
    },
    "office suite": {
        "cost": 250000,
        "build_time": 20,
        "additional_employee_cap": 100,
        "land_usage": 10,
        "description": "Shared office space with modern amenities, ideal for small teams."
    },
    "small office building": {
        "cost": 500000,
        "build_time": 30,
        "additional_employee_cap": 200,
        "land_usage": 50,
        "description": "A dedicated small office building for growing companies."
    },
    "warehouse": {
        "cost": 750000,
        "build_time": 45,
        "additional_employee_cap": 150,
        "land_usage": 40,
        "description": "A large warehouse suited for companies with significant logistics needs."
    },
    "wide campus": {
        "cost": 2000000,
        "build_time": 60,
        "additional_employee_cap": 500,
        "land_usage": 200,
        "description": "A sprawling campus with multiple buildings, ideal for corporate giants."
    },
    "skyscraper": {
        "cost": 3000000,
        "build_time": 90,
        "additional_employee_cap": 1000,
        "land_usage": 150,
        "description": "A towering skyscraper that maximizes vertical space, requiring less land area but high construction complexity."
    }
}

CORPORATE_CATEGORIES = {
    "Consumer Goods": {
        "description": "Companies that manufacture products used by everyday consumers.",
        "subcategories": {
            "Food & Beverage": {
                "description": "Producers of food, drinks, and related consumables."
            },
            "Apparel": "Companies in clothing, footwear, and accessories.",
            "Household Products": "Manufacturers of appliances and home care products.",
            "Recreation": "Any product designed to be used in a recreational setting."
        }
    },
    "Technology": {
        "description": "Firms operating in the tech sector, from hardware to software.",
        "subcategories": {
            "Software": "Developers of applications, operating systems, and cloud services.",
            "Hardware": "Producers of computers, smartphones, and peripherals.",
            "Semiconductors": "Companies involved in chip manufacturing and related technology."
        }
    },
    "Entertainment": {
        "description": "Companies that create or distribute content for entertainment.",
        "subcategories": {
            "Film & Television": "Studios and production companies.",
            "Music": "Record labels, artists, and streaming platforms.",
            "Gaming": "Video game developers and publishers."
        }
    },
    "Services": {
        "description": "Firms that offer services rather than physical products.",
        "subcategories": {
            "Legal Services": "Law firms, legal advisors, and related consultancies.",
            "Financial Services": "Banks, insurance companies, investment firms, and fintech.",
            "Transportation": "Taxi, rideshare, logistics, and courier services.",
            "Hospitality": "Hotels, restaurants, and event management companies.",
            "Personal Care": "Salons, spas, fitness centers, and wellness providers."
        }
    },
    "Retail": {
        "description": "Companies that sell goods directly to consumers.",
        "subcategories": {
            "Department Stores": "Large-scale retailers with multiple product lines.",
            "E-commerce": "Online retail businesses and marketplaces.",
            "Specialty Retail": "Boutique stores and niche product sellers."
        }
    },
    "Finance": {
        "description": "Institutions and firms offering financial products and services.",
        "subcategories": {
            "Banking": "Traditional banks, credit unions, and commercial lenders.",
            "Investment": "Investment banks, hedge funds, and private equity firms.",
            "Insurance": "Companies offering insurance and risk management services."
        }
    },
    "Healthcare": {
        "description": "Companies in the healthcare and life sciences sectors.",
        "subcategories": {
            "Pharmaceuticals": "Drug manufacturers and distributors.",
            "Biotechnology": "Biotech companies focused on research and development.",
            "Medical Devices": "Producers of medical equipment and devices.",
            "Healthcare Services": "Hospitals, clinics, and healthcare providers."
        }
    },
    "Energy": {
        "description": "Firms involved in the production and distribution of energy.",
        "subcategories": {
            "Oil & Gas": "Exploration, production, and refining companies.",
            "Renewable Energy": "Solar, wind, hydro, and other renewable sources."
        }
    },
    "Industrial": {
        "description": "Companies involved in manufacturing, logistics, and heavy industry.",
        "subcategories": {
            "Manufacturing": "Producers of industrial and consumer products.",
            "Logistics": "Supply chain management, transportation, and warehousing."
        }
    },
    "Automotive": {
        "description": "Companies that design, manufacture, and sell vehicles and auto parts.",
        "subcategories": {
            "Vehicles": "Manufacturers of cars, trucks, and motorcycles.",
            "Auto Parts": "Producers of components and accessories.",
            "Electric Vehicles": "Specialized manufacturers of electric-powered vehicles."
        }
    }
}

PRODUCT_TEMPLATES = {
    "Tech": {
        "Smartphone": {
            "requires_randd": True,
            "base_quality": 10,
            "stats": {
                "base_performance": 10,
                "base_battery_life": 10,
                "base_graphics": 10,
                "base_design": 10,
                "base_usability": 10,
                "base_marketability": 10
            },
            "base_production": 100,
            "base_manufacture_cost": 50,
            "prod_to_cust_ratio": 1.0,
            "accessories_included": False
        }
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
        self.config = Config.get_conf(self, identifier=12038120841)
        self.config.register_guild(
            active_projs = {}
        )
    
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
    
    @commands.hybrid_command(name="research_new_product", with_app_command=True, description="Start a new research project for your corporation.")
    async def research_new_product(self, ctx: commands.Context, company: str, budget: int, time_assigned: int, workers_assigned: int = 0):
        if ctx.interaction:
            await ctx.defer()
        
        if company not in self.data:
            await ctx.send("It appears that company is not registered yet.")
            return
        
        corp = self.data[company]

        corp["employees"].setdefault("randd", {})

        if ctx.author.id != corp["CEO"]:
            await ctx.send("It's nice of you to want to contribute to someone else's corporation, but maybe you can do it another way. :)")
            return
        
        if budget <= 0 or  time_assigned <= 0:
            await ctx.send(f"{company} can't create a new product without investing some money or time into it.")
            return
        
        if budget > corp["balance"]:
            await ctx.send(f"{company} doesn't have the financial ability to invest that much. Please invest more into the company if you want to budget that much.")
            return
        
        start_balance = corp["balance"]

        if workers_assigned > 0:
            if not corp["employees"] or not corp["employees"]["randd"]:
                await ctx.send("You need to assign a **Research and Development** department before you can assign workers!")
                return
            if len(corp["employees"]["randd"].keys()) == 0:
                await ctx.send(f"It looks like {company} hasn't hired any employees for their **Research and Development** department yet!")
                return
            available_workers = sum(1 for details in corp["employees"]["randd"].values() if details.get("current_proj") is None)
            if workers_assigned > available_workers:
                if available_workers:
                    await ctx.send(f"{company} currently only has {available_workers} R&D employees not assigned to a research project. Please assign fewer workers.")
                    return
                else:
                    await ctx.send(f"All of {company}'s R&D employees are currently assigned to other projects.")
                    return
        if workers_assigned < 0:
            await ctx.send("You can't assign a negative amount of workers!")
            return
        
        try: 
            time, proj_id, quality = self.new_product_research(corp, budget, workers_assigned, time_assigned)
            now = datetime.now(timezone.utc)
            project_finish = now + timedelta(minutes=time)
            guild_proj_progress = await self.config.guild(ctx.guild).active_projs() or {}
            if company not in guild_proj_progress:
                guild_proj_progress[company] = {}
            guild_proj_progress[company][str(proj_id)] ={
                "time": project_finish.isoformat(),
                "quality": quality
            }
            corp["active_projects"].append(str(proj_id))
            await self.config.guild(ctx.guild).active_projs.set(guild_proj_progress)
            pacific_tz = pytz.timezone("US/Pacific")
            project_finish_pst = project_finish.astimezone(pacific_tz)
            formatted_finish = project_finish_pst.strftime("%B %d, %Y at %I:%M %p %Z")
            plural = ""
            if workers_assigned != 0:
                plural = "employees' "
            if time < time_assigned:
                await ctx.send(f"{company}'s research project (ID: **{proj_id}**) has begun.\nThe project should be finished early because of your {plural}research effectiveness!\nCheck back in at **{formatted_finish}**! \n Please keep this project id handy until I make a /seeactiveproj command. (It will come eventually!)")
            elif time > time_assigned:
                await ctx.send(f"{company}'s research project (ID: **{proj_id}**) has begun.\nThe project will be finished late because of your {plural}lack of research effectiveness!\nCheck back in at **{formatted_finish}**! \n Please keep this project id handy until I make a /seeactiveproj command. (It will come eventually!)")
            else:
                await ctx.send(f"{company}'s research project (ID: **{proj_id}**) has begun.\nThe project should be finished at **{formatted_finish}**! \n Please keep this project id handy until I make a /seeactiveproj command. (It will come eventually!)")
        except Exception as e:
            if corp["balance"] != start_balance:
                corp["balance"] = start_balance
            await ctx.send(f"There was an error ({e})beginning the project. Any balance that was invested has been refunded to the company.")
        
        save_corporations(self.data)


    def new_product_research(self, corp: dict, project_budget: int, employees_assigned: int, time_assigned: int, leader_assigned: str = None)-> tuple:
        employees = max(employees_assigned, 1)

        randd_skill = corp.get("randd_skill", 0)
        
        target_budget_per_emp = 1000
        leadership_skill = 0

        if leader_assigned:
            leadership_skill =  corp["employees"]["randd"][leader_assigned].get("leadership_skill")
        
        target_time_per_emp = self.compute_target_time_per_emp(60.0, employees, leadership_skill)

        per_emp_budget = project_budget / employees
        per_emp_time = time_assigned / employees

        budget_eff = min(1, per_emp_budget / target_budget_per_emp)
        time_eff = min(1, per_emp_time / target_time_per_emp)

        per_emp_effectiveness = (budget_eff + time_eff) / 2
        per_emp_effectiveness *= random.uniform(.95, 1.05)

        overall_effectiveness = per_emp_effectiveness
        overall_effectiveness += randd_skill * .1


        quality_avg = 50 * (1 - math.exp(-overall_effectiveness / 5))
        quality_avg = max(0, min(100, quality_avg))

        research_time = int(time_assigned * math.exp(-overall_effectiveness / 10))
        research_time = max(1, research_time)

        
        corp["balance"] -= project_budget

        project_id = str(random.randint(1, 10**10))

        return research_time, project_id, quality_avg
    
    def compute_target_time_per_emp(self, base_time: float, num_employees: int, leader_effectiveness: float = 0) -> float:
        if num_employees <= 1:
            return base_time
        
        max_overhead = base_time * .5

        saturation_constant = 10

        raw_overhead = max_overhead * (1 - math.exp(-(num_employees - 1) /saturation_constant))

        mitigation = .5 - (leader_effectiveness / 10)

        additional_overhead = raw_overhead * mitigation

        return base_time + additional_overhead
    
    @app_commands.command(name="check_project_progress", description="Check progress of a project your company started.")
    @app_commands.describe(company="Which company to see the projects of!", project="Choose a project to check the progress of!")
    async def check_project_progress(self, interaction: discord.Interaction, company: str, project: str):
        await interaction.response.defer(ephemeral=True)
        
        active_projs = await self.config.guild(interaction.guild).active_projs()
        if company not in active_projs or str(project) not in active_projs[company]:
            await interaction.followup.send("It looks like there was an error storing the project. Please contact an admin to push your project through!", ephemeral=True)
            return
        
        now = datetime.now(timezone.utc)
        timefinish = active_projs[company][str(project)]["time"]

        finish_time = datetime.fromisoformat(timefinish)

        if now >= finish_time:
            outcome = self.chance_of_failure(self.data[company], active_projs[company][str(project)]["quality"])
            if outcome == "failed":
                message = self.get_rnd_message("failure")
                active_projs[company].pop(str(project), None)
            elif outcome == "postponed":
                message = self.get_rnd_message("in_progress")
                additional_time = random.randint(1, 60)
                message += f"\nCheck back in {additional_time} minutes!"
                new_finish_time = now + timedelta(minutes=additional_time)
                active_projs[company][str(project)]["time"] = new_finish_time.isoformat()
            else:
                message = self.get_rnd_message("success_new")
                active_projs[company].pop(str(project), None)
            await interaction.followup.send(message)
        else:
            time_remaining = finish_time - now
            await interaction.followup.send(f"Your project is still in progress. Time remaining: {time_remaining}.")

    def chance_of_failure(self, corp: dict, quality: float):
        randd_skill = corp.get("randd_skill", .5) / 10000
        quality /= 10000

        chance = random.uniform(0.0, 1.0)

        if chance < (.05 - randd_skill - quality):
            secondchance = random.uniform(0.0, 1.0)
            if secondchance <= .7:
                return "postponed"
            else:
                return "failed"
        
        return "success"


        

    @check_project_progress.autocomplete("company")
    async def company_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []

        for key, details in self.data.items():
            comp_name = details.get("name", key)
            if details.get("CEO") == interaction.user.id and current.lower() in comp_name.lower():
                choices.append(app_commands.Choice(name=comp_name, value=comp_name))
        
        return choices
    
    @check_project_progress.autocomplete("project")
    async def project_autocomplete(self, interaction: discord.Interaction, current: str):
        company = interaction.namespace.company
        choices = []
        
        if company in self.data:
            active_projects = self.data[company].get("active_projects", [])
            for proj in active_projects:
                if current.lower() in proj.lower():
                    choices.append(app_commands.Choice(name=proj, value=proj))
        
        return choices


    def get_rnd_message(self, outcome, category=None):
        messages = {
            "in_progress": [
                "One of our researchers is having major success with their research, but they need a little more time!",
                "Our R&D team is making progress—stay tuned for a breakthrough!",
                "Research is underway; we're on the brink of something big, but more time is needed."
            ],
            "success_new": [
                "After extensive research, we've devised the idea for a {category_product}. Do you want to develop this product or get it straight to the market?",
                "Eureka! A new {category_product} concept has emerged from our labs. How would you like to proceed?",
                "Breakthrough! The R&D team has conceived a cutting-edge {category_product}."
            ],
            "failure": [
                "Unfortunately, it seems our investments haven't paid off this time. We should try again on a new product.",
                "Our research did not yield a viable product this round. Time to regroup and strategize.",
                "The R&D efforts didn't come to fruition—sometimes innovation means learning from failure."
            ],
            "improvement": [
                "Great news! Our research has significantly improved your product's performance.",
                "The development process was a success, and your product's quality has increased.",
                "Improvements are in—your product has been enhanced thanks to our dedicated R&D team."
            ]
        }
        
        if outcome in messages:
            msg = random.choice(messages[outcome])
            if "{category_product}" in msg and category:
                msg = msg.format(category_product=category)
            return msg
        else:
            return "Research update: Status unknown."

    @app_commands.command(
    name="landoptions",
    description="View available HQ land options or state info for your corporation."
    )
    @app_commands.describe(option="Select whether to view land plot options, office options, or state details")
    @app_commands.choices(option=[
        app_commands.Choice(name="Land Plots", value="landplots"),
        app_commands.Choice(name="Office Options", value="office_options"),
        app_commands.Choice(name="States", value="states")
    ])
    async def landoptions(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        if option.value == "states":
            # Display state information.
            # Ensure you have a STATE_OPTIONS dictionary defined somewhere in your cog.
            embed = discord.Embed(
                title="Available States",
                description="Each state has its own attributes affecting land costs and policies.",
                color=discord.Color.green()
            )
            for state, details in STATE_OPTIONS.items():
                embed.add_field(
                    name=state,
                    value=(
                        f"Description: {details['description']}\n"
                        f"Land Cost Modifier: {details['land_cost_modifier']}\n"
                        f"Property Tax: {details['property_tax']}%\n"
                        f"Minimum Wage: ${details['minimum_wage']}\n"
                        f"Population: {humanize.intcomma(details['population'])}\n"
                        f"Pop. Density: {details['population_density']} per sq mi\n"
                        f"Infrastructure: {details['infrastructure_spending']}\n"
                        f"Median Salary: ${humanize.intcomma(details['median_salary'])}\n"
                        f"Natural Disaster Chance: {details['natural_disaster_chance']*100:.1f}%\n"
                        f"Allowed Land Options: {', '.join(details['allowed_land_options'])}"
                    ),
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        elif option.value == "office_options":
            embed = discord.Embed(
                title="Available Office Options",
                description="Options for constructing corporate offices, each with its own cost, build time, land usage, and employee capacity.",
                color=discord.Color.purple()
            )
            for name, details in office_options.items():
                embed.add_field(
                    name=f"{name.title()} - Cost: {details['cost']} credits",
                    value=(
                        f"Build Time: {details['build_time']} sec\n"
                        f"Additional Employee Cap: {details['additional_employee_cap']}\n"
                        f"Land Usage: {details['land_usage']} units\n"
                        f"Description: {details['description']}"
                    ),
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        else:
            # Default: show land plot options.
            embed = discord.Embed(
                title="Available HQ Land Options",
                description="Each option has its own cost and potential for development. Costs vary depending on location and land quality.",
                color=discord.Color.blue()
            )
            for name, details in LAND_OPTIONS.items():
                embed.add_field(
                    name=f"{name} - Cost: {details['cost']} credits",
                    value=(
                        f"Developable Land: {details['developable_land']} units\n"
                        f"Multiplier: {details['development_cost_multiplier']}\n"
                        f"Base Employee Cap: {details['base_employee_cap']}\n"
                        f"Description: {details['description']}"
                    ),
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
    
    @commands.hybrid_command(name="viewcorpcats", with_app_command=True, description="View the available corporation categories and their sub-categories.")
    async def viewcorpcats(self, ctx:commands.Context):
        """See a list of the available corporation categories."""
        if ctx.interaction:
            await ctx.defer()
        message = ""
        for parent, details in CORPORATE_CATEGORIES.items():
            message += f"**{parent}:** {details['description']}\n"
            for sub, sub_desc in details["subcategories"].items():
                message += f" - **{sub}**: {sub_desc}\n"
            message += "\n"
        
        chunks = self.split_by_line(message)
        for chunk in chunks:
            await ctx.send(chunk)
    
    def split_by_line(self, content: str, limit: int = 2000):
        lines = content.splitlines(keepends=True)
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) > limit:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    
    @app_commands.command(name="setcorpdetails",
                           description="Set initial corp details.")
    @app_commands.describe(option="Select what detail you would like to set.",
                        company="The name (or identifier) of your corporation",
                        choice="The value you want to set for this detail")
    @app_commands.choices(option=[
        app_commands.Choice(name="Category", value="category"),
        app_commands.Choice(name="Sub-Category", value="subcategory")
    ])
    async def setcorpdetails(self, interaction: discord.Interaction, company: str, 
                            option: app_commands.Choice[str], choice: str):
        # Check if the company exists in our data
        if company not in self.data:
            await interaction.response.send_message("That company is not registered. Please retry.", ephemeral=True)
            return

        corp = self.data[company]

        # Check if the detail is already set.
        if corp.get(option.value) != "general" not in ["general", None]:
            await interaction.response.send_message(
                "This detail has already been set. This command only supports initial setup.", ephemeral=True)
            return

        # For both category and subcategory, we need to validate the choice.
        if option.value == "category":
            # For category, the choice must be one of the keys in CORPORATE_CATEGORIES.
            if choice not in CORPORATE_CATEGORIES:
                await interaction.response.send_message(
                    "This category does not exist. Please run /viewcorpcats to see available categories.", ephemeral=True)
                return
            # Set the category.
            corp["category"] = choice
            await interaction.response.send_message(
                f"The category for {company} has been set to **{choice}** successfully!", ephemeral=True)

        elif option.value == "subcategory":
            # For subcategory, first ensure that the category is already set.
            if not corp.get("category"):
                await interaction.response.send_message(
                    "Please set your corporation's category before setting a sub-category.", ephemeral=True)
                return
            parent_category = corp["category"]
            # Check that the parent category exists in CORPORATE_CATEGORIES.
            if parent_category not in CORPORATE_CATEGORIES:
                await interaction.response.send_message(
                    "The current category of your corporation is invalid. Please contact an admin.", ephemeral=True)
                return
            # Check that the provided subcategory exists under the parent's subcategories.
            subcategories = CORPORATE_CATEGORIES[parent_category]["subcategories"]
            if choice not in subcategories:
                await interaction.response.send_message(
                    "This sub-category does not exist under your current category.", ephemeral=True)
                return
            # Set the subcategory.
            corp["subcategory"] = choice
            await interaction.response.send_message(
                f"The sub-category for {company} has been set to **{choice}** successfully!", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid option.", ephemeral=True)
        
        save_corporations(self.data)
    
    @setcorpdetails.autocomplete("company")
    async def company_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []

        for key, details in self.data.items():
            comp_name = details.get("name", key)
            if details.get("CEO") == interaction.user.id and current.lower() in comp_name.lower():
                choices.append(app_commands.Choice(name=comp_name, value=comp_name))
        
        return choices
    
    @setcorpdetails.autocomplete("choice")
    async def choice_autocomplete(self, interaction:discord.Interaction, current: str):
        choices = []
        company = interaction.namespace.company
        option = interaction.namespace.option
        if option == "category":
            for category in CORPORATE_CATEGORIES.keys():
                choices.append(app_commands.Choice(name=category, value=category))
        else:
            current_cat = company.get("category")
            subcategory_dict = CORPORATE_CATEGORIES[current_cat]["subcategories"]
            for subcategory in subcategory_dict.keys():
                choices.append(app_commands.Choice(name=subcategory, value=subcategory))
        return choices



    
    @commands.hybrid_command(name="buyland", with_app_command=True, description="Purchase land for your corporation's HQ.")
    async def buyland(self, ctx: commands.Context, company: str, state: str, land_option: str):
        company = company.strip()
        state = state.strip()
        land_option = land_option.strip()
        if company not in self.data:
            await ctx.send("That company isn't registered. Please register it via the treasury cog.")
            return
        
        if state not in STATE_OPTIONS:
            await ctx.send("Invalid state. Please choose from: " + ", ".join(STATE_OPTIONS.keys()))
            return
        
        allowed_options = STATE_OPTIONS[state]["allowed_land_options"]
        if land_option not in allowed_options:
            await ctx.send(f"{land_option} is not available in {state}. Available options: " + ", ".join(allowed_options))
            return

        comp = self.data[company]
        if comp["CEO"] != str(ctx.author.id) and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"You are not the CEO of {company}.")
            return

        if comp.get("land"):
            await ctx.send(f"{company} already owns land and this command currently only supports purchasing one plot of land.")
            return

        # Adjust cost based on state modifier
        base_cost = LAND_OPTIONS[land_option]["cost"]
        state_modifier = STATE_OPTIONS[state]["land_cost_modifier"]
        cost = int(base_cost * state_modifier)
        
        if cost > comp.get("balance", 0):
            await ctx.send(f"Your corporation, {company}, does not have enough credits to purchase this land (cost: {cost} credits).")
            return

        comp["balance"] = comp.get("balance", 0) - cost
        comp["land"] = land_option
        comp["land_details"] = LAND_OPTIONS[land_option]
        comp["employee_cap"] = LAND_OPTIONS[land_option]["base_employee_cap"]
        save_corporations(self.data)
        await ctx.send(f"Congratulations! {company} has purchased **{land_option}** in {state} for {cost} credits as its HQ land.")

    
    @commands.hybrid_command(name="buyoffice", with_app_command=True, description="Purchase an office building for your corporation.")
    async def buyoffice(self, ctx: commands.Context, company: str, office_size: str):
        """
        Purchase an office building for your corporation.
        The office_size (e.g., 'hole-in-the-wall', 'office suite', 'small office building', 
        'warehouse', 'wide campus', or 'skyscraper') determines the cost, build time, land usage, 
        and the additional employee capacity.
        Note: Your corporation must have purchased land if the office option requires land.
        """
        if ctx.interaction:
            await ctx.defer()

        company = company.strip()
        office_size = office_size.lower().strip()

        if company not in self.data:
            await ctx.send("That company is not registered. Please register it using the treasury commands.")
            return

        comp = self.data[company]

        # Check if the caller is the CEO (or an admin)
        if comp["CEO"] != str(ctx.author.id) and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"You are not the CEO of {company}.")
            return

        # If the office option requires land (land_usage > 0), check that the company has purchased land
        if office_options[office_size]["land_usage"] > 0:
            if not comp.get("land"):
                return await ctx.send(f"{company} does not have any purchased land. To build a {office_size} office, you must first purchase land using /buyland.")
            available_land = comp["land_details"].get("developable_land", 0)
            required_land = office_options[office_size]["land_usage"]
            if available_land < required_land:
                return await ctx.send(f"{company} doesn't have enough developable land for a {office_size} office (requires {required_land} units, only {available_land} available).")
        
        option = office_options[office_size]
        total_cost = int(option["cost"] * comp["land_details"].get("development_cost_multiplier", 1.0))
        
        # Check company balance
        if total_cost > comp.get("balance", 0):
            await ctx.send(f"{company} doesn't have enough credits to purchase a {office_size} office (cost: {total_cost} credits).")
            return

        await bank.withdraw_credits(ctx.author, total_cost)
        comp["balance"] = comp.get("balance", 0) - total_cost
        
        # If the office requires land, reduce the available developable land accordingly.
        if option["land_usage"] > 0:
            comp["land_details"]["developable_land"] = available_land - option["land_usage"]

        await ctx.send(f"{company}'s {office_size} office building purchase has been initiated. Construction will take {option['build_time']} seconds.")
        await asyncio.sleep(option["build_time"])
        
        comp["hq_built"] = True
        comp["employee_cap"] += option["additional_employee_cap"]
        comp["office"] = office_size
        save_corporations(self.data)
        await ctx.send(f"Construction complete! {company}'s office building is now built. Its employee cap has increased by {option['additional_employee_cap']} to {comp['employee_cap']} employees.")
    
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
    
    @commands.hybrid_command(name="invest", with_app_command=True, 
                           description="Invest money into your corporation's account. "
                                       "This is recorded as a capital investment, not revenue.")
    async def invest(self, ctx: commands.Context, company: str, amount: int):
        if ctx.interaction:
            await ctx.defer()
        
        company = company.strip()
        # Check that the specified company exists
        if company not in self.data:
            await ctx.send("That corporation is not registered.")
            return

        corp = self.data[company]
        # Verify that the user is the CEO (or has admin privileges)
        if corp.get("CEO") != str(ctx.author.id) and not ctx.author.guild_permissions.administrator:
            await ctx.send("You do not have permission to invest in that corporation.")
            return

        # Check that the user has sufficient credits
        if not await bank.can_spend(ctx.author, amount):
            await ctx.send("You don't have enough credits to invest that amount.")
            return

        await bank.withdraw_credits(ctx.author, amount)
        
        # Initialize company account balance if not already present
        if "balance" not in corp:
            corp["balance"] = 0
        corp["balance"] += amount

        save_corporations(self.data)
        await ctx.send(f"Successfully invested {humanize.intword(amount)} credits into "
                    f"{corp.get('name', company)}'s account. New company balance: {humanize.intword(corp['balance'])} credits.")

        
    @commands.hybrid_command(name="companybalance", with_app_command=True, 
                            description="View your corporation's account balance.")
    async def companybalance(self, ctx: commands.Context, company: str):
        company = company.strip()
        if company not in self.data:
            await ctx.send("That corporation is not registered.")
            return

        corp = self.data[company]
        # Verify that the user is the CEO (or admin)
        if corp.get("CEO") != str(ctx.author.id) and not ctx.author.guild_permissions.administrator:
            await ctx.send("You do not have permission to view that corporation's balance.")
            return

        balance = corp.get("balance", 0)
        await ctx.send(f"The account balance for {corp.get('name', company)} is {humanize.intword(balance)} credits.")


    
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
    