import discord
import json
import os
from datetime import datetime, timedelta
from redbot.core import commands

DATA_FILE = "nations.json"

def load_nations_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_nations_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_initial_stats(difficulty: str):
    """
    Returns a dictionary of initial nation stats based on difficulty.
    Additional stats have been added for a more nuanced simulation.
    """
    diff = difficulty.lower()
    if diff == "easy":
        return {
            "population": 150000,
            "gdp": 2000000,
            "troops": 1500,
            "land_area": 15000,  # km²
            "citizen_satisfaction": 80,  # %
            "international_education": 60,  # percentile
            "environmental_quality": 90,  # %
            "median_salary": 30000,  # $
            "wealth_inequality": 30,  # (0-100 index)
            "crime_rate": 10,  # (0-100 index)
            "urbanization": 70,  # %
            "unemployment_rate": 3,  # %
            "healthcare_quality": 85,  # %
            "infrastructure_quality": 80,  # %
            "diplomatic_reputation": 70,  # %
            "economic_growth": 3,  # %
            "national_debt": 100000,  # $
            "leader_approval": 85,  # %
            # New additional stats:
            "innovation": 70,
            "international_trade": 70,
            "social_welfare": 70,
            "public_infrastructure": 70,
            "environmental_sustainability": 80,
            "border_openness": 80,
            "homeless_rate": 5,
            "electricity_rate": 90,
            "literacy_rate": 90,
            "death_rate": 3,
            "infection_rate": 2,
            "birth_rate": 4
        }
    elif diff == "hard":
        return {
            "population": 80000,
            "gdp": 800000,
            "troops": 800,
            "land_area": 8000,
            "citizen_satisfaction": 60,
            "international_education": 40,
            "environmental_quality": 70,
            "median_salary": 15000,
            "wealth_inequality": 50,
            "crime_rate": 30,
            "urbanization": 40,
            "unemployment_rate": 10,
            "healthcare_quality": 60,
            "infrastructure_quality": 55,
            "diplomatic_reputation": 40,
            "economic_growth": 1,
            "national_debt": 500000,
            "leader_approval": 50,
            # New additional stats for hard:
            "innovation": 40,
            "international_trade": 40,
            "social_welfare": 40,
            "public_infrastructure": 40,
            "environmental_sustainability": 50,
            "border_openness": 40,
            "homeless_rate": 15,
            "electricity_rate": 60,
            "literacy_rate": 50,
            "death_rate": 8,
            "infection_rate": 10,
            "birth_rate": 2
        }
    else:  # medium
        return {
            "population": 100000,
            "gdp": 1000000,
            "troops": 1000,
            "land_area": 10000,
            "citizen_satisfaction": 70,
            "international_education": 50,
            "environmental_quality": 80,
            "median_salary": 20000,
            "wealth_inequality": 40,
            "crime_rate": 20,
            "urbanization": 50,
            "unemployment_rate": 5,
            "healthcare_quality": 70,
            "infrastructure_quality": 65,
            "diplomatic_reputation": 50,
            "economic_growth": 2,
            "national_debt": 200000,
            "leader_approval": 70,
            # New additional stats for medium:
            "innovation": 50,
            "international_trade": 50,
            "social_welfare": 50,
            "public_infrastructure": 50,
            "environmental_sustainability": 60,
            "border_openness": 60,
            "homeless_rate": 10,
            "electricity_rate": 80,
            "literacy_rate": 70,
            "death_rate": 5,
            "infection_rate": 5,
            "birth_rate": 3
        }

policy_requirements = {
    "healthcare": 70,
    "education": 60,
    "environment": 50,
    "national_holiday": 0
}

# -- Derived stat update functions --

def update_citizen_satisfaction(nation):
    """
    Recalculates citizen satisfaction as an average of key social indicators.
    Uses healthcare quality, social welfare, international education,
    environmental quality, and public infrastructure, plus a bonus for low crime.
    """
    hs = nation.get("healthcare_quality", 70)
    sw = nation.get("social_welfare", 50)
    ie = nation.get("international_education", 50)
    eq = nation.get("environmental_quality", 80)
    pi = nation.get("public_infrastructure", 50)
    crime = nation.get("crime_rate", 20)
    nation["citizen_satisfaction"] = int((hs + sw + ie + eq + pi + (100 - crime)) / 6)

