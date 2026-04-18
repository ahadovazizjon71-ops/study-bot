import asyncio
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

import config
import database as db

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def get_session_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Join ✅", callback_data="join")
    builder.button(text="Leave ⏹", callback_data="leave")
    return builder.as_markup()

def format_duration(seconds):
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s"

def get_rank_emoji(rank):
    emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    if rank in emojis: return emojis[rank]
    
    # Generate boxed numbers for ranks 4+
    num_str = str(rank)
    mapped = "".join([chr(0xff10 + int(d)) for d in num_str]) # Full-width numbers
    return f"{rank}️⃣"

# --- Handlers ---

@dp.message(Command("startsession"))
async def start_session(message: types.Message):
    if message.from_user.id != config.ADMIN_ID: return
    
    await db.toggle_session(True)
    state = await db.get_session_info()
    
    msg = await bot.send_message(
        config.CHANNEL_ID,
        f"🚀 **Study Session #{state[1]} Boshlandi!**\n\nQuyidagi tugmalar orqali vaqtingizni hisoblang.",
        reply_markup=get_session_kb(),
        parse_mode="Markdown"
    )
    await message.answer(f"Session started. Day: {state[1]}")

@dp.message(Command("endsession"))
async def end_session(message: types.Message):
    if message.from_user.id != config.ADMIN_ID: return
    
    await db.toggle_session(False)
    await message.answer("Session ended. Buttons are now inactive.")

@dp.callback_query(F.data == "join")
async def join_callback(callback: types.CallbackQuery):
    is_active, _, _ = await db.get_session_info()
    if not is_active:
        return await callback.answer("❌ Hozirda faol sessiya yo'q!", show_alert=True)
    
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    await db.add_user_to_session(callback.from_user.id, username)
    
    title = config.TITLES[hash(str(callback.from_user.id)) % len(config.TITLES)]
    
    text = (f"✅ Sessiyaga qo‘shildingiz! Timer boshlandi.\n"
            f"🎯 Study Nickname: {title}\n"
            f"👤 Display Name: {username}")
    
    try:
        await bot.send_message(callback.from_user.id, text)
        await callback.answer("Sessiya boshlandi!")
    except TelegramBadRequest:
        await callback.answer("Botga start bosing!", show_alert=True)

@dp.callback_query(F.data == "leave")
async def leave_callback(callback: types.CallbackQuery):
    duration = await db.remove_user_from_session(callback.from_user.id)
    
    if duration is None:
        return await callback.answer("Siz sessiyada emassiz!", show_alert=True)
    
    msg = f"⏹ Sessiyadan chiqdingiz.\n⏱ Vaqtingiz: {format_duration(duration)}\n"
    msg += "✅ Saqlandi!" if duration >= 3000 else "⚠️ Saqlanmadi (min. 50 daqiqa kerak)."
    
    await bot.send_message(callback.from_user.id, msg)
    await callback.answer("Sessiya yakunlandi.")

@dp.message(Command("day"))
async def day_leaderboard(message: types.Message):
    data = await db.get_leaderboard(is_weekly=False)
    state = await db.get_session_info()
    date_str = datetime.now().strftime("%d.%m.%y (%A)")
    
    header = f"📊 LEADERBOARD — DAY {state[1]} 👑\n📅 Today — {date_str}\n\n"
    body = ""
    
    for i, (user, duration) in enumerate(data, 1):
        emoji = get_rank_emoji(i)
        title = config.TITLES[hash(user) % len(config.TITLES)]
        body += f"{emoji} {user} — {format_duration(duration)} — {title}\n"
    
    await message.answer(header + (body or "Hozircha ma'lumot yo'q."))

@dp.message(Command("weekly"))
async def weekly_leaderboard(message: types.Message):
    data = await db.get_leaderboard(is_weekly=True)
    header = "🗓 WEEKLY LEADERBOARD (7 Days) 🏆\n\n"
    body = ""
    
    for i, (user, duration) in enumerate(data, 1):
        emoji = get_rank_emoji(i)
        body += f"{emoji} {user} — {format_duration(duration)}\n"
        
    await message.answer(header + (body or "Haftalik ma'lumot yo'q."))

@dp.message(Command("reset"))
async def reset_bot(message: types.Message):
    if message.from_user.id != config.ADMIN_ID: return
    await db.reset_database()
    await message.answer("🔄 Barcha ma'lumotlar o'chirildi.")

async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(main())