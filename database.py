import aiosqlite
import os
import logging

DB_PATH = "tournament_bot.db"

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Veritabanı tablolarını ilklendirir."""
        async with aiosqlite.connect(self.db_path) as db:
            # Turnuvalar tablosu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    max_players INTEGER NOT NULL,
                    status TEXT DEFAULT 'registration', -- registration, active, completed, cancelled
                    current_round INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Oyuncu/Katılımcı tablosu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    status TEXT DEFAULT 'active', -- active, waitlist, eliminated, winner
                    waitlist_order INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE
                )
            """)

            # Maçlar tablosu (1v1)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    round INTEGER NOT NULL,
                    match_number INTEGER NOT NULL,
                    player1_id INTEGER,
                    player2_id INTEGER,
                    winner_id INTEGER,
                    temp_voice_id INTEGER,
                    status TEXT DEFAULT 'pending', -- pending, completed
                    FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE
                )
            """)

            # Ticket tablosu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'open', -- open, closed
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Guard Ayarları tablosu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guard_settings (
                    guild_id INTEGER PRIMARY KEY,
                    anti_link INTEGER DEFAULT 1,
                    anti_spam INTEGER DEFAULT 1,
                    word_filter INTEGER DEFAULT 1,
                    log_channel_id INTEGER
                )
            """)

            # Kanal & Sunucu Yapılandırması tablosu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    guild_id INTEGER PRIMARY KEY,
                    results_channel_id INTEGER,
                    waitlist_channel_id INTEGER,
                    ticket_category_id INTEGER,
                    auto_role_id INTEGER
                )
            """)

            # Oyuncu İstatistikleri tablosu
            await db.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    user_id INTEGER PRIMARY KEY,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    tournaments_won INTEGER DEFAULT 0
                )
            """)

            await db.commit()

    # --- TURNUVA İŞLEMLERİ ---
    async def create_tournament(self, guild_id: int, name: str, max_players: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tournaments (guild_id, name, max_players) VALUES (?, ?, ?)",
                (guild_id, name, max_players)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_active_tournament(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tournaments WHERE guild_id = ? AND status IN ('registration', 'active') ORDER BY id DESC LIMIT 1",
                (guild_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def update_tournament_status(self, tournament_id: int, status: str, current_round: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            if current_round is not None:
                await db.execute(
                    "UPDATE tournaments SET status = ?, current_round = ? WHERE id = ?",
                    (status, current_round, tournament_id)
                )
            else:
                await db.execute(
                    "UPDATE tournaments SET status = ? WHERE id = ?",
                    (status, tournament_id)
                )
            await db.commit()

    # --- KATILIMCI & WAITLIST İŞLEMLERİ ---
    async def add_participant(self, tournament_id: int, user_id: int, user_name: str, status: str = 'active', waitlist_order: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO participants (tournament_id, user_id, user_name, status, waitlist_order) VALUES (?, ?, ?, ?, ?)",
                (tournament_id, user_id, user_name, status, waitlist_order)
            )
            await db.commit()

    async def get_participants(self, tournament_id: int, status: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                async with db.execute(
                    "SELECT * FROM participants WHERE tournament_id = ? AND status = ? ORDER BY waitlist_order ASC, id ASC",
                    (tournament_id, status)
                ) as cursor:
                    return await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM participants WHERE tournament_id = ? ORDER BY id ASC",
                    (tournament_id,)
                ) as cursor:
                    return await cursor.fetchall()

    async def get_participant(self, tournament_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM participants WHERE tournament_id = ? AND user_id = ?",
                (tournament_id, user_id)
            ) as cursor:
                return await cursor.fetchone()

    async def remove_participant(self, tournament_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM participants WHERE tournament_id = ? AND user_id = ?",
                (tournament_id, user_id)
            )
            await db.commit()

    async def promote_first_waitlist(self, tournament_id: int):
        """Yedek listesindeki ilk kişiyi (Waitlist #1) asil kadroya taşır."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM participants WHERE tournament_id = ? AND status = 'waitlist' ORDER BY waitlist_order ASC LIMIT 1",
                (tournament_id,)
            ) as cursor:
                first_waitlist = await cursor.fetchone()

            if first_waitlist:
                await db.execute(
                    "UPDATE participants SET status = 'active', waitlist_order = 0 WHERE id = ?",
                    (first_waitlist['id'],)
                )
                await db.commit()
                return first_waitlist
            return None

    # --- MAÇ İŞLEMLERİ ---
    async def create_match(self, tournament_id: int, round_num: int, match_num: int, player1_id: int, player2_id: int, temp_voice_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO matches (tournament_id, round, match_number, player1_id, player2_id, temp_voice_id) VALUES (?, ?, ?, ?, ?, ?)",
                (tournament_id, round_num, match_num, player1_id, player2_id, temp_voice_id)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_matches_for_round(self, tournament_id: int, round_num: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM matches WHERE tournament_id = ? AND round = ? ORDER BY match_number ASC",
                (tournament_id, round_num)
            ) as cursor:
                return await cursor.fetchall()

    async def get_match_by_id(self, match_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)) as cursor:
                return await cursor.fetchone()

    async def set_match_winner(self, match_id: int, winner_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE matches SET winner_id = ?, status = 'completed' WHERE id = ?",
                (winner_id, match_id)
            )
            await db.commit()

            # Maçtan elenen oyuncuyu belirle ve participant durumunu güncelle
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)) as cursor:
                match = await cursor.fetchone()
                if match:
                    loser_id = match['player2_id'] if match['player1_id'] == winner_id else match['player1_id']
                    if loser_id:
                        await db.execute(
                            "UPDATE participants SET status = 'eliminated' WHERE tournament_id = ? AND user_id = ?",
                            (match['tournament_id'], loser_id)
                        )
                        # İstatistik güncelleme
                        await self.record_match_stats(winner_id, loser_id)
            await db.commit()

    async def update_match_voice(self, match_id: int, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE matches SET temp_voice_id = ? WHERE id = ?", (channel_id, match_id))
            await db.commit()

    # --- İSTATİSTİK İŞLEMLERİ ---
    async def record_match_stats(self, winner_id: int, loser_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO player_stats (user_id, wins, losses) VALUES (?, 1, 0)
                ON CONFLICT(user_id) DO UPDATE SET wins = wins + 1
            """, (winner_id,))
            await db.execute("""
                INSERT INTO player_stats (user_id, wins, losses) VALUES (?, 0, 1)
                ON CONFLICT(user_id) DO UPDATE SET losses = losses + 1
            """, (loser_id,))
            await db.commit()

    async def record_tournament_win(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO player_stats (user_id, tournaments_won) VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET tournaments_won = tournaments_won + 1
            """, (user_id,))
            await db.commit()

    async def get_top_players(self, limit: int = 10):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM player_stats ORDER BY tournaments_won DESC, wins DESC LIMIT ?",
                (limit,)
            ) as cursor:
                return await cursor.fetchall()

    # --- TİCKET & GUARD & CONFIG ---
    async def create_ticket(self, guild_id: int, user_id: int, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO tickets (guild_id, user_id, channel_id) VALUES (?, ?, ?)",
                (guild_id, user_id, channel_id)
            )
            await db.commit()

    async def close_ticket(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel_id,))
            await db.commit()

    async def get_guard_settings(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM guard_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                res = await cursor.fetchone()
                if not res:
                    await db.execute("INSERT INTO guard_settings (guild_id) VALUES (?)", (guild_id,))
                    await db.commit()
                    async with db.execute("SELECT * FROM guard_settings WHERE guild_id = ?", (guild_id,)) as c2:
                        return await c2.fetchone()
                return res

    async def update_guard_settings(self, guild_id: int, **kwargs):
        async with aiosqlite.connect(self.db_path) as db:
            for key, val in kwargs.items():
                await db.execute(f"UPDATE guard_settings SET {key} = ? WHERE guild_id = ?", (val, guild_id))
            await db.commit()

    async def get_config(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM bot_config WHERE guild_id = ?", (guild_id,)) as cursor:
                res = await cursor.fetchone()
                if not res:
                    await db.execute("INSERT INTO bot_config (guild_id) VALUES (?)", (guild_id,))
                    await db.commit()
                    async with db.execute("SELECT * FROM bot_config WHERE guild_id = ?", (guild_id,)) as c2:
                        return await c2.fetchone()
                return res

    async def set_config(self, guild_id: int, **kwargs):
        async with aiosqlite.connect(self.db_path) as db:
            for key, val in kwargs.items():
                await db.execute(f"UPDATE bot_config SET {key} = ? WHERE guild_id = ?", (val, guild_id))
            await db.commit()
