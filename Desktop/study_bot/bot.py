import asyncio
import secrets
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

import config
import database as db

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def format_time(sec):
    m, s = divmod(sec, 60)
    return f"{m}m {s:02d}s"

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Bot ishlayapti ✅")

@dp.message(Command("join"))
async def join(msg: types.Message):
    user = msg.from_user
    username = f"@{user.username}" if user.username else user.full_name

    if await db.is_user_in_session(user.id):
        return await msg.answer("⚠️ Siz allaqachon sessiyadasiz!")

    title = secrets.choice(config.TITLES)

    await db.user_join(user.id, username, title)

    await msg.answer(
        f"✅ Sessiyaga qo‘shildingiz!\n"
        f"🎯 Study Nickname: {title}\n"
        f"👤 {username}"
    )

@dp.message(Command("leave"))
async def leave(msg: types.Message):
    duration = await db.user_leave(msg.from_user.id)

    if duration is None:
        return await msg.answer("❌ Siz sessiyada emassiz")

    text = f"⏱ {format_time(duration)}\n"
    text += "✅ Saqlandi!" if duration >= 3000 else "⚠️ 50 min yetmadi"

    await msg.answer(text)

@dp.message(Command("day"))
async def day(msg: types.Message):
    data = await db.get_daily()

    text = "📊 DAILY 👑\n\n"
    for i, (user, sec, title) in enumerate(data, 1):
        text += f"{i}. {user} — {format_time(sec)} — {title}\n"

    await msg.answer(text)

@dp.message(Command("weekly"))
async def weekly(msg: types.Message):
    data = await db.get_weekly()

    text = "🗓 WEEKLY 🏆\n\n"
    for i, (user, sec, title) in enumerate(data, 1):
        text += f"{i}. {user} — {format_time(sec)} — {title}\n"

    await msg.answer(text)

async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())