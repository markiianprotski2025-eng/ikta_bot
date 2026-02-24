import asyncio
import os
import sqlite3
import re
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand

# --- НАЛАШТУВАННЯ ---
API_TOKEN = '8533004902:AAGgmlRxHw59mMel2NdjTv-8wuLCwysdrqc'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАНИХ ---
conn = sqlite3.connect("users_list.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        chat_id INTEGER, 
        user_id INTEGER, 
        username TEXT, 
        UNIQUE(chat_id, user_id)
    )
""")
conn.commit()

# Функція для реєстрації команд у меню "Menu"
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="all", description="Текнути всіх учасників групи"),
    ]
    await bot.set_my_commands(commands)

# Функція завантаження відео
def download_media(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- КОМАНДА /ALL ---
@dp.message(Command("all"))
async def cmd_all(message: types.Message):
    cursor.execute("SELECT username, user_id FROM members WHERE chat_id = ?", (message.chat.id,))
    users = cursor.fetchall()
    
    if not users:
        await message.reply("❌ База порожня. Напишіть щось у чат, щоб я вас запам'ятав.")
        return

    mentions = []
    for username, user_id in users:
        if username and username != 'None':
            mentions.append(f"@{username}")
        else:
            mentions.append(f'<a href="tg://user?id={user_id}">👤</a>')

    for i in range(0, len(mentions), 50):
        text = "🔔 <b>ЗАКЛИК УСІХ УЧАСНИКІВ:</b>\n\n" + " ".join(mentions[i:i+50])
        await message.answer(text, parse_mode="HTML")

# --- ОБРОБКА ПОВІДОМЛЕНЬ ---
@dp.message()
async def handle_everything(message: types.Message):
    # Реєструємо користувача
    if message.chat.type in ["group", "supergroup"]:
        cursor.execute("INSERT OR IGNORE INTO members VALUES (?, ?, ?)", 
                       (message.chat.id, message.from_user.id, message.from_user.username))
        conn.commit()

    # Парсинг посилань (TikTok/Instagram)
    if message.text:
        links = re.findall(r'(https?://[^\s]+)', message.text)
        for url in links:
            if "tiktok.com" in url or "instagram.com" in url:
                try:
                    print(f"🔎 Завантаження: {url}")
                    loop = asyncio.get_event_loop()
                    file_path = await loop.run_in_executor(None, download_media, url)
                    
                    if os.path.exists(file_path):
                        video_file = types.FSInputFile(file_path)
                        await message.reply_video(video=video_file)
                        os.remove(file_path)
                except Exception as e:
                    print(f"❌ Помилка завантаження: {e}")

async def main():
    # Налаштовуємо меню команд при запуску
    await set_commands(bot)
    
    print("🚀 Бот запущений. Меню команд оновлено.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зупинений.")