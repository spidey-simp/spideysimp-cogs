import random
import discord
import asyncio
from discord.ext import commands
from redbot.core.bot import Red
from redbot.core import commands, Config
import wordfreq
import nltk
from nltk.corpus import words
import os

nltk.download("words")

all_words = words.words()

active_games = {}


def get_idioms():
    """Scrapes common idioms from this website."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "idioms.txt")
    idioms = []
    
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if ":" in line:
                idiom = line.split(":")[0]
                idioms.append(idiom.lower())

    return idioms

def get_filtered_words(difficulty: str):
    """Filters words based on difficulty using word frequency."""
    difficulty_settings = {
        "novice": {"freq": .0001, "min_length": 4, "max_length": 6},
        "easy": {"freq": 0.00001, "min_length": 4, "max_length": 8},
        "medium": {"freq": 0.000001, "min_length": 4, "max_length": 10},
        "hard": {"freq": 0.0000001, "min_length": 6, "max_length": 12},
        "expert": {"freq": 0.00000001, "min_length": 6, "max_length": 20},
        "impossible": {"freq": 0.000000001, "min_length": 8, "max_length": None}  # No upper limit
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

def get_timeout(word: str):
    """Calculates timeout based on word length."""
    base_time = 40  # Minimum time for short words
    extra_time_per_letter = 5  # Additional seconds per letter after 6 letters
    return min(120, base_time + max(0, (len(word) - 6) * extra_time_per_letter))  # Cap at 120 sec


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
            impossible_wins=0,
            phrase_toggle = False
        )
        self.config.register_guild(difficulty="medium")
    
    @commands.group(name="spideygameset", aliases=["sgs"])
    async def spideygameset(self, ctx: commands.Context):
        """Command to change the game settings."""
        await ctx.send("Currently this command has no settings.")
    
    @commands.group(name="anagram", invoke_without_command=True)
    async def anagram(self, ctx: commands.Context):
        """Anagram game command group."""
        subcommands = ["start", "hint", "leaderboard", "settings", "stop"]
        command_list = "\n".join([f"- **[p]anagram {cmd}**" for cmd in subcommands])

        await ctx.send(f"**Anagram Commands:**\n{command_list}\n\nUse `[p]anagram start` to begin a game!")

    @anagram.command(name="start", aliases=["s"])
    async def anagram_start(self, ctx: commands.Context):
        """Decode a random english word."""
        if ctx.channel.id in self.active_games:
            await ctx.send("A game is already running in this channel. Please wait for the game to end before starting a new one.")
            return
        
        phrase_setting = await self.config.member(ctx.author).phrase_toggle()
        if phrase_setting:
            player_difficulty = "medium"
            phrase_list = get_idioms()
            base = random.choice(phrase_list)
            scrambled = await self.scramble_phrase(base)
        else:
            player_difficulty = await self.config.member(ctx.author).difficulty()
            word_list = get_filtered_words(player_difficulty)
            base = random.choice(word_list)
            scrambled = await self.scrambler(base)

        self.active_games[ctx.channel.id] = {"word": base, "hint_level": 0}
        

        await ctx.send("The game is about to begin . . .")
        await asyncio.sleep(1)
        timeout_duration = get_timeout(base)
        game_message = await ctx.send(f"🔠 **Unscramble this {'phrase' if phrase_setting else 'word'}:** `{scrambled}`\n⏳ **Time remaining: {timeout_duration} seconds**\n{'💡 Type `[p]anagram hint` for a clue!' if not phrase_setting else ''}")

        async def countdown_timer(time_amount: int):
            """Updates the message every 10 seconds."""
            remaining_times = list(range(time_amount - 10, 0, -10))
            for remaining in remaining_times:
                await asyncio.sleep(10)
                if ctx.channel.id not in self.active_games:
                    return
                await game_message.edit(content=f"🔠 **Unscramble this {'phrase' if phrase_setting else 'word'}:** `{scrambled}`\n⏳ **Time remaining: {remaining} seconds**\n{'💡 Type `[p]anagram hint` for a clue!' if not phrase_setting else ''}")

        self.bot.loop.create_task(countdown_timer(timeout_duration))
        def check(message): 
            normalized_guess = message.content.lower().replace("’", "'")
            normalized_answer = base.lower().replace("’", "'")
            return message.channel == ctx.channel and normalized_guess == normalized_answer
        try:
            while ctx.channel.id in self.active_games:
                message = await self.bot.wait_for('message', timeout=timeout_duration, check=check)
                if ctx.channel.id not in self.active_games:
                    return
                if message.content.lower() == base:
                    difficulty_field = f"{player_difficulty}_wins"
                    current_wins = await self.config.member(message.author).get_raw(difficulty_field)
                    await self.config.member(message.author).set_raw(difficulty_field, value=current_wins + 1)
                    await ctx.send(f"🎉 {message.author.mention} won! The {'phrase' if phrase_setting else 'word'} was `{base}`!")
                    break
        except asyncio.TimeoutError:
            if ctx.channel.id in self.active_games:
                await ctx.send(f"⏳ Time's up! Nobody guessed the word. The correct {'phrase' if phrase_setting else 'word'} was `{base}`! Try again!")
        
        if ctx.channel.id not in self.active_games:
            return
        else:
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
    
    async def scramble_phrase(self, phrase: str):
        """Scrambles each word in a phrase while keeping spaces in tact."""
        phrase_words = phrase.split(" ")
        scrambled_words = ["".join(random.sample(word, len(word))) for word in phrase_words]
        return " ".join(scrambled_words)
    
    @anagram.command(name="hint")
    async def anagram_hint(self, ctx: commands.Context):
        """Gives the first letter as a hint."""
        if ctx.channel.id not in self.active_games:
            await ctx.send("❌ No active game in this channel!")
            return
        
        game = self.active_games[ctx.channel.id]
        word = game["word"]
        if " " in word:
            await ctx.send("Hints are currently not setup for phrases. Sorry.")
            return
        
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
    
    @anagram.command(name="stop", aliases=["st"])
    async def anagram_stop(self, ctx:commands.Context, game_channel: discord.TextChannel = None):
        """Stops an existing game."""
        game_channel = game_channel or ctx.channel
        channel_id = game_channel.id
        if channel_id not in self.active_games:
            await ctx.send(f"❌ No active game found in {game_channel.mention}.")
            return
        answer = self.active_games[channel_id]["word"]
        del self.active_games[channel_id]
        
        channel_message = f" in {game_channel.mention}" if game_channel != ctx.channel else ""
        await ctx.send(f"Game successfully stopped{channel_message}! The answer was {answer}!")

    
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
            key=lambda x: sum(v for v in x[1].values() if isinstance(v, int)),  # Sum of all difficulty wins
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
            total_wins = sum(v for v in data.values() if isinstance(v, int))  # Sum of all difficulty wins
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

    
    @anagram.group(name="settings", invoke_without_command=True)
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
    
    @anagram_setting.command(name="phrases")
    async def anagram_setting_phrases(self, ctx:commands.Context):
        """If you run this command, the presumption is you are toggling phrases to the opposite of whatever you have it."""
        toggle_setting = await self.config.member(ctx.author).phrase_toggle()

        if toggle_setting == True:
            toggle_setting = False
        else:
            toggle_setting = True
        
        await self.config.member(ctx.author).phrase_toggle.set(toggle_setting)

        await ctx.send(f"You have successfully toggled phrases `{'on' if toggle_setting else 'off'}`.")
