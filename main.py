import os
import time
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
import yt_dlp

# --- CREDENTIALS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8816078528:AAHdxpOtiknmkHOvH9dMnE6kin9cgJnhMrg")
API_ID = int(os.environ.get("API_ID", "26585721"))
API_HASH = os.environ.get("API_HASH", "4887f511028d113e5f11d0e6fc583916")

# Health Check Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Active")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Pyrogram Client with Increased Workers for Speed Boost
app = Client(
    "big_file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8  # High concurrency for faster uploads
)

# Optimized Upload Progress Bar (Interval set to 4 sec to avoid Telegram flood limits)
async def upload_progress(current, total, status_msg, start_time):
    now = time.time()
    if not hasattr(upload_progress, "last_update"):
        upload_progress.last_update = 0
        
    if (now - upload_progress.last_update) > 4 or current == total:
        upload_progress.last_update = now
        percentage = current * 100 / total
        elapsed = now - start_time
        speed = (current / (1024 * 1024)) / elapsed if elapsed > 0 else 0
        uploaded_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        try:
            await status_msg.edit_text(
                f"⚡ **Fast Uploading to Telegram...**\n\n"
                f"📊 **Progress:** {percentage:.1f}%\n"
                f"💾 **Size:** {uploaded_mb:.1f} MB / {total_mb:.1f} MB\n"
                f"🚀 **Speed:** {speed:.2f} MB/s"
            )
        except Exception:
            pass

# Helper function to fix and convert WebP thumbnails to JPG for Telegram
def fix_thumbnail(thumb_file):
    if not thumb_file or not os.path.exists(thumb_file):
        return None
    try:
        jpg_thumb = f"{os.path.splitext(thumb_file)[0]}_fixed.jpg"
        im = Image.open(thumb_file)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(jpg_thumb, "JPEG")
        return jpg_thumb
    except Exception:
        return thumb_file

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("⚡ **High-Speed Downloader Bot Ready!**\n\nVideo link bhejin, fast speed aur thumbnail ke sath upload ho jayegi.")

@app.on_message(filters.text & ~filters.command(["start"]))
async def download_and_upload(client: Client, message: Message):
    url = message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.reply_text("❌ Kripya sahi Video URL bhejin.")
        return

    status_msg = await message.reply_text("⏳ Processing URL & High-Speed Engines...")
    base_name = f"video_{message.id}"
    video_path = f"{base_name}.mp4"

    # High Speed & Performance Download Settings
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': video_path,
        'writethumbnail': True,
        'outtmpl': {'thumbnail': base_name},
        'quiet': True,
        'concurrent_fragment_downloads': 8, # Multi-fragment parallel download for HLS/M3U8 streams
        'nocheckcertificate': True,
        'buffersize': 1024 * 1024 * 16, # 16MB Buffer Size Boost
    }

    try:
        await status_msg.edit_text("🚀 **Downloading at Max Speed...**")

        video_info = {}

        def do_download():
            nonlocal video_info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=True)

        await asyncio.to_thread(do_download)

        # Locate downloaded thumbnail
        raw_thumb = None
        for ext in ['.jpg', '.webp', '.png']:
            p_thumb = f"{base_name}{ext}"
            if os.path.exists(p_thumb):
                raw_thumb = p_thumb
                break

        # Convert/Fix thumbnail for fast Telegram preview
        final_thumb = fix_thumbnail(raw_thumb) if raw_thumb else None

        if os.path.exists(video_path):
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

            if file_size_mb > 2000:
                await status_msg.edit_text(f"❌ File size ({file_size_mb:.1f}MB) 2GB Telegram limit se badi hai.")
                for f in [video_path, raw_thumb, final_thumb]:
                    if f and os.path.exists(f): os.remove(f)
                return

            await status_msg.edit_text("⬆️ **Initiating Turbo Upload...**")
            start_time = time.time()

            duration = int(video_info.get('duration', 0)) if video_info else 0
            width = int(video_info.get('width', 0)) if video_info else 0
            height = int(video_info.get('height', 0)) if video_info else 0

            # Telegram Upload with tgcrypto & parallel workers
            await client.send_video(
                chat_id=message.chat.id,
                video=video_path,
                thumb=final_thumb if (final_thumb and os.path.exists(final_thumb)) else None,
                duration=duration,
                width=width,
                height=height,
                caption=f"🎥 **Video Uploaded!**\n💾 **Size:** {file_size_mb:.1f} MB",
                supports_streaming=True,
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )

            # Cleanup Files
            for f in [video_path, raw_thumb, final_thumb]:
                if f and os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Download fail ho gaya.")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Error:** {str(e)}")
        for f in [video_path, raw_thumb, final_thumb]:
            if f and os.path.exists(f): 
                try: os.remove(f)
                except: pass

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Turbo Downloader Bot Active...")
    app.run()
