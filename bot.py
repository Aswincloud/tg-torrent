import os
import requests
import asyncio
import threading
from flask import Flask
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
server = Flask(__name__)
@server.route("/")
def home():
    return "Bot is running!", 200  # Koyeb health check endpoint

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


# Function to start Pyrogram bot in a new event loop
def start_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())  # Create a new event loop for the thread
    app.run()

# Start Flask server
def start_server():
    server.run(host="0.0.0.0", port=8000)

# Run both Pyrogram and Flask concurrently
if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()  # Daemon thread so it exits with main process
    start_server()
