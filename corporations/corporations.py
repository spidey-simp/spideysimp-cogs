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
from .config import STATE_OPTIONS, LAND_OPTIONS, office_options, CORPORATE_CATEGORIES, PRODUCT_TEMPLATES
import copy


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
        "active_projects": [], 
        "pending_projects": {},
        "products": {}
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
        
        allowed_cats = PRODUCT_TEMPLATES.keys()
        if corp["category"] not in allowed_cats:
            await ctx.send(f"This command currently only supports companies in the following categories: {', '.join(allowed_cats)}")
        
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
        
        corp = self.data[company]
        
        now = datetime.now(timezone.utc)
        timefinish = active_projs[company][str(project)]["time"]

        finish_time = datetime.fromisoformat(timefinish)

        if now >= finish_time:
            outcome = self.chance_of_failure(self.data[company], active_projs[company][str(project)]["quality"])
            if outcome == "failed":
                message = self.get_rnd_message("failure")
                active_projs[company].pop(str(project), None)
                corp["active_projects"].remove(str(project))
            elif outcome == "postponed":
                message = self.get_rnd_message("in_progress")
                additional_time = random.randint(1, 60)
                message += f"\nCheck back in {additional_time} minutes!"
                new_finish_time = now + timedelta(minutes=additional_time)
                active_projs[company][str(project)]["time"] = new_finish_time.isoformat()
            else:
                corp_cat = corp["category"]
                if corp_cat not in PRODUCT_TEMPLATES:
                    message = "I am so sorry! At the time of my writing this, products are only supported for tech companies! SORRY!"
                else:
                    rand_key = random.choice(list(PRODUCT_TEMPLATES[corp_cat].keys()))
                    message = self.get_rnd_message("success_new").format(category_product=rand_key)
                    if str(project) not in corp["pending_projects"]:
                        corp["pending_projects"][str(project)] = {}
                    for k, v in active_projs[company][str(project)].items():
                        corp["pending_projects"][str(project)][k] = v
                    corp["pending_projects"][str(project)]["product_type"] = rand_key
                    active_projs[company].pop(str(project), None)
                    if str(project) in corp["active_projects"]:
                        corp["active_projects"].remove(str(project))
            corp["randd_skill"] += random.randint(1, 2)
            save_corporations(self.data)
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
    
    @app_commands.command(name="create_product", description="Take a pending product and make it so!")
    @app_commands.describe(company="The name of the company to make the product for!", project="The project id!", name="The name to give your product!", scrapit = "Actually I want to trash it - True = Trash the product.")
    async def create_product(self, interaction:discord.Interaction, company: str, project: str, name: str=None, scrapit: bool=False):
        await interaction.response.defer()

        corp = self.data[company]
        if scrapit:
            corp["pending_projects"].pop(project, None)
            await interaction.followup.send(f"The project with ID **{project}** has been scrapped.")
            return
        
        proj_dict = corp["pending_projects"][project]
        product_type = proj_dict["product_type"]
        template_dict = copy.deepcopy(PRODUCT_TEMPLATES[corp["category"]][product_type])


        if not name:
            await interaction.followup.send("Assuming you didn't mean to delete the product, you need to give it a name.")
            return
        
        if "products" not in corp:
            corp["products"] = {}
        
        if name in corp["products"]:
            await interaction.followup.send(f"You've already named a product {name} for {company}! Please choose a different name!")
            return
        
        corp["products"][name] = template_dict

        product_dict = corp["products"][name]

        product_dict["base_quality"] = max(template_dict["base_quality"], proj_dict["quality"])

        for stat, value in product_dict["stats"].items():
            variation = random.randint(-5, 5)
            product_dict["stats"][stat] = max(template_dict["stats"][stat], (proj_dict["quality"] + variation))
        
        if proj_dict["quality"] >= 50:
            prod_variation = random.uniform(.9, .99)
            product_dict["base_production"] = template_dict["base_production"] * prod_variation
            cost_variation = random.uniform(.9, .99)
            product_dict["base_manufacture_cost"] = int(template_dict["base_manufacture_cost"] * cost_variation)
        else:
            prod_variation = random.uniform(1.01, 1.1)
            product_dict["base_production"] = template_dict["base_production"] * prod_variation
            cost_variation = random.uniform(1.01, 1.1)
            product_dict["base_manufacture_cost"] = int(template_dict["base_manufacture_cost"] * cost_variation)
        
        corp["pending_projects"].pop(project, None)
        save_corporations(self.data)

        await interaction.followup.send(f"Your {name} {product_type} has been created with a quality of {product_dict['base_quality']}%! From here you can either refine the product or put it straight onto the market!")





    
    @create_product.autocomplete("company")
    async def company_autocomplete(self, interaction:discord.Interaction, current: str):
        choices = []
        for key, details in self.data.items():
            comp_name = details.get("name", key)
            if details.get("CEO") == interaction.user.id and current.lower() in comp_name.lower():
                choices.append(app_commands.Choice(name=comp_name, value=comp_name))
        
        return choices
    
    @create_product.autocomplete("project")
    async def project_autocomplete(self, interaction:discord.Interaction, current: str):
        company = interaction.namespace.company
        choices = []
        
        if company in self.data:
            pending_projects = self.data[company].get("pending_projects", [])
            for proj in pending_projects:
                if current.lower() in proj.lower():
                    choices.append(app_commands.Choice(name=proj, value=proj))
        
        return choices


    
    @commands.command(name="fixproj")
    @commands.admin_or_permissions(administrator=True)
    async def fixproj(self, ctx, company: str, project: str):
        """Temporarily fix a pending project's product_type."""
        # Ensure the company exists in your data
        if company not in self.data:
            await ctx.send("That company isn't registered.")
            return

        corp = self.data[company]
        pending = corp.get("pending_projects", {})
        if project not in pending:
            await ctx.send("Project not found in pending projects.")
            return

        # Set the product_type to the correct product name.
        # If currently product_type is '1' but it should be "Smartphone":
        pending[project]["product_type"] = "Smartphone"
        # Save your changes:
        save_corporations(self.data)
        await ctx.send(f"Project {project} for company {company} has been fixed!")


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


    
    @app_commands.command(name="companyinfo", description="View your corporation's details.")
    @app_commands.describe(company="The Company you want to see the info for!")
    async def companyinfo(self, interaction: discord.Interaction, company: str):
        """
        Show detailed info for a given company.
        If no company is specified, display the corporation for the caller.
        """
        await interaction.response.defer()

        # If no company name is provided, assume the caller's company.
        company = company.strip()
        if company not in self.data:
            await interaction.followup.send("That company is not registered.")
            return

        corp = self.data[company]
        msg = f"**Company Information for {corp.get('name', 'Unnamed Corporation')}**\n"
        msg += f"CEO: <@{corp.get('CEO', 'N/A')}>\n"
        msg += f"Category: {corp.get('category', 'N/A')}\n"
        msg += f"Land: {corp.get('land', 'None')}\n"
        msg += f"Office: {corp.get('office', 'Not built')}\n"
        msg += f"Employee Cap: {corp.get('employee_cap', 'N/A')}\n"
        register_date = corp.get('date_registered')
        formatted_date = datetime.fromisoformat(register_date)
        final_format = formatted_date.strftime("%m/%d/%Y")
        msg += f"Date Registered: {final_format}\n"
        await interaction.followup.send(msg)

    
    @companyinfo.autocomplete("company")
    async def company_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []

        for key, details in self.data.items():
            comp_name = details.get("name", key)
            if details.get("CEO") == interaction.user.id and current.lower() in comp_name.lower():
                choices.append(app_commands.Choice(name=comp_name, value=comp_name))
        
        return choices
    