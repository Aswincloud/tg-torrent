import os
import io
import asyncio
import threading
import posixpath
import cloudscraper
import paramiko
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pyrogram.errors import FloodWait

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
QB_URL = os.environ.get("QB_URL", "http://localhost:8080")
QB_USERNAME = os.environ.get("QB_USERNAME")
QB_PASSWORD = os.environ.get("QB_PASSWORD")
ALLOWED_USERS = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x]

# --- SSH (for renaming sorted media files on the home server) ---------------
SSH_HOST = os.environ.get("SSH_HOST", "ssh.aswincloud.com")
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))
SSH_USER = os.environ.get("SSH_USER", "aswin")
SSH_KEY = os.environ.get("SSH_KEY", "")          # private key contents (PEM/OpenSSH)
# Token->path queue file on the server (written by the qBittorrent sort hook),
# in the SSH user's home so the bot can read it over SSH.
RENAME_QUEUE = os.environ.get("RENAME_QUEUE", "/home/aswin/Movies/.rename_queue.tsv")

def _ssh_run(cmd):
    """Run a command over SSH as SSH_USER, return (rc, stdout, stderr)."""
    if not SSH_KEY:
        return (1, "", "SSH_KEY not configured")
    key = None
    for loader in (paramiko.Ed25519Key, paramiko.RSAKey):
        try:
            key = loader.from_private_key(io.StringIO(SSH_KEY))
            break
        except Exception:
            continue
    if key is None:
        return (1, "", "could not parse SSH_KEY")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=20)
        _in, _out, _err = cli.exec_command(cmd, timeout=30)
        rc = _out.channel.recv_exit_status()
        return (rc, _out.read().decode(errors="replace"), _err.read().decode(errors="replace"))
    except Exception as e:
        return (1, "", f"ssh error: {e}")
    finally:
        try: cli.close()
        except Exception: pass

def _lookup_path(token):
    """Resolve a short token to its real file path via the server queue file."""
    safe = "".join(c for c in token if c.isalnum())  # token is alnum only
    if not safe:
        return None
    rc, out, _ = _ssh_run(
        f"awk -F'\\t' '$1==\"{safe}\"{{print $2; exit}}' {RENAME_QUEUE} 2>/dev/null"
    )
    p = out.strip()
    return p or None

def _do_rename(old_path, new_base):
    """Rename old_path's basename to new_base (extension preserved). Returns (ok, msg)."""
    old_path = old_path.strip()
    if not old_path or "\n" in old_path or "\x00" in old_path:
        return (False, "bad source path")
    # sanitize requested name: strip path separators and dangerous chars
    new_base = new_base.strip().strip("/").replace("/", "").replace("\x00", "")
    if not new_base:
        return (False, "empty name")
    d = posixpath.dirname(old_path)
    _, ext = posixpath.splitext(old_path)
    # if user already typed an extension, don't double it
    if not posixpath.splitext(new_base)[1]:
        new_base = new_base + ext
    new_path = posixpath.join(d, new_base)
    if new_path == old_path:
        return (True, new_base)
    # shell-quote both paths with single quotes (escape embedded quotes)
    def q(s): return "'" + s.replace("'", "'\\''") + "'"
    cmd = (f"test -e {q(old_path)} && ! test -e {q(new_path)} "
           f"&& mv -n {q(old_path)} {q(new_path)} && echo OK")
    rc, out, err = _ssh_run(cmd)
    if "OK" in out:
        return (True, new_base)
    if rc == 1 and not out:
        return (False, "source missing or target already exists")
    return (False, (err or out or "rename failed").strip()[:200])

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

from pyrogram import filters as _filters

def _user_id_allowed(uid):
    return not ALLOWED_USERS or uid in ALLOWED_USERS

@app.on_callback_query(_filters.regex(r"^rn:"))
async def on_rename_button(client, cq):
    if not _user_id_allowed(cq.from_user.id):
        await cq.answer("Not allowed", show_alert=True); return
    token = cq.data.split(":", 1)[1]
    path = await asyncio.to_thread(_lookup_path, token)
    if not path:
        await cq.answer("File not found (already renamed or removed).", show_alert=True)
        return
    cur = posixpath.basename(path)
    await cq.answer()
    # ForceReply prompt carrying the token so the reply handler knows the target.
    await client.send_message(
        cq.message.chat.id,
        f"✏️ Current name:\n`{cur}`\n\nReply with the new name "
        f"(extension optional).\n⁣rn-token:{token}",
        reply_markup=ForceReply(placeholder="Title (Year)"),
    )

@app.on_message(_filters.private & _filters.reply & _filters.text)
async def on_rename_reply(client, message):
    if not _user_id_allowed(message.from_user.id):
        return
    replied = message.reply_to_message
    if not replied or not replied.text or "rn-token:" not in replied.text:
        return  # not a reply to our rename prompt; ignore
    token = replied.text.split("rn-token:", 1)[1].strip()
    new_name = message.text.strip()
    path = await asyncio.to_thread(_lookup_path, token)
    if not path:
        await message.reply("⚠️ File not found (already renamed or removed).")
        return
    ok, msg = await asyncio.to_thread(_do_rename, path, new_name)
    if ok:
        await message.reply(f"✅ Renamed to:\n`{msg}`\n\nJellyfin will rescan shortly.")
    else:
        await message.reply(f"❌ Rename failed: {msg}")

def start_server():
    server.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    print("🚀 Starting bot...")
    app.run()
