from __future__ import annotations

from redbot.core import commands
from redbot.core.data_manager import cog_data_path
import discord
from discord import app_commands
from discord.ext import tasks

import aiosqlite
from pathlib import Path
import json
import time




class Goals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db: aiosqlite.Connection | None = None
        self.db_path: Path = cog_data_path(self) / "goals.db"
    
    async def cog_load(self) -> None:
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute("PRAGMA foreign_keys = ON;")
        await self._create_tables()
        await self.db.commit()
    
    async def cog_unload(self) -> None:
        if self.db is not None:
            await self.db.close()
            self.db = None

    async def _create_tables(self) -> None:
        assert self.db is not None

        await self.db.execute(
            """

            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                timezone    TEXT DEFAULT 'America/Los_Angeles',
                created_at  INTEGER NOT NULL
            );
            """
        )

        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                goal_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id    INTEGER NOT NULL,
                title       TEXT NOT NULL,
                goal_type   TEXT NOT NULL,  -- 'quantity', 'count', 'binary', 'cutoff'
                period      TEXT NOT NULL, -- 'daily', 'weekly', 'monthly'
                target      REAL, -- e.g., 30 minutes, 4 sessions, 3000 words
                unit        TEXT, -- 'min', 'sessions', 'words', 'miles', etc.
                min_attempt REAL DEFAULT 0, -- e.g., 10 min before it "counts"
                daily_cap   REAL, --e.g., cap effective minutes/day (anti-binge)
                active      INTEGER DEFAULT 1,
                meta_json   TEXT DEFAULT '{}',
                created_at  INTEGER NOT NULL
            );
            """
        )

        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_goals_owner_id ON goals (owner_id);")

        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                checkin_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id     INTEGER NOT NULL REFERENCES goals(goal_id) ON DELETE CASCADE,
                owner_id    INTEGER NOT NULL,
                day         TEXT NOT NULL, -- 'YYYY-MM-DD' in user's local time
                value       REAL NOT NULL, -- minutes/words/etc OR 1 for binary done
                note        TEXT,
                meta_json   TEXT DEFAULT '{}', --e.g., {"mode":"run"} or {"slept_at":"22:14"}
                created_at  INTEGER NOT NULL
            );

            """
        )

        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_checkins_goal_day ON checkins(goal_id, day);")
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_checkins_owner_day ON checkins(owner_id, day);")

        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS partners(
                user_id     INTEGER NOT NULL,
                partner_id  INTEGER NOT NULL,
                share_level TEXT DEFAULT 'summary', -- 'summary' vs 'details'
                created_at  INTEGER NOT NULL,
                PRIMARY KEY (user_id, partner_id)
            );
            """
        )

        await self.db.execute(
            """
            
            """
        )
    

    async def ensure_user(self, user_id: int) -> None:
        assert self.db is not None
        now = int(time.time())
        await self.db.execute(
            "INSERT OR IGNORE INTO users(user_id, created_at) VALUES (?, ?);",
            (user_id, now),
        )
        await self.db.commit()