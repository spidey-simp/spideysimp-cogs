import random
import discord
import asyncio
from discord.ext import commands
from redbot.core.bot import Red
from redbot.core import commands, Config
import wordfreq
import nltk
from nltk.corpus import words

nltk.download("words")

all_words = words.words()

active_games = {}

def get_filtered_words(difficulty: str):
    """Filters words based on difficulty using word frequency."""
    difficulty_settings = {
        "novice": {"freq": .001, "min_length": 4, "max_length": 6},
        "easy": {"freq": 0.0001, "min_length": 4, "max_length": 8},
        "medium": {"freq": 0.00001, "min_length": 4, "max_length": 10},
        "hard": {"freq": 0.000001, "min_length": 6, "max_length": 12},
        "expert": {"freq": 0.0000001, "min_length": 6, "max_length": 20},
        "impossible": {"freq": 0.00000001, "min_length": 8, "max_length": None}  # No upper limit
    }

    settings = difficulty_settings.get(difficulty, difficulty_settings["medium"])
    min_length, max_length = settings["min_length"], settings["max_length"]
    frequency_threshold = settings["freq"]
    return [
        word.lower() for word in words.words()
        if wordfreq.word_frequency(word, "en") >= frequency_threshold
        and len(word) >= min_length
        and (max_length is None or len(word) <= max_length)
    ]

class SpideyGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.config = Config.get_conf(self, identifier=13904817238971)
        self.config.register_member(
            difficulty="medium",
            novice_wins= 0, 
            easy_wins=0,
            medium_wins=0,
            hard_wins=0,
            expert_wins=0,
            impossible_wins=0
        )
        self.config.register_guild(difficulty="medium")
    
    @commands.group(name="spideygameset", aliases=["sgs"])
    async def spideygameset(self, ctx: commands.Context):
        """Command to change the game settings."""
        await ctx.send("Currently this command has no settings.")
    
    @commands.group(name="anagram", invoke_without_command=True)
    async def anagram(self, ctx: commands.Context):
        """Anagram game command group."""
        subcommands = ["start", "hint", "leaderboard", "settings"]
        command_list = "\n".join([f"- **[p]anagram {cmd}**" for cmd in subcommands])

        await ctx.send(f"**Anagram Commands:**\n{command_list}\n\nUse `[p]anagram start` to begin a game!")

    @anagram.command(name="start", aliases=["s"])
    async def anagram_start(self, ctx: commands.Context):
        """Decode a random english word."""
        if ctx.channel.id in self.active_games:
            await ctx.send("A game is already running in this channel. Please wait for the game to end before starting a new one.")
            return

        player_difficulty = await self.config.member(ctx.author).difficulty()
        word_list = get_filtered_words(player_difficulty)
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
                difficulty_field = f"{player_difficulty}_wins"
                current_wins = await self.config.member(message.author).get_raw(difficulty_field)
                await self.config.member(message.author).set_raw(difficulty_field, value=current_wins + 1)
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
        """Shows the multi-column leaderboard for all difficulties."""
        
        all_members = await self.config.all_members(ctx.guild)

        if not all_members:
            await ctx.send("No one has won an anagram game yet!")
            return

        # Sort players by total wins (sum of all difficulty wins)
        sorted_members = sorted(
            all_members.items(),
            key=lambda x: sum(x[1].values()),  # Sum of all difficulty wins
            reverse=True
        )

        # Generate leaderboard output
        leaderboard_lines = [
            f"🏆 **Anagram Leaderboard** 🏆\n\n"
            f"```"
            f"{'Player':<15} {'Nov':<4} {'Ez':<4} {'Med':<4} {'Hard':<4} {'Exp':<4} {'Imp':<4} {'Total':<5}\n"
            f"{'-'*50}"
        ]

        for user_id, data in sorted_members[:10]:  # Top 10 players
            total_wins = sum(data.values())  # Sum of all difficulty wins
            leaderboard_lines.append(
                f"{ctx.guild.get_member(user_id).display_name:<15} "
                f"{data.get('novice_wins', 0):<4} "
                f"{data.get('easy_wins', 0):<4} "
                f"{data.get('medium_wins', 0):<4} "
                f"{data.get('hard_wins', 0):<4} "
                f"{data.get('expert_wins', 0):<4} "
                f"{data.get('impossible_wins', 0):<4} "
                f"{total_wins:<5}"
            )

        leaderboard_lines.append("```")  # Close code block for formatting
        await ctx.send("\n".join(leaderboard_lines))

    
    @anagram.group(name="setting", invoke_without_command=True)
    async def anagram_setting(self, ctx:commands.Context):
        """Manage your personal anagram game settings."""
        await ctx.send("Use `[p]anagram setting difficulty <novice/easy/medium/hard/expert/impossible>` to change your difficulty.")
    
    @anagram_setting.command(name="difficulty")
    async def anagram_setting_difficulty(self, ctx:commands.Context, difficulty: str):
        """Set your personal anagram difficulty."""
        valid_difficulties = ["novice", "easy", "medium", "hard", "expert", "impossible"]

        if difficulty.lower() not in valid_difficulties:
            await ctx.send(f"❌ Invalid difficulty! Choose from: {', '.join(valid_difficulties)}.")
            return
        
        await self.config.member(ctx.author).difficulty.set(difficulty.lower())
        await ctx.send(f"✅ {ctx.author.mention}, your anagram difficulty has been set to **{difficulty}**!")
