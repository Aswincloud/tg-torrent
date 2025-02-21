import os
import requests
from pyrogram import Client, filters

# Read secrets from environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))  # API_ID must be converted to int
API_HASH = os.environ.get("API_HASH")
CHAT_ID = os.environ.get("CHAT_ID")

# qBittorrent Web API Credentials
QB_URL = os.environ.get("QB_URL", "http://localhost:8080")  # Default to localhost
QB_USERNAME = os.environ.get("QB_USERNAME")
QB_PASSWORD = os.environ.get("QB_PASSWORD")

# Initialize Telegram Bot
app = Client("torrent_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Login to qBittorrent
def qbittorrent_login():
    session = requests.Session()
    session.post(f"{QB_URL}/api/v2/auth/login", data={"username": QB_USERNAME, "password": QB_PASSWORD})
    return session

# Upload .torrent file to qBittorrent
@app.on_message(filters.document & filters.private)
async def handle_torrent(client, message):
    file_path = await message.download()
    session = qbittorrent_login()

    # Send file to qBittorrent
    with open(file_path, "rb") as f:
        files = {"torrents": f}
        session.post(f"{QB_URL}/api/v2/torrents/add", files=files)

    await message.reply("✅ Torrent added successfully!")
    os.remove(file_path)

# Start Bot
app.run()
