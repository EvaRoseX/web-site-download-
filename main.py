import os
import asyncio
import time
import uuid
import re
import yt_dlp
from pyrogram import Client, filters
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ==========================================
# 1. RENDER PORT BIND FIX (Free Web Service)
# ==========================================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running Alive!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# ==========================================
# 2. TELEGRAM BOT CONFIGURATION
# ==========================================
BOT_TOKEN = "8816078528:AAHdxpOtiknmkHOvH9dMnE6kin9cgJnhMrg"
API_ID = 26585721
API_HASH = "4887f511028d113e5f11d0e6fc583916"

app = Client(
    "telegram_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8
)

@app.on_message(filters.command(["start", "help"]))
async def send_welcome(client, message):
    await message.reply("👋 Namaste! Link bhejiye, main video upload kar dunga.")

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def process_video_link(client, message):
    url = message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        await message.reply("❌ Kripya valid link bhejen.")
        return

    status_msg = await message.reply("⏳ Link process ho raha hai...")
    
    unique_id = str(uuid.uuid4())[:8]
    custom_filename = f"video_{unique_id}.%(ext)s"

    # Primary YT-DLP Options
    ydl_opts = {
        'outtmpl': custom_filename,
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }

    file_path = None

    try:
        await status_msg.edit_text("📥 **Server par download ho raha hai...**")
        
        loop = asyncio.get_running_loop()

        def download():
            try:
                # Attempt 1: Standard Extraction
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        return ydl.prepare_filename(info)
            except Exception:
                # Attempt 2: Fallback to Generic Extractor (Bypasses broken site-specific extractor)
                fallback_opts = ydl_opts.copy()
                fallback_opts['force_generic_extractor'] = True
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        return ydl.prepare_filename(info)
            return None

        file_path = await loop.run_in_executor(None, download)
        
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text("❌ Is link ka extractor filhal site update ki vajah se broken hai. Dusri site ka link try karein.")
            return

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        if file_size_mb > 2000:
            await status_msg.edit_text(f"❌ File Size ({file_size_mb:.1f} MB) Telegram ki 2 GB limit se bada hai.")
            os.remove(file_path)
            return

        last_update_time = [0]

        async def upload_progress(current, total):
            now = time.time()
            if now - last_update_time[0] > 3:
                last_update_time[0] = now
                percent = (current / total) * 100
                curr_mb = current / (1024 * 1024)
                tot_mb = total / (1024 * 1024)
                try:
                    await status_msg.edit_text(
                        f"⬆️ **Uploading to Telegram...**\n\n"
                        f"📊 **Progress:** `{percent:.1f}%`\n"
                        f"📦 **Uploaded:** `{curr_mb:.1f} MB` / `{tot_mb:.1f} MB`"
                    )
                except Exception:
                    pass

        await status_msg.edit_text(f"⬆️ **Upload start ho raha hai...** ({file_size_mb:.1f} MB)")

        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            caption=f"✅ **Done!** ({file_size_mb:.1f} MB)",
            progress=upload_progress
        )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

print("🤖 Bot ready hai...")
app.run()
