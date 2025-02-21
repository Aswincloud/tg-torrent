import os
import requests
from pyrogram import Client, filters

# Read secrets from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))  # API_ID must be converted to int
API_HASH = os.getenv("API_HASH")
CHAT_ID = os.getenv("CHAT_ID")

# qBittorrent Web API Credentials
QB_URL = os.getenv("QB_URL", "http://localhost:8080")  # Default to localhost
QB_USERNAME = os.getenv("QB_USERNAME")
QB_PASSWORD = os.getenv("QB_PASSWORD")

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
