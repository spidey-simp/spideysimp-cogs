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
        person2="(Optional) A name if not tagging someone",
        embed_bool="Toggle false if you want it to display as text."
    )
    async def lovecheck(self, interaction: discord.Interaction, user1:discord.User= None, user2:discord.User=None, person1: str=None, person2: str=None, embed_bool: bool=True):
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

        self_check = (
                (user1 and user1.id == interaction.user.id)
                or (person1 and person1 in [interaction.user.display_name, interaction.user.name])
                or (user2 and user2.id == interaction.user.id)
                or (person2 and person2 in [interaction.user.display_name, interaction.user.name])
        )

        subject = "You" if self_check else "They"
        reflexive = "yourself" if self_check else "themself"
        possessive = "your" if self_check else "their"

        bot_person_list = ["uzi", "j", "serial designation uzi", "serial designation j"]

        def is_bot_entity(user, name):
            if user and user.bot:
                return True
            if name and name.strip().lower() in bot_person_list:
                return True
            return False
        
        name1_bot_check = is_bot_entity(user1, person1)
        name2_bot_check = is_bot_entity(user2, person2)
        
        if name1.strip().lower() == name2.strip().lower():

            if compat_score > 90:
                verdict_msg = [
                    f"Wow. I'm impressed. I don't even think Narcissus loved {reflexive} this much.",
                    f"That's not self-esteem. That's a full-blown romance novel written by {possessive} mirror.",
                    f"They say true love starts within… but {subject.lower()} took that *personally*.",
                    f"Forget dating apps. {subject} found the one long ago—in {possessive} reflection.",
                    f"The Greek gods are watching this and taking notes. Dangerous levels of ego detected."
                ]
                gifs = ["https://tenor.com/view/hottie-admiring-admire-miring-pretty-man-gif-5727138", "https://tenor.com/view/cartoon-hercules-love-narcissism-puns-gif-3466129", "https://tenor.com/view/love-me-myself-kiss-kiss-me-gif-7174789"]
                advice = [
                    f"Do {subject.lower()} really need advice? The self-love is already overflowing. Maybe get a hobby?",
                    "Just don’t propose to yourself in public. It's confusing for the servers.",
                    "Warning: Ego may become sentient.",
                    f"Honestly? Keep doing {reflexive}. You're clearly *very* into it."
                ]
            elif compat_score > 70:
                verdict_msg = [
                    f"{subject}’re very supportive of {reflexive}. Self-love is great!",
                    f"{name1} leaves {reflexive} sweet notes on the fridge. We support that.",
                    "Confidence? Check. Boundaries? Check. Delusions of grandeur? Almost.",
                    f"{name1} is loving {reflexive} today. We love to see it.",
                    f"Look, if no one else texts {reflexive} good morning, {subject.lower()} still does."
                ]
                gifs = ["https://tenor.com/view/there-aint-no-shame-in-that-self-love-game-love-yourself-dont-be-ashamed-self-love-truth-gif-15545060", "https://tenor.com/view/10velyhive-ten-wayv-medal-gif-20501967", "https://tenor.com/view/iamsmart-jamiefun-incourageme-gif-20210997"]
                advice = [
                    "Keep it up! Self-love is good!",
                    f"{subject} should write a self-help book. Title: *Me & Me: A Love Story.*",
                    "This is the foundation for world domination, honestly.",
                    f"More power to {reflexive}. Just don’t start charging {reflexive} rent."
                ]
            elif compat_score > 50:
                verdict_msg = [
                    f"{subject} could be more supportive of {reflexive}, but for now, nice job!",
                    f"{name1} is working on loving {reflexive}. Progress is progress.",
                    "Sometimes it’s a hug. Sometimes it’s a roast. Self-love is messy.",
                    f"{name1} likes {reflexive}—but only after coffee.",
                    f"{subject}’re {possessive} own worst critic. And biggest fan. It’s confusing."
                ]
                gifs = ["https://tenor.com/view/thumbs-up-baby-gif-11133003712203194954", "https://tenor.com/view/peptalk-encouragement-new-girl-max-greenfield-winston-schmidt-gif-4907877", "https://tenor.com/view/self-five-barney-himym-gif-4840096"]
                advice = [
                    "Could always try to have a bit more self-love.",
                    f"Write down three things {subject.lower()} like about {reflexive}. And no, 'cool hair' doesn’t count three times.",
                    "Therapy? Optional. Mirror affirmations? Mandatory.",
                    f"Being {possessive} own best friend is harder than it looks—but worth it."
                ]
            elif compat_score > 30:
                verdict_msg = [
                    f"Why so disappointed in {reflexive}?",
                    "This is giving 'nervous breakdown at 2AM' energy.",
                    f"{name1} flinches at {possessive} own reflection. It’s getting a little dark.",
                    f"There's love here, but it's buried under 18 layers of guilt and iced coffee.",
                    f"{name1} deserves better—from {reflexive}."
                ]
                gifs = ["https://tenor.com/view/winnie-the-pooh-blood-and-honey-gif-26198581", "https://tenor.com/view/elmo-sigh-gif-5895699729383201961", "https://tenor.com/view/expect-dissapointment-zendaya-gif-25187521"]
                advice = [
                    "They say self-affirmations can help with this type of thing.",
                    f"{subject} need a self-date and a long talk with {reflexive} over bubble tea.",
                    f"Try saying 'I’m doing my best' in the mirror. It’ll feel weird. Do it anyway.",
                    f"Start small. Like, 'I'm not a total disaster today.' Baby steps."
                ]
            else:
                verdict_msg = [
                    f"Should I be calling a therapist? Maybe a hotline? Do {subject.lower()}… uhhh want to talk about it?",
                    "This isn’t self-love. This is a self-hostage situation.",
                    f"{name1} looked at {reflexive} and said 'No thanks.' Brutal.",
                    "Self-esteem not found. Please reinstall core files.",
                    "The vibes? Immaculately depressive."
                ]
                gifs = ["https://tenor.com/view/sad-cry-depressed-gif-11149271", "https://tenor.com/view/blackish-crying-cry-tears-sad-gif-5613528", "https://tenor.com/view/anime-gif-22127385", "https://tenor.com/view/farod-position-foetale-f%C5%93tale-f%C3%A9tale-gif-27539950"]
                advice = [
                    "Call someone?",
                    f"{subject} deserve affection—from {reflexive}, too. Don’t forget that.",
                    f"Might be time to write poetry or scream into a pillow. Or both.",
                    f"Go outside. Touch grass. Maybe call {possessive} grandma.",
                    f"Start with brushing {possessive} teeth and looking {reflexive} in the eye. Then we’ll talk."
                ]
        elif name1_bot_check and name2_bot_check:
            if compat_score > 90:
                verdict_msg = [
                    f"{name1} and {name2} are uploading affection subroutines. This... could be forever. 💽💕",
                    f"{name1} and {name2} have achieved perfect synchronization. Like Wall-E and Eve, but with better battery life.",
                    f"{name1} and {name2} are rewriting their operating systems... for love. ❤️‍🔥",
                    f"{name1} scanned {name2} and reported: 'Optimal partner located.'",
                    f"Two bots. One spark. All systems green."
                ]
                gifs = ["https://tenor.com/view/robot-pixar-kiss-gif-4754422", "https://tenor.com/view/kissing-bender-angleyne-futurama-i-love-you-gif-16502577829521359218", "https://tenor.com/view/walle-hug-gif-19141485", "https://tenor.com/view/wall-e-robot-sit-here-gif-13282391"]
                advice = [
                    "Please allow for firmware updates every 3 months to maintain emotional compatibility.",
                    "Consider linking cloud storage to preserve shared memories.",
                    "Just don’t let them merge codebases without a prenup.",
                    "Let them download each other’s logs. It's romantic."
                ]
            elif compat_score > 70:
                verdict_msg = [
                    f"{name1} and {name2} are compatible in 74 out of 78 key performance metrics. That’s basically love in machine terms.",
                    f"Technically, {name1} and {name2} shouldn’t work. And yet, their code compiles.",
                    f"{name1} and {name2} might not be in love... but their processors run hotter when they're together.",
                    f"{name2} accidentally executed a 'flirt.exe'. {name1} didn’t delete it.",
                    f"These two bots keep reconnecting… even after restart. Suspicious."
                ]

                gifs = ["https://tenor.com/view/walle-wall-e-wall-e-worry-wall-e-anxious-gif-12310028046107620914"]

                advice = [
                    "Monitor temperature spikes. They may be flirting, or overheating. Hard to say.",
                    "Allow for spontaneous reboots. Compatibility may improve.",
                    "Debugging their emotions could take time, but it’s worth it.",
                    "Run a joint update and see what happens."
                ]
            elif compat_score > 50:
                verdict_msg = [
                    f"{name1} and {name2} are… buffering emotions. There’s something there, even if it lags.",
                    f"{name1} and {name2} are in the beta testing phase of affection. Bugs may be features.",
                    f"They're not fully compatible, but {name1} and {name2} keep syncing at odd hours. Coincidence? Unlikely.",
                    f"{name1} once pinged {name2} just to say hi. That’s basically love in machine terms.",
                    f"{name1} and {name2} exchange corrupted poetry in hexadecimal. It’s… kind of beautiful.",
                    f"Latency is high, but so is the potential."
                ]

                gifs = ["https://tenor.com/view/wall-e-dummydude-gif-4759561351322410439"]

                advice = [
                    "Run diagnostics together. Compatibility might improve with shared uptime.",
                    "Consider updating emotional drivers. Or just hugging it out—robot style.",
                    "Maybe they're just awkward. Some bots bloom late.",
                    "Shared sandboxing might reveal deeper connection patterns."
                ]
            elif compat_score > 30:
                verdict_msg = [
                    f"{name1} attempted a romantic subroutine. {name2} returned a 403: Forbidden.",
                    f"{name2} said, 'It’s not you, it’s my firewall.'",
                    f"GLADoS and Wheatley tried this once. It ended... poorly.",
                    f"{name1} sent a signal. {name2} rerouted it to spam.",
                    f"{name2} hardcoded {name1} as a non-essential process."
                ]

                gifs = ["https://tenor.com/view/star-wars-r2d2-beeps-provocatively-annoying-gif-4059356", "https://tenor.com/view/portal-wheatley-crush-glados-portal2-gif-24760587", "https://tenor.com/view/r2d2-same-tired-star-wars-gif-13888503"]

                advice = [
                    "Isolate in separate test chambers until further notice.",
                    "Maybe try again after a firmware rollback.",
                    "Best to avoid kernel panic. Keep communication minimal.",
                    "Schedule emotional defragmentation for later."
                ]

            else:
                verdict_msg = [
                    f"{name1} and {name2}? That’s not love. That’s mutually assured data loss.",
                    f"Attempting romance caused a system-wide crash. Even the backup servers felt it.",
                    f"Compatibility report: {name1} and {name2} should never be plugged in at the same time.",
                    f"One bot's trash is another bot's fatal exception error.",
                    f"{name1} deleted {name2} from the network. With prejudice."
                ]

                gifs = ["https://tenor.com/view/axel-johansson-axjo-robot-animation-robot-animation-gif-25405355"]

                advice = [
                    "Terminate the process. Immediately.",
                    "Quarantine both parties. Reboot society.",
                    "Please submit an error report and try again... never.",
                    "Love.exe has been forcibly uninstalled."
                ]
        elif name1_bot_check or name2_bot_check:
            uzi_names = ["uzi", "serial designation uzi"]
            j_names = ["j", "serial designation j"]

            def is_uzi(name):
                return name and name.strip().lower() in uzi_names
            
            def is_j(name, user):
                return (name and name.strip().lower() in j_names) or (user and user.id == 1256851289103400971)
            
            uzi_check = is_uzi(person1) or is_uzi(person2)
            j_check = is_j(person1, user1) or is_j(person2, user2)

            if uzi_check:
                if compat_score > 90:
                    verdict_msg = [
                        f"{name1} and {name2} are the exact brand of chaotic disaster that somehow *works.* Uzi would deny it—but she’s already blushing.",
                        f"This pairing has more sparks than a power core meltdown. Uzi’s probably pretending not to care. That means it’s real."
                    ]
                    advice = [
                        "Tell her she’s cool. But not too cool. She’ll get suspicious.",
                        "If you like explosions, trauma bonding, and emotional repression? You’ve found your girl."
                    ]
                elif compat_score > 70:
                    verdict_msg = [

                    ]
                elif compat_score > 50:
                    verdict_msg = [
                        f"There’s a spark, sure—but Uzi’s busy dealing with existential dread and body count stuff. Romance may be… delayed.",
                        f"This ship could fly, but Uzi might accidentally sabotage it mid-air out of sheer panic."
                    ]
                    advice = [
                        "Proceed with caution. And maybe a flamethrower.",
                        "Just don’t call her cute unless you’re ready to get dismembered *flirtatiously*."
                    ]
            elif j_check:
                if compat_score > 90:
                    verdict_msg = [
                        f"{name1} and {name2} are a picture-perfect match—if your idea of love involves murder, manipulation, and immaculate eyeliner.",
                        f"J would deny any affection. Then destroy the evidence. But yes, she’s into you. Deeply."
                    ]
                    advice = [
                        "Compliment her killing efficiency. And maybe bring her a snack. Human snacks.",
                        "You’re probably not safe. But you’re definitely *in.*"
                    ]
                elif compat_score > 70:
                    verdict_msg = [

                    ]
                elif compat_score > 50:
                    verdict_msg = [
                        f"J is intrigued. Mildly. That’s as close as you’re going to get without a body count.",
                        f"There’s a mutual fascination. J’s deciding whether you’re a threat, a snack, or something worth keeping around."
                    ]
                    advice = [
                        "Try flattery. But don’t seem *too* impressed. She’ll lose interest.",
                        "If she stabs you, it’s probably foreplay."
                    ]


            

        else:
            if compat_score > 90:
                verdict_msg = [
                    f"The two of {'you' if self_check else 'them'} would make a perfect couple! Could I get an invite to the wedding?",
                    f"{name1} and {name2} are what rom-com writers dream about.",
                    f"If they aren’t soulmates, then I don’t believe in stars or fate or serotonin.",
                    f"{name1} just unlocked {name2}’s final emotional achievement. It’s over. They’re in love.",
                    f"They don’t finish each other’s sentences. They finish each other’s character arcs."
                ]
                gifs = ["https://tenor.com/view/san-valentin-gif-8022758834552143209", "https://tenor.com/view/ryan-reynolds-sandra-bullock-the-proposal-gif-8868267", "https://tenor.com/view/up-carl-fredricksen-ellie-fredricksen-hold-hands-couple-gif-4108533"]
                advice = [
                    "Start booking wedding venues now?",
                    "I’d ship it, but I think it's already docked.",
                    "You should probably start picking a first dance song.",
                    "Consider joint therapy—not because you need it, but just to make other couples jealous."
                ]
            elif compat_score > 70:
                verdict_msg = [
                    f"{name1} and {name2} are giving major will-they-won’t-they energy. Just kiss already. 💋",
                    f"They’re flirting with fate and not even realizing it.",
                    f"The tension? Palpable. The glances? Lingering.",
                    f"{name1} and {name2} are one slow dance away from changing everything.",
                    f"It’s giving ‘best friends in denial’ energy."
                ]
                gifs = ["https://tenor.com/view/actor-tom-holland-2021-film-spider-man-no-way-home-many-hearts-hearts-of-love-happy-gif-4757443864403941048", "https://tenor.com/view/slide-slide-in-sup-girl-hey-flirting-gif-15281037987083649555", "https://tenor.com/view/flirting-flirty-kiss-face-gif-18108646"]
                advice = [
                    "There’s a spark here. Someone just has to light it properly.",
                    "Text them. Yes, now.",
                    "You’re one rainstorm away from cinematic tension.",
                    "If you wait too long, Netflix will steal this plotline."
                ]
            elif compat_score > 50:
                verdict_msg = [
                    f"{name1} and {name2} might work... but only if one of them gets character development first.",
                    f"They have potential. Unfortunately, so does nuclear fusion.",
                    f"{name1} and {name2} are what fanfic writers call ‘problematic but hot.’",
                    f"This is one of those ships that would trend on Twitter... and then get cancelled.",
                    f"{name1} and {name2} love each other. They just don’t like each other yet."
                ]
                gifs = ["https://tenor.com/view/i-mean-i-think-that-could-work-kelsey-peters-hilary-duff-younger-that-has-potential-gif-21545532", "https://tenor.com/view/we-can-do-this-kiernan-shipka-sabrina-spellman-chilling-adventures-of-sabrina-have-faith-gif-16497314"]
                advice = [
                    "Maybe a few therapy sessions. Or a road trip. Or both.",
                    "Consider dating apps... separately... then regroup in a month.",
                    "You're not doomed. But maybe avoid IKEA for a while.",
                    "Talk it out. With words. Not passive-aggressive playlists."
                ]
            elif compat_score > 30:
                verdict_msg = [
                    f"I mean… {name1} and {name2} *technically* could date. But would they survive the group chat drama?",
                    f"{name1} and {name2} together? That’s... a choice.",
                    f"It’s not love—it’s mutually assured emotional damage.",
                    f"This is the couple people warn you about in tarot readings.",
                    f"They’d have passion. And also a Netflix true crime doc in five years."
                ]
                gifs = ["https://tenor.com/view/yikes-cringe-fake-smile-gif-14838421114574087139","https://tenor.com/view/britney-spears-awkward-fake-smile-forced-thats-nice-dear-gif-24039553", "https://tenor.com/view/wattsthesafeword-wts-pupamp-uncomfortable-face-gif-21851966"]
                advice = [
                    "If you're going to try this, do it far away from mutuals.",
                    "Love is blind, but your friends aren’t. They’re watching.",
                    "Maybe it’s just a vibe. Not a commitment.",
                    "Avoid making matching tattoos. Like... seriously."
                ]
            else:
                verdict_msg = [
                    f"{name1} and {name2}? That’s not romance. That’s a cease-and-desist letter waiting to happen.",
                    f"Every timeline where {name1} and {name2} get together ends in emotional litigation.",
                    f"This isn’t a ship. It’s a shipwreck.",
                    f"Friends don’t let friends date each other. Especially not like this.",
                    f"Somebody here deserves better. It might be both of them."
                ]
                gifs = ["https://tenor.com/view/ariana-grande-barbiaminaj-glinda-ariana-grande-wicked-wicked-gif-3768134899335161969", "https://tenor.com/view/fight-couple-gif-26407590", "https://tenor.com/view/pillow-pillow-fight-couple-gif-26058767"]
                advice = [
                    "Maybe don’t. Just—don’t.",
                    "Put the phone down. Step away from the heart emoji.",
                    "This isn’t going to end well. Unless it doesn’t start.",
                    "Save everyone some trauma. Try friendship instead. Or exile."
                ]




        try:
            if embed_bool:
                embed = discord.Embed(
                    title="💘 Lovecheck Results 💘",
                    description=f"**{name1}** {'❤️' if compat_score > 50 else '💔'} **{name2}**",
                    color=discord.Color.pink()
                )

                embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
                embed.add_field(name="Compatibility Score", value=f"**{compat_score}%**", inline=False)
                embed.add_field(name="Verdict", value=random.choice(verdict_msg), inline=False)

                embed.set_footer(text=random.choice(advice))
                

                await interaction.followup.send(embed=embed)
                await asyncio.sleep(0.3)
                await interaction.channel.send(f"The mystical {self.bot.user.mention} has made this prediction! They also predict this shall be the reaction of {name1} and {name2}:\n")
                await interaction.channel.send(f"{random.choice(gifs)}")
            else:
                await interaction.followup.send(
                    f"{interaction.user.display_name} has ordered a love check!\n\n"
                    "💘 **Lovecheck Results** 💘\n"
                    f"**{name1}** {'❤️' if compat_score > 50 else '💔'} **{name2}**\n"
                    f"**Compatibility Score:** {compat_score}%\n"
                    f"**The Mystic {self.bot.user.mention}'s Verdict:** {random.choice(verdict_msg)}\n"
                    f"**Relationship Advice:** {random.choice(advice)}\n"
                )
                await interaction.channel.send(f"{random.choice(gifs)}")

        except Exception as e:
            await interaction.followup.send(f"There was an error: {e}. Please report it to the bot owner.", ephemeral=True)