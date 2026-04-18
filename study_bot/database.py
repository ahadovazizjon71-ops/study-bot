import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "study_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Active sessions: only 1 active session allowed at a time globally
        await db.execute("CREATE TABLE IF NOT EXISTS session_state (id INTEGER PRIMARY KEY, is_active INTEGER, start_date DATE, day_count INTEGER)")
        # User current study start
        await db.execute("CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY, username TEXT, join_time TIMESTAMP)")
        # History
        await db.execute("CREATE TABLE IF NOT EXISTS study_logs (user_id INTEGER, username TEXT, duration INTEGER, date DATE, day_num INTEGER)")
        
        # Initialize session state if empty
        async with db.execute("SELECT COUNT(*) FROM session_state") as cur:
            if (await cur.fetchone())[0] == 0:
                await db.execute("INSERT INTO session_state (id, is_active, day_count) VALUES (1, 0, 0)")
        await db.commit()

async def toggle_session(active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        if active:
            await db.execute("UPDATE session_state SET is_active = 1, day_count = day_count + 1, start_date = ?", (datetime.now().date(),))
            await db.execute("DELETE FROM active_users") # Clear previous stale joins
        else:
            await db.execute("UPDATE session_state SET is_active = 0")
        await db.commit()

async def get_session_info():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_active, day_count, start_date FROM session_state WHERE id = 1") as cur:
            return await cur.fetchone()

async def add_user_to_session(user_id, username):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO active_users VALUES (?, ?, ?)", (user_id, username, datetime.now()))
        await db.commit()

async def remove_user_from_session(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT username, join_time FROM active_users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if not row: return None
            
            username, join_time = row[0], datetime.fromisoformat(row[1])
            duration = int((datetime.now() - join_time).total_seconds())
            
            await db.execute("DELETE FROM active_users WHERE user_id = ?", (user_id,))
            
            if duration >= 3000: # 50 mins
                state = await get_session_info()
                await db.execute("INSERT INTO study_logs VALUES (?, ?, ?, ?, ?)", 
                               (user_id, username, duration, datetime.now().date(), state[1]))
            await db.commit()
            return duration

async def get_leaderboard(is_weekly=False):
    async with aiosqlite.connect(DB_PATH) as db:
        if is_weekly:
            since = datetime.now().date() - timedelta(days=7)
            query = "SELECT username, SUM(duration) as total FROM study_logs WHERE date >= ? GROUP BY user_id ORDER BY total DESC"
            params = (since,)
        else:
            query = "SELECT username, SUM(duration) as total FROM study_logs WHERE date = ? GROUP BY user_id ORDER BY total DESC"
            params = (datetime.now().date(),)
            
        async with db.execute(query, params) as cur:
            return await cur.fetchall()

async def reset_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_users")
        await db.execute("DELETE FROM study_logs")
        await db.execute("UPDATE session_state SET is_active = 0, day_count = 0")
        await db.commit()