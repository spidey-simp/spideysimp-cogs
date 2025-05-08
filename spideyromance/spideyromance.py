import random
import discord
from redbot.core import commands
from discord import app_commands


class SpideyRomance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.restraining_order_dict = {}

    
    @commands.command(name="cuddle")
    async def cuddle(self, ctx: commands.Context, *, target: str=None):
        if not target:
            await ctx.send("You can't cuddle no one smh.")
            return
        
        member = None
        if ctx.message.mentions:
            member = discord.utils.find(lambda m: m.name.lower() == target.lower(), ctx.guild.members)
        
        if member:
            target_display = member.mention
        else:
            target_display = target

        if member and str(member.id) in self.restraining_order_dict:
            if str(ctx.author.id) in self.restraining_order_dict[str(member.id)]:
                await ctx.send(f"{target_display} took out a restraining order on you. No cuddles for you.")
                return

        msg_list_use = []
        bonus_msg = []
        
        if member and member.id == ctx.author.id:
            await ctx.send("You can't cuddle yourself sillyhead.")
            return
        
        if member and member.id == self.bot.user.id:
            randchance = random.random()
            if randchance < .1:
                msg_list_use = [f"{ctx.author.mention} and {self.bot.user.mention} are snuggling. How sweet! ❤️"]
                bonus_msg = ["It is a little metallic though . . .  🤖"]
            elif randchance < .5:
                msg_list_use = [f"{self.bot.user.mention} isn't really looking to cuddle with the likes of you, {ctx.author.mention}."]
            else:
                msg_list_use = [f"{self.bot.user.mention} just filed a restraining order against {ctx.author.mention}."]
                self.restraining_order_dict.setdefault(str(self.bot.user.id), []).append(str(ctx.author.id))
        else:
            randchance = random.random()
            if randchance > .95:
                msg_list_use = [f"{target_display} is taking out a restraining order"]

        message = random.choice(msg_list_use)
        await ctx.send(message)

        if bonus_msg != []:
            await ctx.defer(1)
            bonus = random.choice(bonus_msg)
            await ctx.send(bonus)

