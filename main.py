import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Direct Bot Token (Render / Local par chalane ke liye)
TOKEN = "8816078528:AAHdxpOtiknmkHOvH9dMnE6kin9cgJnhMrg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Koi bhi video URL bhejo, main use Telegram par upload kar doonga.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Kripya sahi Video URL bhejin.")
        return

    msg = await update.message.reply_text("Video process ho rha hai, please wait...")

    # Video Download Settings
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'video.mp4',
        'max_filesize': 50 * 1024 * 1024, # 50MB limit
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists("video.mp4"):
            await msg.edit_text("Uploading to Telegram...")
            with open("video.mp4", "rb") as video:
                await update.message.reply_video(video=video, caption="Here is your video!")
            os.remove("video.mp4") # File delete karein
            await msg.delete()
        else:
            await msg.edit_text("Video download karne mein koi dikkat aayi.")

    except Exception as e:
        await msg.edit_text(f"Error: Video process nahi ho paya. ({str(e)})")
        if os.path.exists("video.mp4"):
            os.remove("video.mp4")

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN nahi mila!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot chalu ho raha hai...")
    app.run_polling()

if __name__ == "__main__":
    main()
