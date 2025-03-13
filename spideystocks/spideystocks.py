import discord
import json
import os
import random
import io
from datetime import datetime, timedelta, timezone
from discord.ext import commands, tasks
from redbot.core import commands, bank
import matplotlib.pyplot as plt
import humanize
import pytz

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "market_data.json")
HISTORY_LIMIT = 288

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {
            "companies": {
                "LemonTech": {
                    "price": 120,
                    "name": "LemonTech Inc.",
                    "dividend_yield": 0.03,
                    "bankruptcy_threshold": 60,
                    "price_history": [120],
                    "total_shares": 1000000,
                    "available_shares": 1000000
                },
                "NascarCorp": {
                    "price": 90,
                    "name": "Nascar Corp.",
                    "dividend_yield": 0.02,
                    "bankruptcy_threshold": 45,
                    "price_history": [90],
                    "total_shares": 800000,
                    "available_shares": 800000
                },
                "MM500": {
                    "price": 50,
                    "name": "M&M 500 Ltd.",
                    "dividend_yield": 0.04,
                    "bankruptcy_threshold": 25,
                    "price_history": [50],
                    "total_shares": 500000,
                    "available_shares": 500000
                },
                "SpideySells": {
                    "price": 110,
                    "name": "SpideySells Inc.",
                    "dividend_yield": 0.015,
                    "bankruptcy_threshold": 55,
                    "price_history": [110],
                    "total_shares": 600000,
                    "available_shares": 600000
                },
                "BananaRepublic": {
                    "price": 70,
                    "name": "Banana Republic Co.",
                    "dividend_yield": 0.025,
                    "bankruptcy_threshold": 35,
                    "price_history": [70],
                    "total_shares": 700000,
                    "available_shares": 700000
                }
            },
            "portfolios": {}
        }
    
    default_fields = {
        "category": "general",
        "CEO": "Unknown",
        "location": "Unknown",
        "employees": 0,
        "date_established": "Unknown",
        "daily_volume": 100000,
        "total_shares": 1000000,
        "available_shares": None  # we'll set this to total_shares if missing
    }
    for symbol, company in data.get("companies", {}).items():
        for field, default in default_fields.items():
            if field not in company:
                # For available_shares, if missing, set it to total_shares.
                company[field] = company["total_shares"] if field == "available_shares" else default
    

    default_indices = {
        "Nascar Index": {"value": 1000.0, "history": [1000.0]},
        "M&M Index": {"value": 800.0, "history": [800.0]},
        "Dough Jones Index": {"value": 950.0, "history": [950.0]}
    }
    if "indices" not in data:
        data["indices"] = default_indices
    else:
        for key, default in default_indices.items():
            if key not in data["indices"]:
                data["indices"][key] = default
    save_data(data)
    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# Expanded list of whole-market events.
# Expanded event lists:
WHOLE_MARKET_EVENTS = [
    {"message": "Congress lowers regulations, boosting overall investor sentiment!", "modifier": 0.02},
    {"message": "Banks raise interest rates, dampening market sentiment.", "modifier": -0.03},
    {"message": "A national holiday occurs, leading to increased consumer optimism.", "modifier": 0.01},
    {"message": "Global trade tensions ease, lifting investor confidence.", "modifier": 0.015},
    {"message": "An economic stimulus package is announced by the government.", "modifier": 0.025},
    {"message": "Unexpected surge in consumer spending rallies the market!", "modifier": 0.03},
    {"message": "Major geopolitical conflict intensifies, causing widespread market anxiety.", "modifier": -0.025},
    {"message": "The central bank announces new monetary policy changes, affecting markets.", "modifier": -0.01},
    {"message": "Inflation fears subside as prices stabilize, improving market sentiment.", "modifier": 0.02},
    {"message": "The tech sector shows impressive growth, positively influencing the overall market.", "modifier": 0.03},
    {"message": "Energy prices drop significantly, benefiting consumer spending and market stability.", "modifier": 0.015},
    {"message": "Unemployment figures fall, spurring renewed market optimism.", "modifier": 0.02},
    {"message": "Financial regulators ease restrictions, fueling market enthusiasm.", "modifier": 0.025},
    {"message": "International trade agreements are signed, lifting global investor confidence.", "modifier": 0.02},
    {"message": "A major recession scare is averted, causing markets to rally.", "modifier": 0.03}
]

