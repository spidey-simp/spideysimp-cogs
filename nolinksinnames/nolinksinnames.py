import discord
from redbot.core import commands
import re

LINK_REGEX = re.compile(
    r"(https?:\/\/)?(www\.)?[\w\-]+\.(com|net|org|gg|xyz|link|store|live|info|to)(\/\S*)?",
    re.IGNORECASE,
)

def name_contains_link(name: str) -> bool:
    return bool(LINK_REGEX.search(name))


class NoLinksInNames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    async def check_name(self, member: discord.Member):
        name_to_check = member.display_name or ""
        user_name = member.name
        if name_contains_link(name_to_check):
            try:
                await member.edit(nick=user_name)
            except discord.Forbidden:
                pass  # Bot lacks permissions
            # Optional: Send warning
            try:
                await member.send("Your nickname was reset because it included a link. Please use a name without ads or links.")
            except discord.Forbidden:
                pass  # Can't DM

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            await self.check_name(after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.check_name(member)
    
    @commands.command(name="guildlinkcheck", aliases=["glc"])
    @commands.mod_or_permissions(manage_guild=True)
    async def guildlinkcheck(self, ctx: commands.Context):
        """Runs a guild-wide check to ensure no display names contain links."""
        changed_members = []

        for member in ctx.guild.members:
            name_to_check = member.display_name or ""
            if name_contains_link(name_to_check):
                try:
                    await member.edit(nick=member.name)
                    changed_members.append(member)
                    try:
                        await member.send(
                            "Your nickname was reset because it included a link. Please use a name without ads or links."
                        )
                    except discord.Forbidden:
                        pass
                except discord.Forbidden:
                    continue  # Skip if the bot can't edit them

        if changed_members:
            member_list = "\n- " + "\n- ".join(m.display_name for m in changed_members)
            await ctx.send(
                f"The following members had links in their names and were renamed:{member_list}"
            )
        else:
            await ctx.send("No linked names found.")
