from redbot.core import commands
import discord
import aiohttp
import json
import os
from discord import app_commands
import html
import asyncio
import random
import urllib.parse

BASE_DIR = os.path.dirname(__file__)

API_KEYS = os.path.join(BASE_DIR, "api_keys.json")

CURRENT_API_LIST = ["cat_api"]

cat_breed_list = ["abys", "aege", "abob", "acur", "asho", "awir", "amau", "amis", "bali",
                  "bamb", "beng", "birm", "bomb", "bslo", "bsho", "bure", "buri", "cspa",
                  "ctif", "char", "chau", "chee", "csho", "crex", "cymr", "cypr", "drex",
                  "dons", "lihu", "emau", "ebur", "esho", "hbro", "hima", "jbob", "java",
                  "khao", "kora", "kuri", "lape", "mcoo", "mala", "manx", "munc", "nebe",
                  "norw", "ocic", "orie", "pers", "pixi", "raga", "ragd", "rblu", "sava",
                  "sfol", "srex", "siam", "sibe", "sing", "snow", "soma", "sphy", "tonk",
                  "toyg", "tang", "tvan", "ycho"
                  ]

trivia_categories = [
    {"id": 9,"name": "General Knowledge"},
    {"id": 10,"name": "Entertainment: Books"},
    {"id": 11,"name": "Entertainment: Film"},
    {"id": 12,"name": "Entertainment: Music"},
    {"id": 13,"name": "Entertainment: Musicals & Theatres"},
    {"id": 14,"name": "Entertainment: Television"},
    {"id": 15,"name": "Entertainment: Video Games"},
    {"id": 16,"name": "Entertainment: Board Games"},
    {"id": 17,"name": "Science & Nature"},
    {"id": 18,"name": "Science: Computers"},
    {"id": 19,"name": "Science: Mathematics"},
    {"id": 20,"name": "Mythology"},
    {"id": 21,"name": "Sports"},
    {"id": 22,"name": "Geography"},
    {"id": 23,"name": "History"},
    {"id": 24,"name": "Politics"},
    {"id": 25,"name": "Art"},
    {"id": 26,"name": "Celebrities"},
    {"id": 27,"name": "Animals"},
    {"id": 28,"name": "Vehicles"},
    {"id": 29,"name": "Entertainment: Comics"},
    {"id": 30,"name": "Science: Gadgets"},
    {"id": 31,"name": "Entertainment: Japanese Anime & Manga"},
    {"id": 32,"name": "Entertainment: Cartoon & Animations"}
]

game_categories = [
    "mmorpg", "shooter", "strategy", "moba", "racing", "sports", "social", "sandbox", "open-world", "survival", "pvp", "pve", "pixel", "voxel", "zombie", "turn-based", "first-person", "third-Person", "top-down", "tank", "space", "sailing", "side-scroller", "superhero", "permadeath", "card", "battle-royale", "mmo", "mmofps", "mmotps", "3d", "2d", "anime", "fantasy", "sci-fi", "fighting", "action-rpg", "action", "military", "martial-arts", "flight", "low-spec", "tower-defense", "horror", "mmorts"
]


class CatLinkButton(discord.ui.Button):
    def __init__(self, wiki_url: str):
        super().__init__(label="Wikipedia", style=discord.ButtonStyle.link, url=wiki_url)

class CatView(discord.ui.View):
    def __init__(self, wiki_url: str):
        super().__init__()
        self.add_item(CatLinkButton(wiki_url))

