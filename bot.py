import os
import asyncio
import threading
import cloudscraper
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
QB_URL = os.environ.get("QB_URL", "http://localhost:8080")
QB_USERNAME = os.environ.get("QB_USERNAME")
QB_PASSWORD = os.environ.get("QB_PASSWORD")
ALLOWED_USERS = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x]

app = Client("torrent_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
server = Flask(__name__)

# Cached session
_qb_session = None

def get_qb_session():
    global _qb_session
    if _qb_session:
        # Test if still valid
        try:
            r = _qb_session.get(f"{QB_URL}/api/v2/app/version", timeout=10)
            if r.status_code == 200:
                return _qb_session
        except Exception:
            pass

    session = cloudscraper.create_scraper()
    try:
        session.post(
            f"{QB_URL}/api/v2/auth/login",
            data={"username": QB_USERNAME, "password": QB_PASSWORD},
            timeout=30,
        )
        # Verify via an authenticated call — works whether the server
        # replies "Ok." (200) or 204 No Content on a successful login.
        v = session.get(f"{QB_URL}/api/v2/app/version", timeout=10)
        if v.status_code == 200:
            _qb_session = session
            return session
    except Exception as e:
        print(f"qB login error: {e}")
    return None

@server.route("/")
def home():
    return "Bot is running!", 200

def user_allowed(message):
    return not ALLOWED_USERS or message.from_user.id in ALLOWED_USERS

@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    if not user_allowed(message): return
    await message.reply("🏓 Pong!")

@app.on_message(filters.command("magnet") & filters.private)
async def add_magnet(client, message):
    if not user_allowed(message): return
    if len(message.command) < 2:
        await message.reply("Usage: /magnet <magnet_link>")
        return
    magnet = message.text.split(None, 1)[1]

    def _add():
        s = get_qb_session()
        if not s: return None
        return s.post(f"{QB_URL}/api/v2/torrents/add", data={"urls": magnet}, timeout=30)

    r = await asyncio.to_thread(_add)
    if r and r.status_code == 200:
        await message.reply("✅ Magnet added!")
    else:
        await message.reply("❌ Failed to add magnet.")

@app.on_message(filters.document & filters.private)
async def handle_torrent(client, message):
    if not user_allowed(message): return

    fname = (message.document.file_name or "").lower()
    if not fname.endswith(".torrent"):
        await message.reply("⚠️ Please send a .torrent file.")
        return

    try:
        status_msg = await message.reply("⬇️ Downloading...")
        file_path = await message.download()

        def _upload():
            s = get_qb_session()
            if not s: return None
            with open(file_path, "rb") as f:
                return s.post(f"{QB_URL}/api/v2/torrents/add",
                              files={"torrents": f}, timeout=60)

        r = await asyncio.to_thread(_upload)
        if r and r.status_code == 200:
            await status_msg.edit("✅ Torrent added!")
        else:
            await status_msg.edit(f"❌ Failed: {r.text if r else 'no session'}")
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

@app.on_message(filters.command("status") & filters.private)
async def status(client, message):
    if not user_allowed(message): return

    def _get():
        s = get_qb_session()
        if not s: return None
        return s.get(f"{QB_URL}/api/v2/torrents/info", timeout=30)

    r = await asyncio.to_thread(_get)
    if not r or r.status_code != 200:
        await message.reply("⚠️ Failed to fetch info.")
        return

    torrents = r.json()
    if not torrents:
        await message.reply("📭 No active downloads.")
        return

    lines = [f"📥 {t['name'][:50]} — {t['progress']*100:.1f}% ({t['state']})"
             for t in torrents[:20]]
    await message.reply("\n".join(lines))

def start_server():
    server.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    print("🚀 Starting bot...")
    app.run()
