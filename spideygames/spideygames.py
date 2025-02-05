import random
import discord
import asyncio
from discord.ext import commands
from redbot.core.bot import Red
from redbot.core import commands, Config
import nltk
from nltk.corpus import words

nltk.download("words")

word_list = [word.lower() for word in words.words() if 9 > len(word) > 4]
active_games = {}

class SpideyGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.config = Config.get_conf(self, identifier=13904817238971)
        self.config.register_member(wins=0)
    
    @commands.group(name="spideygameset", aliases=["sgs"])
    async def spideygameset(self, ctx: commands.Context):
        """Command to change the game settings."""
        await ctx.send("Currently this command has no settings.")
    
    @commands.group(name="anagram", invoke_without_command=True)
    async def anagram(self, ctx: commands.Context):
        """Anagram game command group."""
        subcommands = ["start", "hint", "leaderboard"]
        command_list = "\n".join([f"- **[p]anagram {cmd}**" for cmd in subcommands])

        await ctx.send(f"**Anagram Commands:**\n{command_list}\n\nUse `[p]anagram start` to begin a game!")

    @anagram.command(name="start", aliases=["s"])
    async def anagram_start(self, ctx: commands.Context):
        """Decode a random english word."""
        if ctx.channel.id in self.active_games:
            await ctx.send("A game is already running in this channel. Please wait for the game to end before starting a new one.")
            return

        base_word = random.choice(word_list)
        self.active_games[ctx.channel.id] = {"word": base_word, "hint_level": 0}
        
        scrambled_word = await self.scrambler(base_word)

        await ctx.send("The game is about to begin . . .")
        await asyncio.sleep(1)
        game_message = await ctx.send(f"🔠 **Unscramble this word:** `{scrambled_word}`\n⏳ **Time remaining: 60 seconds**\n💡 Type `[p]anagram hint` for a clue!")

        async def countdown_timer():
            """Updates the message every 10 seconds."""
            for remaining in [50, 40, 30, 20, 10]:
                await asyncio.sleep(10)
                if ctx.channel.id not in self.active_games:
                    return
                await game_message.edit(content=f"🔠 **Unscramble this word:** `{scrambled_word}`\n⏳ **Time remaining: {remaining} seconds**\n💡 Type `[p]anagram hint` for a clue!")


        self.bot.loop.create_task(countdown_timer())
        def check(message): return message.channel == ctx.channel and message.content.lower() == base_word
        try:
            message = await self.bot.wait_for('message', timeout=60.0, check=check)
            if message.content.lower() == base_word:

                current_wins = await self.config.member(message.author).wins()
                await self.config.member(message.author).wins.set(current_wins + 1)
                await ctx.send(f"🎉 {message.author.mention} won! The word was `{base_word}`!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ Time's up! Nobody guessed the word. The correct word was `{base_word}`! Try again!")
        
        del self.active_games[ctx.channel.id]

    async def scrambler(self, word: str):
        """Scrambles words."""
        stripped_word = list(word.strip())
        while True:
            shuffled_word = stripped_word[:]
            random.shuffle(shuffled_word)
            anagram = "".join(shuffled_word)
            if anagram != word:
                    return anagram
    
    @anagram.command(name="hint")
    async def anagram_hint(self, ctx: commands.Context):
        """Gives the first letter as a hint."""
        if ctx.channel.id not in self.active_games:
            await ctx.send("❌ No active game in this channel!")
            return
        
        game = self.active_games[ctx.channel.id]
        word = game["word"]
        hint_level = game["hint_level"]
        if hint_level == 0:
            hint = f"💡First hint: The word starts with `{word[0].upper()}`"
        elif hint_level == 1:
            half_revealed = list(word[: len(word) // 2])
            random.shuffle(half_revealed)
            hint = f"💡 Second hint: Here is the first half of the word (shuffled): `{''.join(half_revealed)}`"
        elif hint_level == 2:
            revealed = [letter if i % 2 == 0 else "_" for i, letter in enumerate(word)]
            hint = f"💡 Final hint: `{''.join(revealed)}`"
        else:
            await ctx.send("❌ No more hints available!")
            return
        
        game["hint_level"] += 1
        await ctx.send(hint)
    
    @anagram.command(name="leaderboard", aliases=["lb"])
    async def anagram_leaderboard(self, ctx: commands.Context):
        """Shows the top 10 players with the most anagram wins."""
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)

        if not sorted_members:
            await ctx.send("No one has won an anagram game yet!")
            return

        # Format leaderboard message
        leaderboard = "\n".join(
            [f"**{i+1}.** <@{user_id}> - {data['wins']} wins" for i, (user_id, data) in enumerate(sorted_members[:10])]
        )

        await ctx.send(f"🏆 **Anagram Leaderboard** 🏆\n{leaderboard}")