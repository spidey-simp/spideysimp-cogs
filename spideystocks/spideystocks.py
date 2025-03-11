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

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "market_data.json")

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
                    "price_history": [120]
                },
                "NascarCorp": {
                    "price": 90,
                    "name": "Nascar Corp.",
                    "dividend_yield": 0.02,
                    "bankruptcy_threshold": 45,
                    "price_history": [90]
                },
                "MM500": {
                    "price": 50,
                    "name": "M&M 500 Ltd.",
                    "dividend_yield": 0.04,
                    "bankruptcy_threshold": 25,
                    "price_history": [50]
                },
                "SpideySells": {
                    "price": 110,
                    "name": "SpideySells Inc.",
                    "dividend_yield": 0.015,
                    "bankruptcy_threshold": 55,
                    "price_history": [110]
                },
                "BananaRepublic": {
                    "price": 70,
                    "name": "Banana Republic Co.",
                    "dividend_yield": 0.025,
                    "bankruptcy_threshold": 35,
                    "price_history": [70]
                }
            },
            "portfolios": {}
        }
    if "indices" not in data:
        data["indices"] = {
            "Nascar Index": {"value": 1000, "history": [1000]},
            "M&M Index": {"value": 800, "history": [800]}
        }
    save_data(data)
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


class SpideyStocks(commands.Cog):
    """A simple stock market simulation cog."""

    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()
        self.investor_modifier = 0.0
        self.update_stock_prices.start()
        self.distribute_dividends.start()
        self.update_indices_and_investor_modifier.start()
    
    def cog_unload(self):
        self.update_stock_prices.cancel()
        self.distribute_dividends.cancel()
        self.update_indices_and_investor_modifier.cancel()
    
    @tasks.loop(minutes=5)
    async def update_stock_prices(self):
        """Randomly update stock prices every 5 minutes using float arithmetic."""
        for company in self.data["companies"].values():
            change_percent = random.uniform(-0.05, 0.05)
            old_price = company["price"]
            new_price = max(1.0, old_price * (1 + change_percent + self.investor_modifier))
            company["price"] = new_price  # Keep as float internally
            company.setdefault("price_history", []).append(new_price)
            if len(company["price_history"]) > 20:
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
        """
        # Update each index with lower volatility (e.g., ±1%)
        for index in self.data["indices"].values():
            old_value = index["value"]
            change = random.uniform(-0.01, 0.01)  # ±1%
            new_value = max(1, int(old_value * (1 + change)))
            index["value"] = new_value
            index.setdefault("history", []).append(new_value)
            if len(index["history"]) > 20:
                index["history"].pop(0)
        
        # Calculate the average percentage change from the last two recorded values for each index.
        total_change = 0
        count = 0
        for index in self.data["indices"].values():
            history = index["history"]
            if len(history) >= 2:
                change_pct = (history[-1] - history[-2]) / history[-2]
                total_change += change_pct
                count += 1
        avg_change = total_change / count if count > 0 else 0
        
        # Clamp the investor modifier to a reasonable range, e.g. ±3%
        self.investor_modifier = max(-0.03, min(0.03, avg_change))
        save_data(self.data)
    
    @commands.hybrid_command(name="stockstatus", with_app_command=True, description="View current stock prices and your portfolio.")
    async def stockstatus(self, ctx: commands.Context):
        message = "**Current Stock Prices:**\n"
        for symbol, company in self.data["companies"].items():
            price = company['price']
            # If available, use total_shares to compute market cap; otherwise default to 1.
            total_shares = company.get("total_shares", 1)
            market_cap = price * total_shares
            message += f"{company['name']} ({symbol}): ${price:.2f} | Market Cap: {humanize.intcomma(market_cap)} credits\n"
        
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

    
    @commands.hybrid_command(name="stockbuy", with_app_command=True, description="Buy shares in a company.")
    async def stockbuy(self, ctx: commands.Context, symbol: str, shares: int = 1):
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
        await ctx.send(f"You bought {shares} shares of {company['name']} at ${company['price']} each for {total_cost} credits.")

    @commands.hybrid_command(name="stocksell", with_app_command=True, description="Sell shares in a company.")
    async def stocksell(self, ctx: commands.Context, symbol: str, shares: int):
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
        await ctx.send(f"You sold {shares} shares of {company['name']} at ${company['price']} each for {total_value} credits.")
    
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
