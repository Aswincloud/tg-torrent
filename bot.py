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
app = Client("torrent_bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Create Flask server for Koyeb health checks
server = Flask(__name__)

@server.route("/")
def home():
    return "Bot is running!", 200  # Koyeb health check endpoint

# Ping command
@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    await message.reply("🏓 Pong! The bot is alive.")
    
# Login to qBittorrent
def qbittorrent_login():
    session = requests.Session()
    login_response = session.post(
        f"{QB_URL}/api/v2/auth/login", 
        data={"username": QB_USERNAME, "password": QB_PASSWORD}
    )
    
    if login_response.text != "Ok.":
        print("❌ qBittorrent login failed!")
        return None
    
    print("✅ Logged in to qBittorrent")
    return session

# Upload .torrent file to qBittorrent
@app.on_message(filters.document & filters.private)
async def handle_torrent(client, message):
    print("📩 Received a file...")  # Debugging
    
    try:
        file_path = await message.download()
        print(f"✅ File downloaded: {file_path}")
        
        session = qbittorrent_login()
        if not session:
            await message.reply("❌ Failed to connect to qBittorrent!")
            return
        
        with open(file_path, "rb") as f:
            files = {"torrents": f}
            response = session.post(f"{QB_URL}/api/v2/torrents/add", files=files)
        
        if response.status_code == 200:
            await message.reply("✅ Torrent added successfully!")
        else:
            await message.reply(f"❌ Failed to add torrent! {response.text}")

        os.remove(file_path)
    
    except FloodWait as e:
        print(f"⏳ Flood wait detected! Sleeping for {e.value} seconds...")
        time.sleep(e.value)  # Sleep to prevent API bans


@app.on_message(filters.command("status") & filters.private)
async def status(client, message):
    session = qbittorrent_login()
    if not session:
        await message.reply("❌ Could not connect to qBittorrent.")
        return

    res = session.get(f"{QB_URL}/api/v2/torrents/info")
    if res.status_code == 200:
        torrents = res.json()
        if not torrents:
            await message.reply("📭 No active downloads.")
        else:
            msg = "\n".join([f"📥 {t['name']} - {t['progress']*100:.1f}%" for t in torrents])
            await message.reply(msg)
    else:
        await message.reply("⚠️ Failed to fetch torrent info.")


# Function to start Flask server
def start_server():
    server.run(host="0.0.0.0", port=8000)

# Run both Pyrogram and Flask concurrently
if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()  # Start Flask in a new thread
    print("🚀 Starting Telegram bot...")
    app.run()  # Ensures Pyrogram listens for messages
