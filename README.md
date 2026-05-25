# tg-torrent 🤖

A Telegram bot that lets you add torrents to your qBittorrent instance remotely — send a magnet link or `.torrent` file and it gets queued instantly.

## Features

- `/magnet <link>` — add a magnet link to qBittorrent
- Send a `.torrent` file directly — auto-uploaded
- `/status` — view active downloads with progress
- `/ping` — health check
- User allowlist to restrict access

## Deployment

Deployed on [Koyeb](https://koyeb.com) as a containerized service using Docker.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash from my.telegram.org |
| `QB_URL` | qBittorrent Web UI URL |
| `QB_USERNAME` | qBittorrent username |
| `QB_PASSWORD` | qBittorrent password |
| `ALLOWED_USERS` | Comma-separated Telegram user IDs allowed to use the bot |
| `CHAT_ID` | Primary chat/user ID |

### Run with Docker

```bash
docker build -t tg-torrent .
docker run -d \
  -e BOT_TOKEN=your_token \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e QB_URL=http://your-qbittorrent-url \
  -e QB_USERNAME=admin \
  -e QB_PASSWORD=your_password \
  -e ALLOWED_USERS=123456789 \
  -p 8000:8000 \
  tg-torrent
```

## Stack

- [Pyrogram](https://pyrogram.org) — Telegram MTProto client
- [Flask](https://flask.palletsprojects.com) — lightweight HTTP server for health checks
- [cloudscraper](https://github.com/VeNoMouS/cloudscraper) — qBittorrent session management
- Python 3.9