def update_birth_rate(nation):
    """
    Computes birth rate as proportional to citizen satisfaction,
    social welfare, and healthcare quality, reduced by unemployment.
    """
    cs = nation.get("citizen_satisfaction", 70)
    sw = nation.get("social_welfare", 50)
    hs = nation.get("healthcare_quality", 70)
    unemp = nation.get("unemployment_rate", 5)
    nation["birth_rate"] = (cs + sw + hs) / 3 - unemp

def update_death_rate(nation):
    """
    Death rate is inversely related to healthcare and environmental quality.
    """
    hs = nation.get("healthcare_quality", 70)
    eq = nation.get("environmental_quality", 80)
    nation["death_rate"] = max(0, 10 - ((hs / 10) + (eq / 10)))

def update_homeless_rate(nation):
    """
    Homeless rate increases with wealth inequality and unemployment, but is mitigated by social welfare.
    """
    wi = nation.get("wealth_inequality", 40)
    unemp = nation.get("unemployment_rate", 5)
    sw = nation.get("social_welfare", 50)
    nation["homeless_rate"] = max(0, (wi + unemp * 5) - sw)

def update_electricity_rate(nation):
    """
    Electricity rate depends on public infrastructure.
    """
    pi = nation.get("public_infrastructure", 50)
    nation["electricity_rate"] = min(100, pi + 20)

def update_literacy_rate(nation):
    """
    Literacy rate is the average of international education and public infrastructure.
    """
    ie = nation.get("international_education", 50)
    pi = nation.get("public_infrastructure", 50)
    nation["literacy_rate"] = int((ie + pi) / 2)

def update_infection_rate(nation):
    """
    Infection rate is inversely related to healthcare quality and literacy rate.
    """
    hs = nation.get("healthcare_quality", 70)
    lr = nation.get("literacy_rate", 60)
    nation["infection_rate"] = max(0, 20 - ((hs + lr) / 10))

def update_dependent_stats(nation):
    """
    Updates all derived or interconnected stats.
    """
    update_citizen_satisfaction(nation)
    update_birth_rate(nation)
    update_death_rate(nation)
    update_homeless_rate(nation)
    update_electricity_rate(nation)
    update_literacy_rate(nation)
    update_infection_rate(nation)

# -- Main Cog Class --

