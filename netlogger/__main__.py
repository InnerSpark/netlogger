"""Run the logger: python -m netlogger

Maintenance commands (on an install.sh server, run them as `sudo netlogger ...`):
  python -m netlogger reset-password <username or callsign>
  python -m netlogger backup [file]
"""
import os
import secrets
import sqlite3
import sys
import threading
import time
from http.server import ThreadingHTTPServer

from . import __version__, ami, audio, auth, config, db, schedule
from .web import Handler

KEEP_BACKUPS = 10


def reset_password(who):
    """Give an account a new random password and log it out everywhere. For admins locked out."""
    u = db.q("SELECT * FROM users WHERE username=? OR callsign=?", (who.strip(), who.strip().upper()), one=True)
    if not u:
        names = ", ".join(f"{r['username']} ({r['callsign'] or 'no call'})" for r in db.q("SELECT username, callsign FROM users"))
        print(f"No account '{who}'. Accounts: {names or 'none'}", file=sys.stderr)
        return 1
    pw = "-".join(secrets.token_urlsafe(4) for _ in range(3))
    db.q("UPDATE users SET pw_hash=? WHERE id=?", (auth.hash_password(pw), u["id"]))
    auth.end_user_sessions(u["id"])
    print(f"New password for {u['username']} ({u['role']}): {pw}")
    print("Log in with it, then change it under Change password.")
    return 0


def backup(path=None):
    """Copy the database safely, even while the logger is running."""
    if path is None:
        folder = config.DATA_DIR / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"netlog-{time.strftime('%Y%m%d-%H%M%S')}.db"
        for f in sorted(folder.glob("netlog-*.db"))[:-(KEEP_BACKUPS - 1)]:  # keep the newest ones
            f.unlink()
    # Straight from the file, before any upgrade touches the tables
    src = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    dst = sqlite3.connect(path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    os.chmod(path, 0o600)  # holds password hashes
    print(f"Backed up to {path}")
    return 0


def main():
    db.connect()
    print(f"Net Logger {__version__}", flush=True)
    threading.Thread(target=audio.transcriber, daemon=True).start()
    threading.Thread(target=audio.listener, daemon=True).start()
    schedule.start()
    if config.NODE_CONTROL:
        print(f"node control on: logger node {config.LOGGER_NODE} via {config.AMI_HOST}:{config.AMI_PORT}", flush=True)
        if config.AUTO_CONNECT and config.DEFAULT_NODE:
            threading.Thread(target=ami.auto_connect_loop, daemon=True).start()
    else:
        print("node control off (AMI_HOST not set)", flush=True)
    print(f"dashboard on http://{config.HTTP_HOST}:{config.HTTP_PORT}", flush=True)
    ThreadingHTTPServer((config.HTTP_HOST, config.HTTP_PORT), Handler).serve_forever()


def cli(argv):
    if not argv:
        return main()
    cmd, args = argv[0], argv[1:]
    if cmd == "reset-password" and len(args) == 1:
        db.connect()
        return reset_password(args[0])
    if cmd == "backup" and len(args) <= 1:
        return backup(args[0] if args else None)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