SECTOR_EVENTS = [
    {"message": "A breakthrough in renewable energy policy boosts tech and consumer goods sectors!", "affected_sectors": ["tech", "consumer goods"], "modifier": 0.04},
    {"message": "New healthcare regulations increase costs for healthcare providers.", "affected_sectors": ["healthcare"], "modifier": -0.05},
    {"message": "Entertainment tax cuts spur growth in the entertainment industry.", "affected_sectors": ["entertainment"], "modifier": 0.03},
    {"message": "A surge in travel demand boosts the travel sector.", "affected_sectors": ["travel"], "modifier": 0.05}
]

INDIVIDUAL_EVENTS = [
    {"message": "{affected_company} unveils a groundbreaking new product!", "modifier": 0.05},
    {"message": "A class action lawsuit is filed against {affected_company}, causing shares to plummet.", "modifier": -0.06},
    {"message": "{affected_company} reports record profits this quarter, boosting its stock price.", "modifier": 0.04},
    {"message": "A major scandal hits {affected_company}, leading to a significant drop in share price.", "modifier": -0.07},
    {"message": "{affected_company} announces a strategic partnership that excites investors.", "modifier": 0.05},
    {"message": "{affected_company} faces severe supply chain issues, impacting revenue projections.", "modifier": -0.04},
    {"message": "An innovative R&D breakthrough at {affected_company} lifts market expectations.", "modifier": 0.06},
    {"message": "{affected_company} misses earnings estimates, sending shares downward.", "modifier": -0.05},
    {"message": "A positive credit rating upgrade boosts investor confidence in {affected_company}.", "modifier": 0.03},
    {"message": "{affected_company} launches an aggressive marketing campaign, driving demand.", "modifier": 0.04},
    {"message": "A significant management shakeup unsettles investors at {affected_company}.", "modifier": -0.03},
    {"message": "{affected_company} secures a large government contract, sparking enthusiasm.", "modifier": 0.05},
    {"message": "{affected_company} faces regulatory scrutiny that shakes investor confidence.", "modifier": -0.04},
    {"message": "A surprise merger announcement sends {affected_company}'s shares soaring.", "modifier": 0.06},
    {"message": "{affected_company} cuts costs significantly, resulting in improved profitability.", "modifier": 0.03}
]