class SpideyNations(commands.Cog):
    """A nation-building simulation game inspired by NationStates"""

    def __init__(self, bot):
        self.bot = bot
        self.nations = load_nations_data()
    
    @commands.hybrid_command(name="startnation", with_app_command=True, description="Create your own nation!")
    async def startnation(self, ctx: commands.Context, nation_name: str, difficulty: str = "medium"):
        """Create your own nation with a custom name."""
        user_id = str(ctx.author.id)
        if user_id in self.nations:
            await ctx.send("You already have a nation!")
            return
        
        stats = get_initial_stats(difficulty)
        self.nations[user_id] = {
            "name": nation_name,
            "capital": "Capital City",
            "president": ctx.author.display_name,
            "difficulty": difficulty.lower(),
            "ideology": "None",
            **stats,
            "policies": {},
            "policy_adjustments": {},
            "history": []
        }
        save_nations_data(self.nations)
        await ctx.send(
            f"The '{nation_name}' has officially declared independence from its former land!\n"
            f"President {ctx.author.display_name}, your people look to you to lead them into a golden age!\n"
            "As of now your capital is called \"Capital City\" if you want to change that please /setcapital and /setpresident if you want to change your own name.\n"
            "Use /setideology to set your nation's ideology."
        )
    
    @commands.hybrid_command(name="setcapital", with_app_command=True, description="Set your nation's capital.")
    async def setcapital(self, ctx: commands.Context, *, capital: str):
        """Set the capital of your nation."""
        user_id = str(ctx.author.id)
        if user_id not in self.nations:
            await ctx.send("You need to start a nation first using /startnation")
            return

        self.nations[user_id]["capital"] = capital
        self.nations[user_id]["history"].append(f"Capital changed to {capital}")
        save_nations_data(self.nations)
        await ctx.send(f"Your nation's capital has been set to {capital}.")
    
    @commands.hybrid_command(name="setpresident", with_app_command=True, description="Set your nation's president name.")
    async def setpresident(self, ctx: commands.Context, *, president: str):
        """Set the president's name for your nation."""
        user_id = str(ctx.author.id)
        if user_id not in self.nations:
            await ctx.send("You need to start a nation first using /startnation")
            return

        self.nations[user_id]["president"] = president
        self.nations[user_id]["history"].append(f"President set to {president}")
        save_nations_data(self.nations)
        await ctx.send(f"Your nation's president is now {president}.")
        
    @commands.hybrid_command(name="nationstatus", with_app_command=True, description="Display your nation's status.")
    async def nationstatus(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        if user_id not in self.nations:
            await ctx.send("You must first start a nation using /startnation.")
            return

        nation = self.nations[user_id]
        status = (
            f"**Nation:** {nation['name']}\n"
            f"**Capital:** {nation['capital']}\n"
            f"**President:** {nation['president']}\n"
            f"**Difficulty:** {nation['difficulty']}\n"
            f"**Ideology:** {nation['ideology']}\n\n"
            f"**Population:** {nation['population']}\n"
            f"**GDP:** ${nation['gdp']:,} per annum\n"
            f"**Troops:** {nation['troops']}\n"
            f"**Land Area:** {nation['land_area']} km²\n\n"
            f"**Citizen Satisfaction:** {nation['citizen_satisfaction']}%\n"
            f"**International Education:** {nation['international_education']}%\n"
            f"**Environmental Quality:** {nation['environmental_quality']}%\n"
            f"**Median Salary:** ${nation['median_salary']:,}\n"
            f"**Wealth Inequality:** {nation['wealth_inequality']}\n"
            f"**Crime Rate:** {nation['crime_rate']}\n"
            f"**Urbanization:** {nation['urbanization']}%\n"
            f"**Unemployment Rate:** {nation['unemployment_rate']}%\n"
            f"**Healthcare Quality:** {nation['healthcare_quality']}%\n"
            f"**Infrastructure Quality:** {nation['infrastructure_quality']}%\n"
            f"**Diplomatic Reputation:** {nation['diplomatic_reputation']}%\n"
            f"**Economic Growth:** {nation['economic_growth']}%\n"
            f"**National Debt:** ${nation['national_debt']:,}\n\n"
            f"**Leader Approval:** {nation['leader_approval']}%\n\n"
            f"**Innovation:** {nation.get('innovation', 'N/A')}\n"
            f"**International Trade:** {nation.get('international_trade', 'N/A')}\n"
            f"**Social Welfare:** {nation.get('social_welfare', 'N/A')}\n"
            f"**Public Infrastructure:** {nation.get('public_infrastructure', 'N/A')}\n"
            f"**Environmental Sustainability:** {nation.get('environmental_sustainability', 'N/A')}\n"
            f"**Border Openness:** {nation.get('border_openness', 'N/A')}\n\n"
            f"**Policies:** {nation['policies']}\n"
            f"**History:** {nation['history']}\n"
        )
        await ctx.send(status)
    
    @commands.hybrid_command(name="setideology", with_app_command=True, description="Set your nation's ideology.")
    async def setideology(self, ctx: commands.Context, *, ideology: str):
        user_id = str(ctx.author.id)
        if user_id not in self.nations:
            await ctx.send("Please start a nation using /startnation first.")
            return

        self.nations[user_id]["ideology"] = ideology
        self.nations[user_id]["history"].append(f"Ideology set to {ideology}")
        save_nations_data(self.nations)
        await ctx.send(f"Your nation’s ideology has been set to {ideology}. Your policies now reflect this stance.")
    
    @commands.hybrid_command(name="adjustapolicy", with_app_command=True, description="Adjust an existing policy.")
    async def adjustapolicy(self, ctx: commands.Context, policy: str, *, new_value: str):
        user_id = str(ctx.author.id)
        if user_id not in self.nations:
            await ctx.send("You must first start a nation using /startnation.")
            return

        policy_key = policy.lower()
        nation = self.nations[user_id]
        if policy_key not in nation["policies"]:
            await ctx.send("That policy doesn't exist. Please use /setinitialpolicy to define your core policies.")
            return

        required_approval = policy_requirements.get(policy_key, 0)
        if nation["leader_approval"] < required_approval:
            await ctx.send(f"Your leader approval ({nation['leader_approval']}%) is too low to adjust {policy_key} (requires {required_approval}%).")
            return

        if nation["ideology"].lower() in ["democratic", "democracy"]:
            last_adjustments = nation.get("policy_adjustments", {})
            last_time_str = last_adjustments.get(policy_key)
            if last_time_str:
                last_time = datetime.fromisoformat(last_time_str)
                if datetime.utcnow() - last_time < timedelta(hours=1):
                    await ctx.send("As a democratic nation, you can only adjust one policy per hour. Please wait before making further changes.")
                    return

        nation["policies"][policy_key] = new_value
        nation["history"].append(f"Policy '{policy_key}' adjusted to '{new_value}'.")
        nation.setdefault("policy_adjustments", {})[policy_key] = datetime.utcnow().isoformat()
        # Update dependent stats after policy adjustment.
        update_dependent_stats(nation)
        save_nations_data(self.nations)
        await ctx.send(f"Policy '{policy_key}' has been updated to '{new_value}'.")
    
    @commands.hybrid_command(name="startpolicytest", with_app_command=True, description="Take an extensive policy test affecting your nation's stats.")
    async def startpolicytest(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        if user_id not in self.nations:
            await ctx.send("You must first start a nation using /startnation.")
            return

        questions = [
            {
                "q": "Q1. A country should be judged by how it treats its worst-off citizens.",
                "modifiers": {
                    "strongly disagree": {"citizen_satisfaction": -5, "gdp": -50000},
                    "disagree": {"citizen_satisfaction": -3, "gdp": -25000},
                    "agree": {"citizen_satisfaction": 3, "gdp": 25000},
                    "strongly agree": {"citizen_satisfaction": 5, "gdp": 50000}
                }
            },
            {
                "q": "Q2. Corporations are good for society.",
                "modifiers": {
                    "strongly disagree": {"gdp": -60000, "citizen_satisfaction": -4, "wealth_inequality": 5},
                    "disagree": {"gdp": -30000, "citizen_satisfaction": -2, "wealth_inequality": 3},
                    "agree": {"gdp": 30000, "citizen_satisfaction": 2, "wealth_inequality": -3},
                    "strongly agree": {"gdp": 60000, "citizen_satisfaction": 4, "wealth_inequality": -5}
                }
            },
            {
                "q": "Q3. Marijuana should be legal.",
                "modifiers": {
                    "strongly disagree": {"gdp": -100000, "citizen_satisfaction": -5, "unemployment_rate": -1},
                    "disagree": {"gdp": -50000, "citizen_satisfaction": -3, "unemployment_rate": -0.5},
                    "agree": {"gdp": 50000, "citizen_satisfaction": 3, "unemployment_rate": 1},
                    "strongly agree": {"gdp": 100000, "citizen_satisfaction": 5, "unemployment_rate": 2}
                }
            },
            {
                "q": "Q4. The world needs to rediscover its spirituality.",
                "modifiers": {
                    "strongly disagree": {"international_education": -5, "citizen_satisfaction": -3},
                    "disagree": {"international_education": -3, "citizen_satisfaction": -1},
                    "agree": {"international_education": 3, "citizen_satisfaction": 1},
                    "strongly agree": {"international_education": 5, "citizen_satisfaction": 3}
                }
            },
            {
                "q": "Q5. Young people should perform a year's compulsory military service.",
                "modifiers": {
                    "strongly disagree": {"troops": -100, "citizen_satisfaction": -4},
                    "disagree": {"troops": -50, "citizen_satisfaction": -2},
                    "agree": {"troops": 50, "citizen_satisfaction": 2},
                    "strongly agree": {"troops": 100, "citizen_satisfaction": 4}
                }
            },
            {
                "q": "Q6. Capitalism is on the way out.",
                "modifiers": {
                    "strongly disagree": {"gdp": 50000, "citizen_satisfaction": 3},
                    "disagree": {"gdp": 25000, "citizen_satisfaction": 1},
                    "agree": {"gdp": -25000, "citizen_satisfaction": -1},
                    "strongly agree": {"gdp": -50000, "citizen_satisfaction": -3}
                }
            },
            {
                "q": "Q7. Without democracy, a country has nothing.",
                "modifiers": {
                    "strongly disagree": {"leader_approval": -10},
                    "disagree": {"leader_approval": -5},
                    "agree": {"leader_approval": 5},
                    "strongly agree": {"leader_approval": 10}
                }
            },
            {
                "q": "Q8. It's better to deter criminals than rehabilitate them.",
                "modifiers": {
                    "strongly disagree": {"crime_rate": -5, "citizen_satisfaction": 2},
                    "disagree": {"crime_rate": -2, "citizen_satisfaction": 1},
                    "agree": {"crime_rate": 2, "citizen_satisfaction": -1},
                    "strongly agree": {"crime_rate": 5, "citizen_satisfaction": -2}
                }
            },
            {
                "q": "Q9. The government should heavily subsidize R&D to spur technological innovation.",
                "modifiers": {
                    "strongly disagree": {"innovation": -10, "national_debt": 50000},
                    "disagree": {"innovation": -5, "national_debt": 25000},
                    "agree": {"innovation": 5, "national_debt": -25000},
                    "strongly agree": {"innovation": 10, "national_debt": -50000}
                }
            },
            {
                "q": "Q10. Free trade agreements are essential for economic growth, even if they cause job displacement.",
                "modifiers": {
                    "strongly disagree": {"international_trade": -10, "wealth_inequality": 5},
                    "disagree": {"international_trade": -5, "wealth_inequality": 2},
                    "agree": {"international_trade": 5, "wealth_inequality": -2},
                    "strongly agree": {"international_trade": 10, "wealth_inequality": -5}
                }
            },
            {
                "q": "Q11. A strong social safety net is crucial so that a booming economy benefits everyone.",
                "modifiers": {
                    "strongly disagree": {"social_welfare": -10, "citizen_satisfaction": -4},
                    "disagree": {"social_welfare": -5, "citizen_satisfaction": -2},
                    "agree": {"social_welfare": 5, "citizen_satisfaction": 2},
                    "strongly agree": {"social_welfare": 10, "citizen_satisfaction": 4}
                }
            },
            {
                "q": "Q12. The nation should invest in renewable energy even if it raises short-term costs.",
                "modifiers": {
                    "strongly disagree": {"environmental_sustainability": -10, "gdp": -50000},
                    "disagree": {"environmental_sustainability": -5, "gdp": -25000},
                    "agree": {"environmental_sustainability": 5, "gdp": 25000},
                    "strongly agree": {"environmental_sustainability": 10, "gdp": 50000}
                }
            }
        ]

        valid_answers = ["strongly disagree", "disagree", "agree", "strongly agree"]

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("Starting the comprehensive policy test. Answer each question with: Strongly Disagree, Disagree, Agree, or Strongly Agree.")

        for q in questions:
            await ctx.send(q["q"])
            try:
                response = await self.bot.wait_for("message", check=check, timeout=60.0)
            except Exception:
                await ctx.send("Timed out waiting for an answer. Please try again.")
                return

            answer = response.content.lower().strip()
            if answer not in valid_answers:
                await ctx.send("Invalid answer. Please answer exactly with: Strongly Disagree, Disagree, Agree, or Strongly Agree.")
                return

            modifiers = q["modifiers"][answer]
            for stat, change in modifiers.items():
                current = self.nations[user_id].get(stat, 0)
                self.nations[user_id][stat] = current + change
                self.nations[user_id]["history"].append(f"{q['q']} -> {answer.title()}: {stat} changed by {change}.")

        # After processing all questions, update dependent stats.
        update_dependent_stats(self.nations[user_id])
        save_nations_data(self.nations)
        await ctx.send("Policy test complete! Your nation's stats have been updated based on your responses.")

        nation = self.nations[user_id]
        summary = (
            f"**Updated Stats for {nation['name']}**\n"
            f"Citizen Satisfaction: {nation.get('citizen_satisfaction', 'N/A')}%\n"
            f"GDP: ${nation.get('gdp', 0):,}\n"
            f"Troops: {nation.get('troops', 'N/A')}\n"
            f"Leader Approval: {nation.get('leader_approval', 'N/A')}%\n"
            f"Innovation: {nation.get('innovation', 'N/A')}\n"
            f"International Trade: {nation.get('international_trade', 'N/A')}\n"
            f"Social Welfare: {nation.get('social_welfare', 'N/A')}\n"
            f"Public Infrastructure: {nation.get('public_infrastructure', 'N/A')}\n"
            f"Environmental Sustainability: {nation.get('environmental_sustainability', 'N/A')}\n"
            f"Border Openness: {nation.get('border_openness', 'N/A')}\n"
            f"Homeless Rate: {nation.get('homeless_rate', 'N/A')}\n"
            f"Electricity Rate: {nation.get('electricity_rate', 'N/A')}%\n"
            f"Literacy Rate: {nation.get('literacy_rate', 'N/A')}%\n"
            f"Death Rate: {nation.get('death_rate', 'N/A')}\n"
            f"Infection Rate: {nation.get('infection_rate', 'N/A')}\n"
            f"Birth Rate: {nation.get('birth_rate', 'N/A')}\n"
        )
        await ctx.send(summary)