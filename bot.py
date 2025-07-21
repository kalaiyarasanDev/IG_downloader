import os
import asyncio
from dotenv import load_dotenv
import nest_asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from downloader import get_available_formats, download_media
from datetime import datetime

# 🧠 Patch event loop for compatibility (especially in IDEs)
nest_asyncio.apply()

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
user_sessions = {}
DOWNLOAD_DIR = "downloads"
FILE_LIFETIME_SECONDS = 86400  # 24 hours

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# 🧹 Cleanup old files every hour
async def cleanup_downloads():
    while True:
        now = datetime.now().timestamp()
        for fname in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isfile(fpath):
                age = now - os.path.getmtime(fpath)
                if age > FILE_LIFETIME_SECONDS:
                    os.remove(fpath)
        await asyncio.sleep(3600)

# 👋 /start command
async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("👋 Send a public Instagram post or reel link to begin downloading.")

# 📌 /help command
async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "📌 Send a public Instagram reel/post URL.\n"
            "🎞️ Choose your preferred video quality.\n"
            "📤 Video will be sent right here.\n"
            "🧹 Downloads auto-delete after 24 hours.\n"
            "🚀 Fast download — no login required!"
        )

# 🔗 Handle Instagram link
async def handle_url(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        url = update.message.text.strip()

        user_sessions.pop(user_id, None)
        user_sessions[user_id] = url

        await update.message.reply_text("🔍 Looking up available video formats…")

        try:
            video_opts = get_available_formats(url)
            buttons = [
                [InlineKeyboardButton(f"🎞️ {label}", callback_data=fmt_id)]
                for fmt_id, label in video_opts
            ]

            if buttons:
                await update.message.reply_text("🎛️ Choose video quality:", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await update.message.reply_text("⚠️ No video formats found for this link.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error while fetching formats: {e}")

# 🎞️ Download and send selected video
async def handle_format_selection(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message:
        user_id = query.from_user.id
        url = user_sessions.get(user_id)
        format_id = query.data

        if not url:
            await query.message.reply_text("⚠️ Session expired. Please send the Instagram link again.")
            return

        await query.edit_message_text("⏳ Downloading video…")

        try:
            file_path = download_media(url, format_id, user_id)
            if not file_path:
                await query.message.reply_text("⚠️ File not found. Download may have failed.")
                return

            with open(file_path, "rb") as f:
                await query.message.reply_video(InputFile(f))

            user_sessions.pop(user_id, None)
        except Exception as e:
            await query.message.reply_text(f"❌ Failed to send video: {e}")

# ✅ Main async block that launches the bot and cleanup task
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_format_selection))

    # Launch background cleanup task safely inside event loop
    asyncio.create_task(cleanup_downloads())

    print("🚀 Bot is running with auto-cleanup enabled.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())