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

# Dummy Web Server (Render Port Binding)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Active")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

app = Client(
    "big_file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=8
)

# --- LIVE DOWNLOAD PROGRESS HOOK ---
def yt_dlp_progress_hook(d, loop, status_msg):
    if d['status'] == 'downloading':
        now = time.time()
        # Rate limit updates to avoid Telegram flood limits (every 3 seconds)
        if not hasattr(yt_dlp_progress_hook, "last_update"):
            yt_dlp_progress_hook.last_update = 0

        if (now - yt_dlp_progress_hook.last_update) > 3:
            yt_dlp_progress_hook.last_update = now

            downloaded = d.get('downloaded_bytes', 0) / (1024 * 1024)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            total_mb = total / (1024 * 1024) if total else 0

            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', '0B/s').strip()
            eta = d.get('_eta_str', 'N/A').strip()

            text = (
                f"⬇️ **Downloading Video...**\n\n"
                f"📊 **Progress:** {percent}\n"
                f"💾 **Downloaded:** {downloaded:.1f} MB / {total_mb:.1f} MB\n"
                f"⚡ **Speed:** {speed}\n"
                f"⏳ **ETA:** {eta}"
            )

            asyncio.run_coroutine_threadsafe(
                status_msg.edit_text(text),
                loop
            )

# --- LIVE UPLOAD PROGRESS FUNCTION ---
async def upload_progress(current, total, status_msg, start_time):
    now = time.time()
    if not hasattr(upload_progress, "last_update"):
        upload_progress.last_update = 0

    if (now - upload_progress.last_update) > 3 or current == total:
        upload_progress.last_update = now
        percentage = current * 100 / total
        elapsed = now - start_time
        speed = (current / (1024 * 1024)) / elapsed if elapsed > 0 else 0
        uploaded_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)

        try:
            await status_msg.edit_text(
                f"⬆️ **Uploading to Telegram...**\n\n"
                f"📊 **Progress:** {percentage:.1f}%\n"
                f"💾 **Uploaded:** {uploaded_mb:.1f} MB / {total_mb:.1f} MB\n"
                f"🚀 **Speed:** {speed:.2f} MB/s"
            )
        except Exception:
            pass

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
    await message.reply_text("⚡ **Bot Active!** Video URL bhejein.")

@app.on_message(filters.text & ~filters.command(["start"]))
async def download_and_upload(client: Client, message: Message):
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        await message.reply_text("❌ Kripya sahi Video URL bhejin.")
        return

    status_msg = await message.reply_text("⏳ Processing URL & Metadata...")
    base_name = f"video_{message.id}"
    video_path = f"{base_name}.mp4"
    loop = asyncio.get_running_loop()

    # yt-dlp Settings with Live Progress Hook
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': video_path,
        'writethumbnail': True,
        'outtmpl': {'thumbnail': base_name},
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'progress_hooks': [lambda d: yt_dlp_progress_hook(d, loop, status_msg)],
    }

    raw_thumb = None
    final_thumb = None

    try:
        await status_msg.edit_text("🚀 **Starting High-Speed Download...**")

        video_info = {}

        def do_download():
            nonlocal video_info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=True)

        await asyncio.to_thread(do_download)

        # Find and fix thumbnail
        for ext in ['.jpg', '.webp', '.png', '.jpeg']:
            p_thumb = f"{base_name}{ext}"
            if os.path.exists(p_thumb):
                raw_thumb = p_thumb
                break

        final_thumb = fix_thumbnail(raw_thumb) if raw_thumb else None

        if os.path.exists(video_path):
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

            if file_size_mb > 2000:
                await status_msg.edit_text(f"❌ File size ({file_size_mb:.1f}MB) 2GB Telegram limit se bada hai.")
                for f in [video_path, raw_thumb, final_thumb]:
                    if f and os.path.exists(f): 
                        try: os.remove(f)
                        except: pass
                return

            await status_msg.edit_text("⬆️ **Starting Telegram Upload...**")
            start_time = time.time()

            duration = int(video_info.get('duration', 0)) if video_info else 0
            width = int(video_info.get('width', 0)) if video_info else 0
            height = int(video_info.get('height', 0)) if video_info else 0

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

            # Cleanup
            for f in [video_path, raw_thumb, final_thumb]:
                if f and os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Download fail ho gaya.")

    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Error:** `{str(e)[:200]}`")
        for f in [video_path, raw_thumb, final_thumb]:
            if f and os.path.exists(f): 
                try: os.remove(f)
                except: pass

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot Active with Dual Live Progress...")
    app.run()
