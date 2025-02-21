import os
import requests
from pyrogram import Client, filters

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")
print(BOT_TOKEN)
API_ID = {{ secret.API_ID }}  # Your Telegram API ID
API_HASH = "{{ secret.API_HASH }}"
CHAT_ID = "{{ secret.CHAT_ID }}"

# qBittorrent Web API Credentials
QB_URL = "{{ secret.QB_URL }}"
QB_USERNAME = "{{ secret.QB_USERNAME }}"
QB_PASSWORD = "{{ secret.QB_PASSWORD }}"

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
