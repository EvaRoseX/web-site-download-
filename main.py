import os
import time
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8816078528:AAHdxpOtiknmkHOvH9dMnE6kin9cgJnhMrg")
API_ID = int(os.environ.get("API_ID", "26585721"))
API_HASH = os.environ.get("API_HASH", "4887f511028d113e5f11d0e6fc583916")

# Dummy Web Server (Render Web Service Active Rakhne Ke Liye)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Active and Running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Pyrogram Client Setup
app = Client("big_file_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Live Progress Bar Handler for Uploading
async def upload_progress(current, total, status_msg, start_time):
    now = time.time()
    # Har 3 second mein status message update karein
    if not hasattr(upload_progress, "last_update"):
        upload_progress.last_update = 0
        
    if (now - upload_progress.last_update) > 3 or current == total:
        upload_progress.last_update = now
        percentage = current * 100 / total
        speed = current / (now - start_time) / (1024 * 1024)  # MB/s
        uploaded_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        try:
            await status_msg.edit_text(
                f"⬆️ **Uploading to Telegram...**\n\n"
                f"📊 **Progress:** {percentage:.1f}%\n"
                f"💾 **Size:** {uploaded_mb:.1f} MB / {total_mb:.1f} MB\n"
                f"⚡ **Speed:** {speed:.2f} MB/s"
            )
        except Exception:
            pass

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("👋 **Hello!**\n\nKoi bhi video link bhejo, main 2GB tak ki files Telegram par fast speed aur live progress ke sath upload kar doonga.")

@app.on_message(filters.text & ~filters.command(["start"]))
async def download_and_upload(client: Client, message: Message):
    url = message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.reply_text("❌ Kripya sahi Video URL (http:// ya https://) bhejin.")
        return

    status_msg = await message.reply_text("⏳ Processing link...")
    filename = f"video_{message.id}.mp4"

    # Best Quality Download Settings
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
    }

    try:
        await status_msg.edit_text("⬇️ **Downloading video to server...**")

        # Async Download Execution
        def do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await asyncio.to_thread(do_download)

        if os.path.exists(filename):
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)

            # Telegram 2GB Limit Check
            if file_size_mb > 2000:
                await status_msg.edit_text(f"❌ File size ({file_size_mb:.1f}MB) limit se bada hai (Max 2GB allowed).")
                os.remove(filename)
                return

            await status_msg.edit_text("⬆️ **Starting Telegram Upload...**")
            start_time = time.time()

            await client.send_video(
                chat_id=message.chat.id,
                video=filename,
                caption=f"🎥 **Video Uploaded Successfully!**\n💾 **Size:** {file_size_mb:.1f} MB",
                supports_streaming=True,
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )

            # Clean up server disk space
            os.remove(filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Download karne mein dikkat aayi.")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Error:** {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    # Render web service port bind
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot starting with Pyrogram...")
    app.run()
