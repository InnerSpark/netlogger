"""Accounts, password hashing, sessions and login throttling. Standard library only."""
import base64
import hashlib
import hmac
import secrets
import threading
import time

from . import config, db

ROLES = ("admin", "operator")
MIN_PASSWORD = 10
_N, _R, _P = 2**14, 8, 1


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    b = lambda x: base64.b64encode(x).decode()
    return f"scrypt${_N}${_R}${_P}${b(salt)}${b(h)}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got, base64.b64decode(h))
    except Exception:
        return False


def password_problem(pw: str):
    if len(pw or "") < MIN_PASSWORD:
        return f"Password must be at least {MIN_PASSWORD} characters."
    return None


def username_problem(name: str):
    name = (name or "").strip()
    if not (2 <= len(name) <= 32) or not all(c.isalnum() or c in "-_." for c in name):
        return "Username must be 2 to 32 letters, numbers, dots, dashes or underscores."
    return None


# ---------- users ----------
def license_ok(u):
    return (not config.REQUIRE_LICENSE) or bool(u.get("callsign") and u.get("verified_by"))


def public(u):
    if not u:
        return None
    return {"id": u["id"], "username": u["username"], "role": u["role"],
            "callsign": u.get("callsign"), "license_name": u.get("license_name"),
            "license_class": u.get("license_class"), "verified_by": u.get("verified_by"),
            "license_ok": license_ok(u)}


def save_license(uid, result, verified_by):
    db.q("""UPDATE users SET callsign=?, license_name=?, license_class=?, license_verified=?, verified_by=?
            WHERE id=?""",
         (result["call"], result.get("name", ""), result.get("class", ""), time.time(), verified_by, uid))


def callsign_taken(call, except_id=None):
    return bool(db.q("SELECT 1 FROM users WHERE callsign=? AND id<>?", (call, except_id or -1), one=True))


def user_count():
    return db.q("SELECT COUNT(*) AS n FROM users", one=True)["n"]


def admin_count():
    return db.q("SELECT COUNT(*) AS n FROM users WHERE role='admin'", one=True)["n"]


def create_user(username, password, role):
    return db.insert("INSERT INTO users (username, pw_hash, role, created) VALUES (?,?,?,?)",
                     (username.strip(), hash_password(password), role, time.time()))


def get_user(uid):
    return db.q("SELECT * FROM users WHERE id=?", (uid,), one=True)


def list_users():
    return [public(u) for u in db.q("SELECT * FROM users ORDER BY username COLLATE NOCASE")]


# ---------- sessions ----------
def _h(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(user_id):
    token = secrets.token_urlsafe(32)
    now = time.time()
    db.q("DELETE FROM sessions WHERE expires < ?", (now,))
    db.q("INSERT INTO sessions (token_hash, user_id, created, expires) VALUES (?,?,?,?)",
         (_h(token), user_id, now, now + config.SESSION_DAYS * 86400))
    return token


def session_user(token):
    if not token:
        return None
    return db.q("""SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
                   WHERE s.token_hash=? AND s.expires > ?""", (_h(token), time.time()), one=True)


def end_session(token):
    if token:
        db.q("DELETE FROM sessions WHERE token_hash=?", (_h(token),))


def end_user_sessions(user_id, keep_token=None):
    if keep_token:
        db.q("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (user_id, _h(keep_token)))
    else:
        db.q("DELETE FROM sessions WHERE user_id=?", (user_id,))


def cookie(token, clear=False):
    parts = [f"nl_session={'' if clear else token}", "Path=/", "HttpOnly", "SameSite=Strict",
             f"Max-Age={0 if clear else config.SESSION_DAYS * 86400}"]
    if config.COOKIE_SECURE:
        parts.append("Secure")
    return "; ".join(parts)


# ---------- login throttling ----------
_fails = {}
_fails_lock = threading.Lock()


def throttled(key):
    """Seconds left before this client may try again, or 0."""
    with _fails_lock:
        n, until = _fails.get(key, (0, 0))
    return max(0, int(until - time.time()))


def record_fail(key):
    with _fails_lock:
        n, _ = _fails.get(key, (0, 0))
        n += 1
        # 5 free tries, then 30s, 60s, 120s... capped at 15 min
        wait = 0 if n < 5 else min(30 * 2 ** (n - 5), 900)
        _fails[key] = (n, time.time() + wait)


def record_ok(key):
    with _fails_lock:
        _fails.pop(key, None)


def login(username, password):
    u = db.q("SELECT * FROM users WHERE username=?", ((username or "").strip(),), one=True)
    if u and verify_password(password or "", u["pw_hash"]):
        return u
    if not u:
        verify_password(password or "", _DUMMY)  # same timing whether or not the user exists
    return None


_DUMMY = hash_password(secrets.token_hex(8))
