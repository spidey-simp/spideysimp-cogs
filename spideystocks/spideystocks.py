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

DATA_FILE = "market_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
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
        self.update_stock_prices.start()
        self.distribute_dividends.start()
    
    def cog_unload(self):
        self.update_stock_prices.cancel()
        self.distribute_dividends.cancel()
    
    @tasks.loop(minutes=5)
    async def update_stock_prices(self):
        """Randomly update stock prices every 5 minutes."""
        for company in self.data["companies"].values():
            change_percent = random.uniform(-0.05, 0.05)
            old_price = company["price"]
            new_price = max(1, int(old_price * (1 + change_percent)))
            company["price"] = new_price
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
    
    @commands.hybrid_command(name="stockstatus", with_app_command=True, description="View current stock prices and your portfolio.")
    async def stockstatus(self, ctx: commands.Context):
        message = "**Current Stock Prices:**\n"
        for symbol, company in self.data["companies"].items():
            message +=f"{company['name']} ({symbol}): ${company['price']}\n"
        user_id = str(ctx.author.id)
        portfolio = self.data["portfolios"].get(user_id, {})
        if portfolio:
            message += "\n**Your Portfolio:**\n"
            for symbol, shares in portfolio.items():
                message += f"{symbol}: {shares} shares\n"
        else:
            message += "\nYou currently do not own any shares."
        await ctx.send(message)
    
    @commands.hybrid_command(name="stockbuy", with_app_command=True, description="Buy shares in a company.")
    async def stockbuy(self, ctx: commands.Context, symbol: str, shares: int = 1):
        symbol = symbol.strip()
        if symbol not in self.data["companies"]:
            await ctx.send("That company does not exist.")
            return
        
        company = self.data["companies"][symbol]
        total_cost = company["price"] * shares
        if not await bank.can_spend(ctx.author, total_cost):
            await ctx.send("You don't have enough credits to buy these shares.")
            return
        
        await bank.withdraw_credits(ctx.author, total_cost)
        user_id = str(ctx.author.id)
        self.data["porfolios"].setdefault(user_id, {})
        self.data["portfolios"][user_id][symbol] = self.data[user_id].get(symbol, 0) + shares
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
        self.data["portfolios"][user_id][symbol] -= shares
        if self.data["portfolios"][user_id][symbol] == 0:
            del self.data["portfolios"][user_id][symbol]
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
        plt.plot(times, price_history, marker='o', linestyle='-', color='blue')
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