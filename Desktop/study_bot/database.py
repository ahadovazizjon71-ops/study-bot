import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "study_persistence.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            join_time TEXT,
            title TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            duration INTEGER,
            date TEXT,
            title TEXT,
            timestamp TEXT
        )
        """)
        await db.commit()

async def is_user_in_session(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM active_sessions WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None

async def user_join(user_id, username, title):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO active_sessions VALUES (?, ?, ?, ?)",
            (user_id, username, datetime.now().isoformat(), title)
        )
        await db.commit()

async def user_leave(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT join_time, username, title FROM active_sessions WHERE user_id = ?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return None

        join_time = datetime.fromisoformat(row[0])
        username = row[1]
        title = row[2]

        duration = int((datetime.now() - join_time).total_seconds())

        await db.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))

        if duration >= 3000:
            await db.execute(
                "INSERT INTO study_logs (user_id, username, duration, date, title, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, duration, datetime.now().date().isoformat(), title, datetime.now().isoformat())
            )

        await db.commit()
        return duration

async def get_daily():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT username, SUM(duration), title
            FROM study_logs
            WHERE date = ?
            GROUP BY user_id
            ORDER BY SUM(duration) DESC
        """, (datetime.now().date().isoformat(),)) as cur:
            return await cur.fetchall()

async def get_weekly():
    async with aiosqlite.connect(DB_PATH) as db:
        since = (datetime.now().date() - timedelta(days=7)).isoformat()

        async with db.execute("""
        SELECT t1.username, t1.total,
        (SELECT title FROM study_logs t2 WHERE t2.user_id = t1.user_id ORDER BY timestamp DESC LIMIT 1)
        FROM (
            SELECT user_id, username, SUM(duration) as total
            FROM study_logs
            WHERE date >= ?
            GROUP BY user_id
        ) t1
        ORDER BY t1.total DESC
        """, (since,)) as cur:
            return await cur.fetchall()