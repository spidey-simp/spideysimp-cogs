import discord
from redbot.core import commands
from discord.ext import tasks
import random

class StatusSet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_rotator.start()
    
    def cog_unload(self):
        self.status_rotator.cancel()

    @tasks.loop(hours=3)
    async def status_rotator(self):
        await self.bot.wait_until_ready()
        spiderman_movies = [
            # Tobey Maguire Trilogy
            "Spider-Man (2002)",
            "Spider-Man 2 (2004)",
            "Spider-Man 3 (2007)",

            # Andrew Garfield Films
            "The Amazing Spider-Man (2012)",
            "The Amazing Spider-Man 2 (2014)",

            # Tom Holland (MCU)
            "Captain America: Civil War (2016)",
            "Spider-Man: Homecoming (2017)",
            "Avengers: Infinity War (2018)",
            "Avengers: Endgame (2019)",
            "Spider-Man: Far From Home (2019)",
            "Spider-Man: No Way Home (2021)",

            # Spider-Verse Animated
            "Spider-Man: Into the Spider-Verse (2018)",
            "Spider-Man: Across the Spider-Verse (2023)",
            "Spider-Man: Beyond the Spider-Verse (TBA)"
        ]

        spiderman_shows = [
            "Spider-Man: The Animated Series (1994–1998)",
            "Spectacular Spider-Man (2008–2009)",
            "Ultimate Spider-Man (2012–2017)",
            "Spider-Man (2017–2020)",
            "Spidey and His Amazing Friends (2021– )",  # Kids-focused, but popular
            "Your Friendly Neighborhood Spider-Man (2025– )"  # Upcoming
        ]
        statuses = [
                discord.Activity(type=discord.ActivityType.watching, name="the streets of New York City"),
                discord.Activity(type=discord.ActivityType.listening, name="for trouble in Queens"),
                discord.Activity(type=discord.ActivityType.competing, name="with other applicants for an Avengers spot"),
                discord.Activity(type=discord.ActivityType.watching, name="the Daily Bugle slander me again"),
                discord.Activity(type=discord.ActivityType.listening, name="to J. Jonah Jameson call me a menace"),
                discord.Activity(type=discord.ActivityType.listening, name="to my spidey sense"),
                discord.Game(name="Spider-Man")
            ]


        rand_num = random.random()
        if rand_num < .5:
            movie_or_show = random.random()
            if movie_or_show < .1:
                status = discord.Activity(type=discord.ActivityType.watching, name=random.choice(spiderman_shows))
            else:
                status = discord.Activity(type=discord.ActivityType.watching, name=random.choice(spiderman_movies))
        else:
            status = random.choice(statuses)
            
        await self.bot.change_presence(activity=status)
            