class WorldOfApis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.api_keys = self.load_json()
        self.breed_dict = {}
        self.user_trivia_settings = {}

    
    def load_json(self) -> dict:
        if not os.path.exists(API_KEYS):
            return {}
        else:
            with open(API_KEYS, "r") as f:
                return json.load(f)
    
    def save_json(self) -> None:
        with open(API_KEYS, "w") as f:
            json.dump(self.api_keys, f, indent=4)
    
    async def load_dog_breeds(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thedogapi.com/v1/breeds") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Create dict: name -> id
                    self.breed_dict = {str(breed["id"]): breed["name"] for breed in data}  # ID → Name

                    # For autocomplete
                    self.autocomplete_list = [
                        app_commands.Choice(name=breed["name"], value=str(breed["id"])) for breed in data
                    ]
                else:
                    self.breed_dict = {}
                    self.autocomplete_list = []
    

    woa = app_commands.Group(name="woa", description="World of Apis commands")

    @woa.command(name="add_api_key", description="Add an api key for WOA.")
    @app_commands.describe(api="The program for the api key.", key="The api key itself.")
    @app_commands.choices(api=[
        app_commands.Choice(name="TheCatAPI", value="cat_api")
    ])
    async def add_api_key(self, interaction:discord.Interaction, api:str, key:str):

        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to edit api keys.", ephemeral=True)
        
        if api not in CURRENT_API_LIST:
            return await interaction.response.send_message("That API is not currently supported.")
        
        self.api_keys.setdefault(api, "")
        self.api_keys[api] = key
        self.save_json()
        await interaction.response.send_message(f"The api key for {api} has successfully been uploaded.", ephemeral=True)
    
    async def cat_breed_autocomplete(self, interaction:discord.Interaction, current: str):
        return [
            app_commands.Choice(name=breed, value=breed)
            for breed in cat_breed_list if current.lower() in breed.lower()
        ][:25]

    @woa.command(name="cat", description="See a cat with its facts.")
    @app_commands.describe(breed="The breed of cat you want to see.")
    @app_commands.autocomplete(breed=cat_breed_autocomplete)
    async def cat(self, interaction:discord.Interaction, breed: str=None):
        await interaction.response.defer(thinking=True)

        api = self.api_keys.get("cat_api")
        if not api:
            return await interaction.followup.send("Please ask the admin to upload an API key.", ephemeral=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.thecatapi.com/v1/images/search?{'breed_ids=' + breed + '&' if breed else ''}api_key={api}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Unable to find a cat :(")
                cat_json = await resp.json()

                cat_dict = cat_json[0]
                embed = discord.Embed(title="Cat Profile", color=discord.Color.blurple())
                embed.set_image(url=cat_dict.get("url"))
                embed.set_footer(text="Courtesy of TheCatAPI")

                breeds_list = cat_dict.get("breeds")
                if breeds_list:
                    breed_info = breeds_list[0]
                    name = breed_info.get("name")
                    desc = breed_info.get("description")
                    wiki_url = breed_info.get("wikipedia_url")

                    if name:
                        embed.title = f"{name} – Cat Profile"
                    if desc:
                        embed.add_field(name="📝 Description", value=desc, inline=False)
                    
                    temperament = breed_info.get("temperament")
                    if temperament:
                        embed.add_field(name="😺 Temperament", value=temperament, inline=False)

                    traits = {
                        "Affection": breed_info.get("affection_level"),
                        "Energy": breed_info.get("energy_level"),
                        "Intelligence": breed_info.get("intelligence"),
                        "Dog Friendly": breed_info.get("dog_friendly"),
                        "Child Friendly": breed_info.get("child_friendly"),
                        "Shedding": breed_info.get("shedding_level"),
                        "Grooming Needs": breed_info.get("grooming"),
                        "Health Issues": breed_info.get("health_issues"),
                        "Vocalization": breed_info.get("vocalisation"),
                    }
                    trait_lines = [
                        f"• **{k}**: {'⭐' * v}" for k, v in traits.items() if isinstance(v, int)
                    ]
                    if trait_lines:
                        embed.add_field(name="📊 Traits", value="\n".join(trait_lines), inline=False)

                    origin = breed_info.get("origin")
                    life_span = breed_info.get("life_span")
                    hypoallergenic = "Yes" if breed_info.get("hypoallergenic") else "No"
                    weight = breed_info.get("weight", {}).get("imperial")

                    details = []
                    if origin: details.append(f"• **Origin**: {origin}")
                    if life_span: details.append(f"• **Life Span**: {life_span} years")
                    if weight: details.append(f"• **Weight**: {weight} lbs")
                    details.append(f"• **Hypoallergenic**: {hypoallergenic}")

                    if details:
                        embed.add_field(name="📦 Additional Info", value="\n".join(details), inline=False)


                if wiki_url:
                    view = CatView(wiki_url)
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send(embed=embed)
    
    
    async def dog_breed_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            choice for choice in self.autocomplete_list if current.lower() in choice.name.lower()
        ][:25]

    @woa.command(name="dog", description="See a dog with its facts.")
    @app_commands.describe(breed="The breed of dog you want to see.")
    @app_commands.autocomplete(breed=dog_breed_autocomplete)
    async def dog(self, interaction: discord.Interaction, breed: str = None):
        await interaction.response.defer(thinking=True, ephemeral=False)

        api = self.api_keys.get("cat_api")
        if not api:
            return await interaction.followup.send("Please ask the admin to upload an API key.", ephemeral=True)

        base_url = "https://api.thedogapi.com/v1/images/search"
        breed_id_param = ""
        if breed:
            if not hasattr(self, "breed_dict") or not self.breed_dict:
                return await interaction.followup.send(
                    "🐕 Woah there! I want to look at dogs just as much as you! "
                    "Ask an admin to run `/woa initialize_dog`, or run this command without a breed for now.",
                    ephemeral=True
                )
            if breed not in self.breed_dict:
                return await interaction.followup.send("Breed not recognized. Please try again.", ephemeral=True)
            breed_id_param = f"&breed_ids={breed}"

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}?api_key={api}{breed_id_param}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Failed to fetch a dog image.")
                data = await resp.json()
                dog_dict = data[0]
                image_id = dog_dict.get("id")

            if not breed:
                # No breed = no metadata. Just send image.
                embed = discord.Embed(title="Here's a random dog!", color=discord.Color.orange())
                embed.set_image(url=dog_dict.get("url"))
                return await interaction.followup.send(embed=embed)

            # Otherwise: Get full breed info via image ID
            async with session.get(f"https://api.thedogapi.com/v1/images/{image_id}") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Failed to fetch dog metadata.")
                dog_meta = await resp.json()

        embed = discord.Embed(title="Dog Profile 🐾", color=discord.Color.orange())
        embed.set_image(url=dog_meta.get("url"))

        breeds_list = dog_meta.get("breeds")
        if breeds_list:
            breed_info = breeds_list[0]
            embed.add_field(name="Breed", value=breed_info.get("name", "Unknown"))

            if bred := breed_info.get("bred_for"):
                embed.add_field(name="Bred For", value=bred, inline=False)
            if group := breed_info.get("breed_group"):
                embed.add_field(name="Group", value=group, inline=True)
            if life := breed_info.get("life_span"):
                embed.add_field(name="Life Span", value=life, inline=True)
            if temper := breed_info.get("temperament"):
                embed.add_field(name="Temperament", value=temper, inline=False)
            if origin := breed_info.get("origin"):
                embed.set_footer(text=f"Origin: {origin}")

        await interaction.followup.send(embed=embed)

    @woa.command(name="initialize_dog", description="Initializes or refreshes the dog breed list.")
    async def initialize_dog(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("You do not have permission to initialize dog data.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.load_dog_breeds()
        await interaction.followup.send("Dog breeds have been initialized and are ready to go! 🐶", ephemeral=True)

    @woa.command(name="joke", description="Get a random joke!")
    async def joke(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        async with aiohttp.ClientSession() as session:
            async with session.get("https://v2.jokeapi.dev/joke/Any") as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Couldn't fetch a joke right now. Try again later!")

                joke_data = await resp.json()

        embed = discord.Embed(title="Here's a joke for you", color=discord.Color.green())

        if joke_data.get("flags", {}).get("nsfw"):
            embed.title += " 🔞"


        if joke_data["type"] == "single":
            embed.description = joke_data["joke"]
        else:
            setup = joke_data["setup"]
            delivery = joke_data["delivery"]
            embed.description = f"{setup}\n\n||{delivery}||"  # Spoiler tag for punchline

        await interaction.followup.send(embed=embed)

    @woa.command(name="advice", description="Receive a random piece of advice or search for one.")
    @app_commands.describe(query="Optional keyword to search for related advice.")
    async def advice(self, interaction: discord.Interaction, query: str = None):
        await interaction.response.defer(thinking=True)

        url = "https://api.adviceslip.com/advice"
        if query:
            url = f"https://api.adviceslip.com/advice/search/{query}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("Alas, the fates have failed to provide any advice.")

                text = await resp.text()
                data = json.loads(text)

        if query:
            slips = data.get("slips")
            if not slips:
                return await interaction.followup.send(f"No advice found for `{query}`. Even the wise cannot see all ends.")
            slip = slips[0]  # Take the first matching result
        else:
            slip = data.get("slip")

        if not slip:
            return await interaction.followup.send("There was an error retrieving the advice. Perhaps it was not meant for mortal ears.")

        embed = discord.Embed(
            title="💡 Advice",
            description=slip["advice"],
            color=discord.Color.teal()
        )
        await interaction.followup.send(embed=embed)

    async def trivia_category_autocomplete(self, interaction:discord.Interaction, current:str):
        category_choices = []

        for data in trivia_categories:
            if current.lower() in data["name"].lower():
                category_choices.append(app_commands.Choice(name=data.get("name"), value=str(data.get("id"))))
            
        return category_choices
        
    @woa.command(name="trivia_settings", description="Edit your trivia settings")
    @app_commands.describe(
        category="The category you want for trivia",
        answer_period="Time (in seconds) before the answer is shown",
        difficulty="Difficulty for the questions.",
        answer_display="How answers should be displayed",
        mode= "Whether you want it competitive or solo.",
        question_number="Number of questions. (Max 50)"
    )
    @app_commands.autocomplete(category=trivia_category_autocomplete)
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="Easy", value="easy"),
            app_commands.Choice(name="Medium", value="medium"),
            app_commands.Choice(name="Hard", value="hard")
        ],
        answer_display=[
            app_commands.Choice(name="Multiple Choice", value="choices"),
            app_commands.Choice(name="Letter Hint", value="hint"),
            app_commands.Choice(name="No Answer Shown", value="none")
        ],
        mode=[
            app_commands.Choice(name="Solo", value="solo"),
            app_commands.Choice(name="Competitive", value="competitive")
        ]
    )
    async def trivia_settings(
        self,
        interaction: discord.Interaction,
        category: str = None,
        answer_period: int = None,
        difficulty: str = None,
        answer_display: str = None,
        mode: str = None,
        question_number:int=None
    ):
        if not category and not answer_period and not difficulty and not answer_display and not mode and not question_number:
            return await interaction.response.send_message("Please choose one of the settings to alter.", ephemeral=True)

        user_id = str(interaction.user.id)
        self.user_trivia_settings.setdefault(user_id, {"category": "9", "answer_period": 30, "difficulty": "easy", "answer_display": "choices", "question_number": 10})

        response_lines = []

        valid_ids = {str(cat["id"]) for cat in trivia_categories}
        if category:
            if category not in valid_ids:
                response_lines.append("📚 Category could not be updated, because the category typed wasn't an accepted category.")
            else:
                self.user_trivia_settings[user_id]["category"] = category
                name = next(c["name"] for c in trivia_categories if str(c["id"]) == category)
                response_lines.append(f"📚 Category set to **{name}**.")

        if difficulty:
            self.user_trivia_settings[user_id]["difficulty"] = difficulty
            response_lines.append(f"🎯 Difficulty set to **{difficulty.title()}**.")

        if answer_display:
            self.user_trivia_settings[user_id]["answer_display"] = answer_display
            response_lines.append(f"👁️ Answer display mode set to **{answer_display}**.")

        if answer_period:
            self.user_trivia_settings[user_id]["answer_period"] = answer_period
            response_lines.append(f"⏱️ Answer delay set to **{answer_period} seconds**.")
        
        if mode:
            self.user_trivia_settings[user_id]["mode"] = mode
            response_lines.append(f"🎮 Mode set to **{mode.title()}**.")
        
        if question_number:
            if question_number > 50 or question_number < 0:
                response_lines.append("❔Unable to edit number of questions. Must be a number 1-50.")
            else:
                self.user_trivia_settings[user_id]["question_number"] = question_number
                response_lines.append(f"❔ Number of questions set to **{question_number}**.")

        await interaction.response.send_message("\n".join(response_lines))


    @commands.command(name="wtrivia")
    async def trivia(self, ctx):
        """Start a multi-question trivia match."""
        user_id = str(ctx.author.id)
        settings = self.user_trivia_settings.get(user_id, {})

        category = settings.get("category", "9")
        difficulty = settings.get("difficulty", "easy")
        delay = settings.get("answer_period", 30)
        display = settings.get("answer_display", "choices")
        mode = settings.get("mode", "competitive")
        total_questions = settings.get("question_number", 10)
        score = {}

        def generate_hint(answer: str):
            words = answer.split()
            if not words:
                return "?"
            hint = " ".join(word[0] if word else "_" for word in words)
            return f"{len(words)} word{'s' if len(words) > 1 else ''}:\n{hint}"

        url = (
            f"https://opentdb.com/api.php?amount={total_questions}"
            f"&category={category}&difficulty={difficulty}&type=multiple&encode=url3986"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        if data.get("response_code") != 0 or "results" not in data:
            await ctx.send("⚠️ Trivia API error: Could not fetch enough questions. Try again later.")
            return

        questions = data["results"]

        for round_num, question_data in enumerate(questions, start=1):
            # Unescape question/answers
            question = html.unescape(urllib.parse.unquote(question_data["question"]))
            correct = html.unescape(urllib.parse.unquote(question_data["correct_answer"]))
            incorrect = [
                html.unescape(urllib.parse.unquote(ans))
                for ans in question_data["incorrect_answers"]
            ]
            options = incorrect + [correct]
            random.shuffle(options)

            option_letters = ["A", "B", "C", "D"]
            option_map = dict(zip(option_letters, options))
            correct_letter = next(k for k, v in option_map.items() if v == correct)

            embed = discord.Embed(
                title=f"Question {round_num}/{total_questions} ({mode.title()} Mode)",
                description=question,
                color=discord.Color.teal()
            )

            # If question contains "following", force display of choices
            force_choices = "following" in question.lower()
            actual_display = "choices" if force_choices else display

            if actual_display == "choices":
                formatted = "\n".join([f"{l}. {o}" for l, o in option_map.items()])
                embed.add_field(name="Options", value=formatted)
            elif actual_display == "hint":
                embed.add_field(name="Hint", value=generate_hint(correct))
            # else: "none"

            await ctx.send(embed=embed)

            def check(m):
                if m.channel != ctx.channel:
                    return False
                content = m.content.lower().strip()
                is_correct = content == correct.lower() or content == correct_letter.lower()
                is_stop = content == "stop" and m.author == ctx.author
                if mode == "solo":
                    return m.author == ctx.author and (is_correct or is_stop)
                return is_correct or is_stop

            try:
                winner = await self.bot.wait_for("message", check=check, timeout=delay)
                if winner.content.lower().strip() == "stop" and winner.author == ctx.author:
                    await ctx.send("🛑 Trivia stopped by the game owner.")
                    return
                score[winner.author] = score.get(winner.author, 0) + 1
                await ctx.send(f"🎉 {winner.author.mention} got it right! The answer was: **{correct}**")
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time’s up! The correct answer was: **{correct}**")

        if not score:
            await ctx.send("No one scored this round. Better luck next time!")
        else:
            sorted_scores = sorted(score.items(), key=lambda x: x[1], reverse=True)
            results = "\n".join([f"{user.mention}: {points} point(s)" for user, points in sorted_scores])
            winner = sorted_scores[0][0]
            await ctx.send(f"🏁 Trivia over! The winner is {winner.mention}!\n\n**Final Scores:**\n{results}")

    @woa.command(name="view_triv_settings", description="View your current trivia settings.")
    async def view_triv_settings(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        settings = self.user_trivia_settings.get(user_id)

        if not settings:
            return await interaction.response.send_message("You have no trivia settings saved.", ephemeral=True)

        category_name = next((c["name"] for c in trivia_categories if str(c["id"]) == settings.get("category", "9")), "General Knowledge")
        difficulty = settings.get("difficulty", "easy").title()
        answer_display = settings.get("answer_display", "choices").replace("choices", "Multiple Choice").replace("hint", "Letter Hint").replace("none", "No Answer Shown")
        mode = settings.get("mode", "competitive").title()
        answer_period = settings.get("answer_period", 30)
        question_number = settings.get("question_number", 10)

        embed = discord.Embed(title="Your Trivia Settings", color=discord.Color.gold())
        embed.add_field(name="📚 Category", value=category_name, inline=False)
        embed.add_field(name="🎯 Difficulty", value=difficulty, inline=True)
        embed.add_field(name="👁️ Answer Display", value=answer_display, inline=True)
        embed.add_field(name="🎮 Mode", value=mode, inline=True)
        embed.add_field(name="⏱️ Answer Delay", value=f"{answer_period} seconds", inline=True)
        embed.add_field(name="❔ Number of Questions", value=str(question_number), inline=True)

        await interaction.response.send_message(embed=embed)

    async def game_category_autocomplete(self, interaction:discord.Interaction, current:str):
        return [
            app_commands.Choice(name=category, value=category)
            for category in game_categories
            if current.lower() in category.lower()
        ]


    @woa.command(name="freetogame", description="Get a free to play game.")
    @app_commands.describe(platform="The platform to see games for.", category="The type of category for the games to display.")
    @app_commands.choices(platform=[
        app_commands.Choice(name="PC", value="pc"),
        app_commands.Choice(name="Browser", value="browser")
    ])
    @app_commands.autocomplete(category=game_category_autocomplete)
    async def freetogame(self, interaction:discord.Interaction, platform: str = "pc", category:str=None):
        """Get a random free-to-play game for the specified platform (default: PC)."""
        valid_platforms = ["pc", "browser"]
        if platform.lower() not in valid_platforms:
            return await interaction.response.send_message(f"❌ Invalid platform. Choose from: {', '.join(valid_platforms)}")

        url = f"https://www.freetogame.com/api/games?platform={platform.lower()}{'&category=' + category if category else ''}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await interaction.response.send_message("Failed to fetch game data from FreeToGame API.")
                data = await resp.json()

        if not data:
            return await interaction.response.send_message("No games found for the specified platform.")

        game = random.choice(data)

        embed = discord.Embed(
            title=game.get("title"),
            url=game.get("game_url"),
            description=game.get("short_description"),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=game.get("thumbnail"))
        embed.add_field(name="Genre", value=game.get("genre"), inline=True)
        embed.add_field(name="Platform", value=game.get("platform"), inline=True)
        embed.add_field(name="Publisher", value=game.get("publisher"), inline=True)
        embed.add_field(name="Developer", value=game.get("developer"), inline=True)
        embed.set_footer(text=f"Release Date: {game.get('release_date')}")

        await interaction.response.send_message(embed=embed)