class SpideyStocks(commands.Cog):
    """A simple stock market simulation cog."""

    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()
        self.investor_modifier = 0.0
        self.market_injection = 0.0
        self.index_modifier = 0.0
        tz = pytz.timezone("US/Pacific")
        now = datetime.now(tz)
        if now.hour < 9 or now.hour >= 17:
            self.market_closed = True
        else:
            self.market_closed = False

        # Always start the market_check_loop so the market status gets updated.
        self.market_check_loop.start()
        self.distribute_dividends.start()
        # Only start update tasks if the market is open.
        if not self.market_closed:
            self.bot.loop.create_task(self.market_open())

    
    def cog_unload(self):
        self.market_check_loop.cancel()
        self.distribute_dividends.cancel()
        if not self.market_closed:
            self.bot.loop.create_task(self.market_close())

    @tasks.loop(minutes=5)
    async def market_check_loop(self):
        tz = pytz.timezone("US/Pacific")
        now = datetime.now(tz)

        if now.hour < 9 or now.hour >= 17:
            if not self.market_closed:
                await self.market_close()
        else:
            if self.market_closed:
                await self.market_open()
    
    async def market_close(self, forceful: bool = False, index_drop_amount: int = 0):
        """Close the market by canceling update tasks and sending a message."""
        channel_id = self.data.get("update_channel_id")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
        else:
            channel = None

        display_message = "The market has closed for the day."
        if forceful:
            display_message += f" The market dropped by {index_drop_amount} points, so investors closed it early."
        # Cancel your update tasks.
        self.update_stock_prices.cancel()
        self.update_indices_and_investor_modifier.cancel()
        self.stock_updates_loop.cancel()
        self.market_closed = True
        
        if channel:
            await channel.send(display_message)
    
    async def market_open(self):
        """Reopen the market by restarting update tasks and notifying the channel."""
        self.update_stock_prices.start()
        self.update_indices_and_investor_modifier.start()
        self.stock_updates_loop.start()
        channel_id = self.data.get("update_channel_id")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send("The market has reopened for another day of trading!")
        self.market_closed = False

    
    @tasks.loop(minutes=5)
    async def update_stock_prices(self):
        """
        Randomly update stock prices every 5 minutes.
        Adjust the price volatility based on liquidity: 
        if daily_volume is lower than a baseline, price swings are larger.
        """
        baseline_volume = 100000  # Define a baseline volume.

        scaled_modifier = self.investor_modifier * (5/30)
        
        for company in self.data["companies"].values():
            # Get the company's liquidity; default to baseline if not provided.
            volume = company.get("daily_volume", baseline_volume)
            # Compute a volatility factor: if volume is lower than baseline, factor > 1 (more volatility).
            # For example, factor = baseline_volume / volume.
            volatility_factor = baseline_volume / volume  
            # Alternatively, you might clamp this factor between, say, 0.5 and 2.
            volatility_factor = max(0.5, min(2, volatility_factor))
            
            change_percent = random.uniform(-0.05, 0.05) * volatility_factor
            old_price = company["price"]
            new_price = max(1.0, old_price * (1 + change_percent + scaled_modifier))
            company["price"] = new_price  # Keep as float internally.
            company.setdefault("price_history", []).append(new_price)
            if len(company["price_history"]) > HISTORY_LIMIT:
                company["price_history"].pop(0)
        save_data(self.data)



    @tasks.loop(hours=24)
    async def distribute_dividends(self):
        for symbol, company in self.data["companies"].items():
            dividend_yield = company.get("dividend_yield", 0)
            if company["price"] < company.get("bankruptcy_threshold", 50):
                dividend_yield = 0
            dividend_per_share = company["price"] * dividend_yield
            for user_id, portfolio in self.data["portfolios"].items():
                shares = portfolio.get(symbol, 0)
                if shares > 0:
                    total_dividend = dividend_per_share * shares
                    await bank.deposit_credits(user_id, int(total_dividend))
        save_data(self.data)
    
    @tasks.loop(minutes=30)
    async def update_indices_and_investor_modifier(self):
        """
        Update indices every 30 minutes with low volatility,
        then calculate an average change to adjust the investor modifier.
        Incorporate any market injection and decay it over time.
        Also apply an index modifier that can be updated by whole-market events.
        """
        # Update each index with lower volatility (e.g., ±1%), factoring in the index_modifier.
        for index in self.data["indices"].values():
            old_value = index["value"]
            change = random.uniform(-0.01, 0.01)  # ±1%
            # Apply both the random change and the index_modifier.
            new_value = round(old_value * (1 + change + self.index_modifier), 1)
            index["value"] = new_value
            index.setdefault("history", []).append(new_value)
            if len(index["history"]) > 20:
                index["history"].pop(0)
        
        # Calculate the average percentage change for each index.
        total_change = 0
        count = 0
        for index in self.data["indices"].values():
            history = index["history"]
            if len(history) >= 2:
                change_pct = (history[-1] - history[-2]) / history[-2]
                total_change += change_pct
                count += 1
        avg_change = total_change / count if count > 0 else 0

        # Clamp the base modifier to a reasonable range (e.g., ±3%).
        base_modifier = max(-0.03, min(0.03, avg_change))
        # Combine with market injection for investor modifier.
        self.investor_modifier = base_modifier + self.market_injection
        self.market_injection *= 0.90
        if abs(self.market_injection) < 0.005:
            self.market_injection = 0.0

        # Decay the index modifier as well (e.g., 10% decay per cycle).
        self.index_modifier *= 0.90
        if abs(self.index_modifier) < 0.005:
            self.index_modifier = 0.0

        save_data(self.data)

    
    @tasks.loop(hours=1)
    async def stock_updates_loop(self):
        """
        Every hour, post an update in the designated channel with current index values,
        along with a chance for a news event.
        The event can be market-wide, sector-wide, or corporation-specific.
        """
        channel_id = self.data.get("update_channel_id")
        if not channel_id:
            return  # No update channel set.
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        update_message = "**Hourly Market Update:**\n"
        for index_name, index in self.data.get("indices", {}).items():
            current_value = index.get("value", 0)
            history = index.get("history", [])
            if len(history) >= 2 and history[-2] != 0:
                percent_change = ((history[-1] - history[-2]) / history[-2]) * 100
                update_message += f"{index_name}: {current_value:.1f} ({percent_change:+.2f}%)\n"
            else:
                update_message += f"{index_name}: {current_value:.1f}\n"
        
        # Determine if a news event occurs (33% chance)
        if random.randint(0, 100) < 33:
            # Decide which tier: let's use tier probabilities:
            tier_roll = random.random()  # between 0 and 1.
            if tier_roll < 0.3:
                # Market-wide event (30% chance of 33%)
                event = random.choice(WHOLE_MARKET_EVENTS)
                update_message += "\n**Market News:**\n" + event["message"]
                self.market_injection += event["modifier"]
                self.index_modifier += event["modifier"]
            elif tier_roll < 0.6:
                # Sector-wide event (30% chance of 33%)
                event = random.choice(SECTOR_EVENTS)
                update_message += "\n**Sector News:**\n" + event["message"]
                # Apply modifier to companies in the affected sectors.
                for company in self.data["companies"].values():
                    if company.get("category") in event["affected_sectors"]:
                        company["price"] = max(1.0, company["price"] * (1 + event["modifier"]))
                        company.setdefault("price_history", []).append(company["price"])
            else:
                # Corporation-specific event (40% chance of 33%)
                company_symbol = random.choice(list(self.data["companies"].keys()))
                event = random.choice(INDIVIDUAL_EVENTS)
                event_message = event["message"].format(affected_company=company_symbol)
                update_message += "\n**Corporate News:**\n" + event_message
                company = self.data["companies"][company_symbol]
                company["price"] = max(1.0, company["price"] * (1 + event["modifier"]))
                company.setdefault("price_history", []).append(company["price"])
        
        await channel.send(update_message)
        save_data(self.data)




    @commands.hybrid_command(name="setupdatechannel", with_app_command=True, description="Set the channel for hourly market updates (admin only).")
    @commands.admin_or_permissions(administrator=True)
    async def setupdatechannel(self, ctx: commands.Context, channel: discord.TextChannel):
        self.data["update_channel_id"] = channel.id
        save_data(self.data)
        await ctx.send(f"Stock market update channel set to {channel.mention}.")


    
    @commands.hybrid_command(name="stockstatus", with_app_command=True, description="View current stock prices and your portfolio.")
    async def stockstatus(self, ctx: commands.Context):
        message = "**Current Stock Prices:**\n"
        for symbol, company in self.data["companies"].items():
            price = company['price']
            # If available, use total_shares to compute market cap; otherwise default to 1.
            total_shares = company.get("total_shares", 1)
            market_cap = price * total_shares
            message += f"{company['name']} ({symbol}): ${price:.2f} | Market Cap: {humanize.intcomma(int(market_cap))} credits\n"
        
        user_id = str(ctx.author.id)
        portfolio = self.data["portfolios"].get(user_id, {})
        if portfolio:
            message += "\n**Your Portfolio:**\n"
            total_portfolio_value = 0
            for symbol, shares in portfolio.items():
                if symbol in self.data["companies"]:
                    company = self.data["companies"][symbol]
                    price = company["price"]
                    value = shares * price
                    total_portfolio_value += value
                    message += f"{symbol}: {shares} shares @ ${price:.2f} = {value:.2f} credits\n"
            message += f"\nTotal Portfolio Value: {total_portfolio_value:.2f} credits"
        else:
            message += "\nYou currently do not own any shares."
        await ctx.send(message)
    
    @commands.hybrid_command(name="indexstatus", with_app_command=True, description="View current market indices.")
    async def indexstatus(self, ctx: commands.Context):
        message = "**Market Indices:**\n"
        indices = self.data.get("indices", {})
        if indices:
            for index_name, index in indices.items():
                value = index.get("value", 0)
                message += f"{index_name}: {value}\n"
        else:
            message += "No indices available."
        await ctx.send(message)
    
    @commands.hybrid_command(name="forcesellall", with_app_command=True, description="Force sell all shares from a user's portfolio (admin only).")
    @commands.admin_or_permissions(administrator=True)
    async def forcesellall(self, ctx: commands.Context, target: discord.Member):
        """
        Force sells all shares from the target user's portfolio.
        Sold shares are removed from the user's portfolio (and not re-added to available_shares),
        and credits are deposited based on current share prices.
        """
        user_id = str(target.id)
        if user_id not in self.data["portfolios"] or not self.data["portfolios"][user_id]:
            await ctx.send(f"{target.mention} does not have any shares to sell.")
            return

        total_credits = 0
        details = []
        # Iterate over each company in the user's portfolio.
        for symbol, shares in self.data["portfolios"][user_id].items():
            if symbol not in self.data["companies"]:
                continue
            company = self.data["companies"][symbol]
            sale_value = company["price"] * shares
            total_credits += sale_value
            details.append(f"{shares} shares of {company['name']} at ${company['price']:.2f} each for ${sale_value:.2f} credits")
            # Note: We do not add the shares back to company["available_shares"].
        
        # Remove the user's entire portfolio.
        self.data["portfolios"][user_id] = {}
        save_data(self.data)
        await bank.deposit_credits(target, int(total_credits))
        
        details_text = "\n".join(details)
        await ctx.send(f"Force sold all shares from {target.mention}:\n{details_text}\nTotal credits received: ${total_credits:.2f}")

    
    @commands.hybrid_command(name="inject_market", with_app_command=True, description="Inject a boost into the overall market indices (admin only).")
    @commands.admin_or_permissions(administrator=True)
    async def inject_market(self, ctx: commands.Context, injection: float):
        """
        Inject money into the overall market.
        The injection is given as a decimal percentage (e.g., 0.01 for a 1% boost).
        This temporarily increases the investor modifier.
        """
        self.market_injection += injection
        await ctx.send(f"Market injection increased by {injection:.2%}. Current market injection: {self.market_injection:.2%}")


    
    @commands.hybrid_command(name="stockbuy", with_app_command=True, description="Buy shares in a company.")
    async def stockbuy(self, ctx: commands.Context, symbol: str, shares: int = 1):
        if ctx.interaction:
            await ctx.defer()
        symbol = symbol.strip()
        if symbol not in self.data["companies"]:
            await ctx.send("That company does not exist.")
            return
        
        company = self.data["companies"][symbol]
        if shares > company.get("available_shares", 0):
            await ctx.send("Not enough shares available for purchase.")
            return
        total_cost = company["price"] * shares
        total_cost = int(total_cost)
        if not await bank.can_spend(ctx.author, total_cost):
            await ctx.send("You don't have enough credits to buy these shares.")
            return
        
        await bank.withdraw_credits(ctx.author, total_cost)
        user_id = str(ctx.author.id)
        self.data["portfolios"].setdefault(user_id, {})
        self.data["portfolios"][user_id][symbol] = self.data["portfolios"][user_id].get(symbol, 0) + shares
        company["available_shares"] -= shares
        save_data(self.data)
        price = company['price']
        await ctx.send(f"You bought {shares} shares of {company['name']} at ${price:.2f} each for {total_cost} credits.")

    @commands.hybrid_command(name="stocksell", with_app_command=True, description="Sell shares in a company.")
    async def stocksell(self, ctx: commands.Context, symbol: str, shares: int):
        if ctx.interaction:
            await ctx.defer()
        symbol = symbol.strip()
        user_id = str(ctx.author.id)
        if user_id not in self.data["portfolios"] or symbol not in self.data["portfolios"][user_id] or self.data["portfolios"][user_id][symbol] < shares:
            await ctx.send("You don't have enough shares to sell.")
            return
        
        company = self.data["companies"][symbol]
        total_value = company["price"] * shares
        total_value = int(total_value)
        self.data["portfolios"][user_id][symbol] -= shares
        if self.data["portfolios"][user_id][symbol] == 0:
            del self.data["portfolios"][user_id][symbol]
        company["available_shares"] += shares
        save_data(self.data)
        await bank.deposit_credits(ctx.author, total_value)
        price = company['price']
        await ctx.send(f"You sold {shares} shares of {company['name']} at ${price:.2f} each for {total_value} credits.")
    
    @commands.hybrid_command(name="stockgraph", with_app_command=True, description="Display a line graph of a stock's price history.")
    async def stockgraph(self, ctx: commands.Context, symbol: str):
        symbol = symbol.strip()
        if symbol not in self.data["companies"]:
            await ctx.send("That company does not exist.")
            return
        
        company = self.data["companies"][symbol]
        price_history = company.get("price_history", [company["price"]])

        times = list(range(len(price_history)))

        plt.figure(figsize=(8,4))
        plt.style.use('dark_background')
        plt.plot(times, price_history, linestyle='-')
        plt.title(f"{company['name']} Price History")
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        file = discord.File(fp=buf, filename="stockgraph.png")

        embed = discord.Embed(
            title=f"{company['name']} Stock Price History",
            description="Price history over the recent period.",
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://stockgraph.png")
        await ctx.send(embed=embed, file=file)
    
    @commands.hybrid_command(name="indexgraph", with_app_command=True, description="Display a line graph of a market index's history.")
    async def indexgraph(self, ctx: commands.Context, index_name: str):
        """
        Display the history of a market index as a line graph.
        Example: /indexgraph "Dough Jones Index"
        """
        index_name = index_name.strip()
        indices = self.data.get("indices", {})
        if index_name not in indices:
            await ctx.send("That index does not exist. Please check the index name.")
            return

        index = indices[index_name]
        history = index.get("history", [])
        if not history:
            await ctx.send("No history data available for this index.")
            return

        # Generate a line graph for the index history.
        times = list(range(len(history)))
        plt.figure(figsize=(8, 4))
        plt.style.use('dark_background')
        plt.plot(times, history, linestyle='-')
        plt.title(f"{index_name} History")
        plt.xlabel("Time")
        plt.ylabel("Index Value")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        file = discord.File(fp=buf, filename="indexgraph.png")

        embed = discord.Embed(
            title=f"{index_name} History",
            description="Index history over the recent period.",
            color=discord.Color.blue()
        )
        embed.set_image(url="attachment://indexgraph.png")
        await ctx.send(embed=embed, file=file)
    
