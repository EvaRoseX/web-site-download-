import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram Bot Token (Render Environment Variables se aayega)
TOKEN = os.environ.get("BOT_TOKEN", "8816078528:AAHdxpOtiknmkHOvH9dMnE6kin9cgJnhMrg")

# Render Web Service Health Check Fix (Dummy HTTP Server)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Video URL bhejo, main download karke bhej doonga.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Kripya sahi Video URL bhejin.")
        return

    msg = await update.message.reply_text("Video process ho rha hai, please wait...")

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
            os.remove("video.mp4")
            await msg.delete()
        else:
            await msg.edit_text("Video download karne mein dikkat aayi.")

    except Exception as e:
        await msg.edit_text(f"Error: ({str(e)})")
        if os.path.exists("video.mp4"):
            os.remove("video.mp4")

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN nahi mila!")
        return

    # Background Thread mein Dummy HTTP Server start karein (Render Port Bind ke liye)
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot chalu ho raha hai...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
