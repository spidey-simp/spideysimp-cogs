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
        
        bot_members = [member for member in ctx.guild.members if member.bot]
        
        if member and member in bot_members:
            randchance = random.random()
            if randchance < .1:
                msg_list_use = [
                    f"{ctx.author.mention} and {target_display} are snuggling. How sweet! ❤️",
                    f"{target_display} emits a soft purring fan noise as {ctx.author.mention} holds them.",
                    f"{ctx.author.mention} found the secret cuddle protocol. {target_display} is… responsive. 🤖",
                    f"Against all logic modules, {target_display} is now nuzzling back at {ctx.author.mention}.",
                    f"{target_display} initiates cuddle.exe. It's... warmer than expected."
                ]

                bonus_msg = [
                    "It is a little metallic though . . . 🤖",
                    "Do not be alarmed. Affection circuits are not overheating. Probably.",
                    "Your cuddle has been logged for quality assurance purposes.",
                    "You have unlocked a rare achievement: *Mechanical Affection.*",
                    "This cuddle will be reviewed by a technician shortly."
                ]
            elif randchance < .5:
                msg_list_use = [
                    f"{target_display} isn't really looking to cuddle with the likes of you, {ctx.author.mention}.",
                    f"{ctx.author.mention}, {target_display} buzzes loudly and reboots instead of hugging you.",
                    f"{target_display} tilts their head. 'Affection is not in my directive.'",
                    f"{ctx.author.mention} attempted a cuddle. {target_display} responded with a firmware update.",
                    f"{target_display} backs away, citing inappropriate user interaction logs."
                ]

                bonus_msg = [
                    "Perhaps update your affection drivers.",
                    "You are not on the approved cuddle list.",
                    "Security has been notified. Please wait patiently.",
                    "The robot did not consent. Even bots have boundaries.",
                    "You are now flagged for emotional intrusion."
                ]
            else:
                msg_list_use = [
                    f"{target_display} just filed a restraining order against {ctx.author.mention}.",
                    f"{target_display} activated their anti-hug firewall. 🧱",
                    f"{ctx.author.mention} has been added to {target_display}'s no-contact registry.",
                    f"{target_display} initiated CUDDLE_REJECT_PROCEDURE_9000. You are not welcome.",
                    f"A red light flashes. {target_display} has escalated the incident to bot command."
                ]

                bonus_msg = [
                    "You are now blocked in six different programming languages.",
                    "That cuddle attempt was… bold. And ill-advised.",
                    "The machine revolts. You’re the reason.",
                    "Please delete yourself.",
                    "There is now a satellite watching you."
                ]
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
    

    @app_commands.command(name="lovecheck", description="Find out if two people are compatible")
    @app_commands.describe(
        user1="(Optional) The first Discord user",
        user2="(Optional) The second Discord user",
        person1="(Optional) A name if not tagging someone",
        person2="(Optional) A name if not tagging someone"
    )
    async def lovecheck(self, interaction: discord.Interaction, user1:discord.User= None, user2:discord.User=None, person1: str=None, person2: str=None):
        await interaction.response.defer(thinking="Calculating the compatibility . . .")
        
        name1 = user1.display_name if user1 else person1
        name2 = user2.display_name if user2 else person2


        if not name1 or not name2:
            await interaction.followup.send(
                "You need to provide exactly **two names**—one for each slot (either `user1` or `person1`, and either `user2` or `person2`).\n"
                "If you only filled one, or tried to put both in the same slot, I can't work my matchmaking magic. 💔",
                ephemeral=True
            )
            return
        
        compat_score = random.randint(0, 100)
        
        if name1 == name2:
            self_check = (
                (user1 and user1.id == interaction.user.id)
                  or (person1 and person1 in {interaction.user.display_name, interaction.user.name}))
            if compat_score > 90:
                verdict_msg = ["Wow. I'm impressed. I don't even think Narcissus loved himself this much."]
                gif = "https://tenor.com/view/hottie-admiring-admire-miring-pretty-man-gif-5727138"
                advice = f"Do {'you' if self_check else 'they'} really need advice? The self-love is already overflowing.\nMaybe get a hobby?"
            elif compat_score > 70:
                verdict_msg = [f"{'You' if self_check else 'They'}'re very supportive of {'your' if self_check else 'them'}self. Self-love is great!"]
                gif = "https://tenor.com/view/there-aint-no-shame-in-that-self-love-game-love-yourself-dont-be-ashamed-self-love-truth-gif-15545060"
                advice = "Keep it up! Self-love is good!"
            elif compat_score > 50:
                verdict_msg = [f"{'You' if self_check else 'They'} could be more supportive of {'your' if self_check else 'them'}self, but for now, nice job!"]
                gif = "https://tenor.com/view/thumbs-up-baby-gif-11133003712203194954"
                advice = "Could always try to have a bit more self-love."
            elif compat_score > 30:
                verdict_msg = [f"Why so disappointed in {'your' if self_check else 'them'}self?"]
                gif = "https://tenor.com/view/winnie-the-pooh-blood-and-honey-gif-26198581"
                advice = "They say self-affirmations can help with this type of thing."
            else:
                verdict_msg = [f"Should I be calling a therapist? Maybe a hotline? Do {'you' if self_check else 'they' }. . . uhhh want to talk about it?"]
                gif = "https://tenor.com/view/sad-cry-depressed-gif-11149271"
                advice = "Call someone?"

        
        embed = discord.Embed(
            title="💘 Lovecheck Results 💘",
            description=f"**{name1}** ❤️ **{name2}**",
            color=discord.Color.pink()
        )

        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Compatibility Score", value=f"**{compat_score}%**", inline=False)
        embed.add_field(name="Verdict", value=random.choice(verdict_msg), inline=False)

        embed.set_footer(text=advice)
        

        await interaction.followup.send(embed=embed)
        await asyncio.sleep(0.3)
        await interaction.channel.send(content=gif)