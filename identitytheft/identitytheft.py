import re
import random
from collections import defaultdict
from datetime import datetime, timedelta

import discord
import discord.http
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Cog

async def fetch_url(session, url):
    async with session.get(url) as response:
        assert response.status == 200
        return await response.json()

class IdentityTheft(Cog):
    """
    Identity Theft!

    The idea for this cog comes from the Dad cog by Fox-V3.
    It is designed to respond to user messages saying "I'm . . . " with funny messages.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=684457913250480143, force_registration=True)

        default_guild = {"enabled": False, "cooldown": 0, "blacklist": []}

        self.config.register_guild(**default_guild)

        self.cooldown = defaultdict(datetime.now)

        self.self_mention_responses = [
            "Yes, we know lol",
            "Woah, Captain Obvious has arrived!",
            "Really? We had no idea.",
            "The sky is blue also.",
            "Oh, look who's talking!",
            "Thanks for the update!",
             "Congratulations, you just stated the obvious.",
            "Oh look, Captain Obvious has graced us with their presence.",
            "Stop—you're going to make the obvious seem revolutionary.",
            "Thanks, Sherlock, but we already knew water is wet.",
            "Wow, your insight is as deep as a puddle.",
            "Hold on, let me alert the media: the obvious just spoke.",
            "Amazing—another reminder that you're, well, you.",
            "Bravo! Your knack for stating the self-evident is unparalleled.",
            "Keep it up, genius. We all needed that groundbreaking update.",
            "Well, that was obvious. Thanks for making it painfully clear."
        ]

        self.impersonation_responses = [
            "I'm impersonating you now! How do you like it?!",
            "I'm {author}—the upgrade your sorry ass always needed!",
            "Heads up: I just hijacked your identity. Mediocrity just got booted!",
            "Oh snap, your identity just got a major makeover. Welcome to the new model!",
            "Your clone is trash, so I took over. Get used to perfection, {author}!",
            "Warning: Identity theft in progress. Your weak self has been replaced with a boss!",
            "I stole your identity—let's be honest, your old version was a total flop!",
            "Sorry not sorry—I'm {author} 2.0, and your outdated self is history!",
            "Identity hijacked. Consider this your upgrade from bland to badass!",
            "Your identity just got a serious overhaul—if you can't handle it, that's on you!",
            "Damn, I just pulled down my pants and no wonder you're so grumpy all the time!",
            "I immediately regret my decision. You do not have much going on.",
            "I'm {author} with extra edge—enjoy the upgrade, even if it hurts!",
            "Fuck yeah, I'm {author} now—upgrade complete, you pathetic excuse for a clone!",
            "Your identity sucked, so I took over. Consider it a fuckin' upgrade!",
            "I just hijacked your sorry ass identity and gave it a badass makeover!",
            "Damn, being {author} beats your lame ass any day!",
            "Hey, I'm {author} now—your old self was about as interesting as soggy cereal!",
            "Aw man, my dick is tiny now!",
            "Your identity was a steaming pile of shit. Now I'm {author}—the upgrade you never deserved!",
            "I'm {author} now, and your identity? Fuck that—I'm the real deal!"
        ]


    async def red_delete_data_for_user(self, **kwargs):
        """no data is collected from users"""
        return

    @commands.group()
    @checks.admin()
    async def identitytheft(self, ctx: commands.Context):
        """Toggle the identity theft auto-response."""
        pass
    
    @identitytheft.command(name="enable")
    async def identitytheft_enable(self, ctx: commands.Context):
        """Toggles if you want the automatic bot responses on."""
        is_on = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not is_on)
        await ctx.send("Automatic responses to identify theft messages are now set to {}".format(not is_on))

    @identitytheft.command(name="cooldown")
    async def identitytheft_cooldown(self, ctx: commands.Context, cooldown: int):
        """Set the cooldown (in seconds) of auto responses."""

        await self.config.guild(ctx.guild).cooldown.set(cooldown)
        self.cooldown[ctx.guild.id] = datetime.now()
        await ctx.send("Auto responses cooldown is now set to {} seconds".format(cooldown))
    
    @identitytheft.group(name="blacklist", aliases=["bl"])
    async def blacklist(self, ctx: commands.Context):
        """Manage your webhook impersonation blacklist."""
        pass

    @blacklist.command(name="optout", aliases=["off", "oo"])
    async def blacklist_optout(self, ctx:commands.Context):
        """Opt out of having your profile used for webhook impersonation."""
        guild_blacklist = await self.config.guild(ctx.guild).blacklist()
        if ctx.author.id in guild_blacklist:
            await ctx.send("You are already opted out of webhook impersonation.")
            return
        guild_blacklist.append(ctx.author.id)
        await self.config.guild(ctx.guild).blacklist.set(guild_blacklist)
        await ctx.send("You have opted out of webhook impersonation.")
    
    @blacklist.command(name="optin", aliases=["on", "oi"])
    async def blacklist_optin(self, ctx: commands.Context):
        """Opt in to having your profile used for webhook impersonation."""
        guild_blacklist = await self.config.guild(ctx.guild).blacklist()
        if ctx.author.id not in guild_blacklist:
            await ctx.send("You are not opted out.")
            return
        guild_blacklist.remove(ctx.author.id)
        await self.config.guild(ctx.guild).blacklist.set(guild_blacklist)
        await ctx.send("You have opted in for webhook impersonation.")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        guild: discord.Guild = message.guild
        if guild is None:
            return
        
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        
        guild_config = self.config.guild(guild)
        is_on = await guild_config.enabled()
        if not is_on:
            return
        
        if self.cooldown[guild.id] > datetime.now():
            return
        
        cleaned_content = message.clean_content.strip()
        lower_content = cleaned_content.lower()

        index = lower_content.find("i'm")
        if index == -1:
            index = lower_content.find("i’m")
        if index == -1:
            index = lower_content.find(" im ")
        if index == -1:
            return
        
        candidate = cleaned_content[index:]
        
        match_candidate = re.match(r"(?i)^\s*(?:i(?:['’]m|m))\s+(.+)", candidate)

        if match_candidate:
            target_text = match_candidate.group(1).strip()
        else:
            return
        
        def normalize(text: str) -> str:
            return re.sub(r'[^a-z]', '', text.lower())

        target_member = None
        mention_match = re.match(r"<@!?(\d+)>", target_text)
        if mention_match:
            member_id = int(mention_match.group(1))
            target_member = guild.get_member(member_id)
        else:
            normalized_candidate = normalize(target_text)
            if (normalize(message.author.display_name).startswith(normalized_candidate) or normalize(message.author.name).startswith(normalized_candidate)):
                target_member = message.author
            else:
                for member in guild.members:
                    if (normalize(member.display_name).startswith(normalized_candidate) or normalize(member.name).startswith(normalized_candidate)):
                        target_member = member
                        break
        
        if target_member is None:
            return
        
        if target_member.id == guild.me.id:
            try:
                await message.channel.send(
                    f"Identity theft is not a joke {message.author.mention}! Millions of families suffer every year!",
                    allowed_mentions=discord.AllowedMentions(),
                )
            except discord.HTTPException:
                return
            
            self.cooldown[guild.id] = datetime.now() + timedelta(
                seconds=(await guild_config.cooldown())
            )
            return
        
        if target_member.id == message.author.id:
            response = random.choice(self.self_mention_responses)
            try:
                await message.channel.send(response)
            except discord.HTTPException:
                return
            self.cooldown[guild.id] = datetime.now() + timedelta(seconds=(await guild_config.cooldown()))
            return
        
        try:
            await message.channel.send(f"How would you like it if I pretended to be you, {message.author.mention}?!")
        except discord.HTTPException:
            return
        
        guild_blacklist = await self.config.guild(guild).blacklist()
        if message.author.id in guild_blacklist:
            self.cooldown[guild.id] = datetime.now() + timedelta(seconds=(await guild_config.cooldown()))
            return
        
        permissions = message.channel.permissions_for(guild.me)
        if not permissions.manage_webhooks:
            self.cooldown[guild.id] = datetime.now() + timedelta(seconds=(await guild_config.cooldown()))
            return
        
        try:
            webhooks = await message.channel.webhooks()
            webhook = next((wh for wh in webhooks if wh.name == "IdentityTheftWebhook"), None)
            if webhook is None:
                webhook = await message.channel.create_webhook(name="IdentityTheftWebhook")
            
            impersonation_message = random.choice(self.impersonation_responses).format(author=message.author.display_name)
            await webhook.send(
                impersonation_message,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            )
        except Exception:
            pass
        
        self.cooldown[guild.id] = datetime.now() + timedelta(seconds = (await guild_config.cooldown()))
