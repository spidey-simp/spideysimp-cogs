from collections import defaultdict
from datetime import datetime, timedelta

import discord
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
    It is designed to respond to user messages saying "I'm [bot name]" saying not to commit identity theft.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6897100, force_registration=True)

        default_guild = {"enabled": True, "cooldown": 0}

        self.config.register_guild(**default_guild)

        self.cooldown = defaultdict(datetime.now)

    async def red_delete_data_for_user(self, **kwargs):
        """no data is collected from users"""
        return

    @commands.group()
    @checks.admin()
    async def identitytheft(self, ctx: commands.Context):
        """Identity Theft is a cog designed to respond to users when they say I'm [bot name]"""
        pass
    
    @identitytheft.command(name="enable")
    async def identitytheft_enable(self, ctx: commands.Context):
        """Toggles if you want the automatic bot responses on"""
        is_on = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not is_on)
        await ctx.send("Automatic responses to messages saying 'I'm [botname]' are now set to {}".format(not enabled))

    @identitytheft.command(name="cooldown")
    async def identitytheft_cooldown(self, ctx: commands.Context, cooldown: int):
        """Set the cooldown of auto responses."""

        await self.config.guild(ctx.guild).cooldown.set(cooldown)
        self.cooldown[ctx.guild.id] = datetime.now()
        await ctx.send("Auto responses cooldown is now set to {} seconds".format(cooldown))

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        guild: discord.Guild = getattr(message, "guild", None)
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
        
        cleaned_content = message.clean_content
        content_split = cleaned_content.split()
        if len(content_split) == 0:
            return


        if f"i'm {guild.me.display_name}" in cleaned_content:
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
        else:
            return
