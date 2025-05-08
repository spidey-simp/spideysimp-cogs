import random
import discord
import asyncio
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
            member = ctx.message.mentions[0]
        else:
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
                msg_list_use = [
                    f"{target_display} is taking out a restraining order on {ctx.author.display_name}. 🚔",
                    f"Your cuddle attempt triggered a legal response. {target_display} is not amused.",
                    f"{ctx.author.mention}, you've been formally banned from the Snuggle Zone™.",
                    f"{target_display} just lawyered up. No more hugs for you.",
                    f"Cease and desist. {target_display} wants 500 feet of space and a security detail."
                ]
                if member:
                    self.restraining_order_dict.setdefault(str(member.id), []).append(str(ctx.author.id))
                bonus_msg = [
                    "Damn that’s tough. 🫢",
                    "You cuddled so hard you broke the law.",
                    "Not everyone appreciates unprompted affection, champ.",
                    "Your cuddle license has been revoked.",
                    "Next time, try a wave."
                ]

            elif randchance > .8:
                msg_list_use = [
                    f"{target_display} doesn't seem very interested in cuddling with you, {ctx.author.mention}.",
                    f"{target_display} side-eyed the cuddle attempt and walked away. 😬",
                    f"{ctx.author.mention} tried to cuddle {target_display}, but it’s giving 'restraining vibe' energy.",
                    f"{target_display} gave a thumbs up… and then ghosted.",
                    f"{ctx.author.mention} misread the situation. Hug denied. 💔"
                ]
                bonus_msg = [
                    "Maybe buy them a drink first. 🍷",
                    "Recalibrating cuddle radar… 🛰️",
                    "Tough crowd, huh?",
                    "Rejection builds character. Allegedly.",
                    "You miss 100% of the cuddles you don't shoot for—and 100% of the ones you do."
                ]

            else:
                msg_list_use = [
                    f"{ctx.author.mention} and {target_display} are snuggling. How sweet! ❤️",
                    f"{ctx.author.mention} just pulled {target_display} into the warmest cuddle imaginable. ☁️",
                    f"{ctx.author.mention} and {target_display} are now contractually obligated to be cozy. 📜🤗",
                    f"A certified snuggle session has begun between {ctx.author.mention} and {target_display}. 🧸",
                    f"{ctx.author.mention} is absolutely swaddling {target_display} in affection. Someone get a blanket!"
                ]
                bonus_msg =[
                    "Happy cuddles! 🫶",
                    "Wholesome levels rising dangerously. ☢️",
                    "May this cuddle never end. (It will, of course.)",
                    "That was so soft it registered on the Mohs scale.",
                    "And just like that, serotonin."
                ]


        message = random.choice(msg_list_use)
        await ctx.send(message)

        if bonus_msg != []:
            await asyncio.sleep(1)
            bonus = random.choice(bonus_msg)
            await ctx.send(bonus)

