"""HTTP API and static dashboard. Every /api route except /api/auth/* needs a login."""
import csv
import io
import json
import mimetypes
import re
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler

from . import __version__, ami, audio, auth, config, db, netlog
from .parser import extract_calls

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                                "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"),
}


class HTTPError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def need(cond, code, message):
    if not cond:
        raise HTTPError(code, message)


class Handler(BaseHTTPRequestHandler):
    server_version = "NetLogger"
    sys_version = ""

    def log_message(self, *a):
        pass

    # ---------- plumbing ----------
    def send(self, code, body, ctype="application/json", headers=None):
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in {**SECURITY_HEADERS, **(headers or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def token(self):
        c = SimpleCookie(self.headers.get("Cookie", ""))
        return c["nl_session"].value if "nl_session" in c else None

    def client(self):
        if config.TRUST_PROXY and config.CLIENT_IP_HEADER:
            ip = self.headers.get(config.CLIENT_IP_HEADER, "").strip()
            if ip:
                return ip
        if config.TRUST_PROXY:
            # The proxy appends the real client address last; earlier entries can be spoofed
            fwd = [a.strip() for a in self.headers.get("X-Forwarded-For", "").split(",") if a.strip()]
            if fwd:
                return fwd[-1]
        return self.client_address[0]

    def json_body(self):
        # JSON-only POSTs: a cross-site form can't send this without a CORS preflight, which we never allow
        need(self.headers.get("Content-Type", "").split(";")[0].strip() == "application/json", 415, "Send JSON.")
        n = int(self.headers.get("Content-Length") or 0)
        need(n <= 64 * 1024, 413, "Request too large.")
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            raise HTTPError(400, "Bad JSON.")

    def user(self, admin=False):
        u = auth.session_user(self.token())
        need(u, 401, "Please log in.")
        if admin:
            need(u["role"] == "admin", 403, "Admins only.")
        return u

    def route(self, method):
        path = self.path.split("?", 1)[0]
        try:
            if method == "GET" and not path.startswith("/api/"):  # HEAD comes through as GET
                return self.static(path)
            for m, pattern, fn in ROUTES:
                if m == method:
                    match = re.fullmatch(pattern, path)
                    if match:
                        return fn(self, *match.groups())
            raise HTTPError(404, "Not found.")
        except HTTPError as e:
            self.send(e.code, {"error": e.message})
        except Exception as e:  # never leak a stack trace to the browser
            print("server error:", repr(e), flush=True)
            self.send(500, {"error": "Something went wrong on the logger. Check its logs."})

    def do_GET(self):
        self.route("GET")

    def do_HEAD(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def static(self, path):
        rel = path.lstrip("/") or "index.html"
        f = (config.WEB_DIR / rel).resolve()
        if not f.is_relative_to(config.WEB_DIR) or not f.is_file():
            f = config.WEB_DIR / "index.html"  # single-page app
        if not f.is_file():
            return self.send(500, "Dashboard not built. Run: cd web && npm ci && npm run build", "text/plain")
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        cache = {"Cache-Control": "public, max-age=31536000, immutable"} if "/assets/" in path else {"Cache-Control": "no-cache"}
        self.send(200, f.read_bytes(), ctype, cache)


# ---------- auth ----------
def auth_status(h):
    return h.send(200, {"setup_needed": auth.user_count() == 0,
                        "user": auth.public(auth.session_user(h.token()))})


def auth_setup(h):
    b = h.json_body()
    need(auth.user_count() == 0, 409, "Setup is already done. Log in instead.")
    need(not auth.username_problem(b.get("username")), 400, auth.username_problem(b.get("username")) or "")
    need(not auth.password_problem(b.get("password")), 400, auth.password_problem(b.get("password")) or "")
    uid = auth.create_user(b["username"], b["password"], "admin")
    token = auth.new_session(uid)
    print(f"admin account {b['username']!r} created", flush=True)
    h.send(200, {"user": auth.public(auth.get_user(uid))}, headers={"Set-Cookie": auth.cookie(token)})


def auth_login(h):
    b = h.json_body()
    wait = auth.throttled(h.client())
    need(not wait, 429, f"Too many tries. Wait {wait} seconds.")
    u = auth.login(b.get("username"), b.get("password"))
    if not u:
        auth.record_fail(h.client())
        raise HTTPError(401, "Wrong username or password.")
    auth.record_ok(h.client())
    token = auth.new_session(u["id"])
    h.send(200, {"user": auth.public(u)}, headers={"Set-Cookie": auth.cookie(token)})


def auth_logout(h):
    h.json_body()
    auth.end_session(h.token())
    h.send(200, {}, headers={"Set-Cookie": auth.cookie("", clear=True)})


def me_password(h):
    u = h.user()
    b = h.json_body()
    need(auth.verify_password(b.get("current") or "", u["pw_hash"]), 400, "Current password is wrong.")
    need(not auth.password_problem(b.get("new")), 400, auth.password_problem(b.get("new")) or "")
    db.q("UPDATE users SET pw_hash=? WHERE id=?", (auth.hash_password(b["new"]), u["id"]))
    auth.end_user_sessions(u["id"], keep_token=h.token())  # sign out other devices
    h.send(200, {})


# ---------- users (admin) ----------
def users_list(h):
    h.user(admin=True)
    h.send(200, {"users": auth.list_users()})


def users_create(h):
    h.user(admin=True)
    b = h.json_body()
    need(not auth.username_problem(b.get("username")), 400, auth.username_problem(b.get("username")) or "")
    need(not auth.password_problem(b.get("password")), 400, auth.password_problem(b.get("password")) or "")
    need(b.get("role") in auth.ROLES, 400, "Role must be admin or operator.")
    need(not db.q("SELECT 1 FROM users WHERE username=?", (b["username"].strip(),), one=True),
         409, "That username is taken.")
    auth.create_user(b["username"], b["password"], b["role"])
    h.send(200, {"users": auth.list_users()})


def users_update(h, uid):
    me = h.user(admin=True)
    uid = int(uid)
    target = auth.get_user(uid)
    need(target, 404, "No such user.")
    b = h.json_body()
    losing_admin = target["role"] == "admin" and (b.get("delete") or b.get("role") == "operator")
    need(not (losing_admin and auth.admin_count() <= 1), 400, "There must be at least one admin.")
    if b.get("delete"):
        need(uid != me["id"], 400, "You can't delete your own account.")
        db.q("DELETE FROM users WHERE id=?", (uid,))
        return h.send(200, {"users": auth.list_users()})
    if "role" in b:
        need(b["role"] in auth.ROLES, 400, "Role must be admin or operator.")
        db.q("UPDATE users SET role=? WHERE id=?", (b["role"], uid))
    if b.get("password"):
        need(not auth.password_problem(b["password"]), 400, auth.password_problem(b["password"]) or "")
        db.q("UPDATE users SET pw_hash=? WHERE id=?", (auth.hash_password(b["password"]), uid))
        auth.end_user_sessions(uid)
    h.send(200, {"users": auth.list_users()})


# ---------- net + check-ins ----------
def state(h):
    h.user()
    net = netlog.current_or_last_net()
    rows = db.q("SELECT * FROM checkins WHERE net_id=? ORDER BY ts", (net["id"],)) if net else []
    heard = db.q("SELECT ts, text FROM transmissions ORDER BY id DESC LIMIT 8")
    h.send(200, {"net": net, "checkins": rows, "heard": heard})


def export_csv(h):
    h.user()
    net = netlog.current_or_last_net()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["#", "time", "call", "name", "location", "class", "flags", "first_time"])
    rows = db.q("SELECT * FROM checkins WHERE net_id=? ORDER BY ts", (net["id"] if net else -1,))
    for i, r in enumerate(rows, 1):
        w.writerow([i, time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"])), r["call"], r["name"],
                    r["location"], r["class"], r["flags"], "yes" if r["first_time"] else ""])
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", net["name"] if net else "net")
    h.send(200, out.getvalue(), "text/csv", {"Content-Disposition": f'attachment; filename="{name}.csv"'})


def net_open(h):
    h.user()
    b = h.json_body()
    if not netlog.open_net():
        name = (b.get("name") or "").strip()[:80] or time.strftime("Net %Y-%m-%d")
        db.insert("INSERT INTO nets (name, opened) VALUES (?,?)", (name, time.time()))
    h.send(200, {})


def net_close(h):
    h.user()
    h.json_body()
    db.q("UPDATE nets SET closed=? WHERE closed IS NULL", (time.time(),))
    h.send(200, {})


def checkin_add(h):
    h.user()
    b = h.json_body()
    net = netlog.open_net()
    need(net, 400, "Open a net first.")
    calls = extract_calls(str(b.get("call", "")).upper())
    need(calls, 400, "That's not a valid US callsign.")
    netlog.add_checkin(net["id"], calls[0], [], "manual")
    h.send(200, {})


FLAG_KEYS = {"traffic", "short_time", "recheck"}


def checkin_update(h, cid):
    h.user()
    cid = int(cid)
    b = h.json_body()
    row = db.q("SELECT * FROM checkins WHERE id=?", (cid,), one=True)
    need(row, 404, "That check-in is gone.")
    if b.get("delete"):
        db.q("DELETE FROM checkins WHERE id=?", (cid,))
        return h.send(200, {})
    if "call" in b:
        calls = extract_calls(str(b["call"]).upper())
        need(calls, 400, "That's not a valid US callsign.")
        need(not db.q("SELECT 1 FROM checkins WHERE call=? AND id<>? AND net_id=?", (calls[0], cid, row["net_id"]), one=True),
             400, f"{calls[0]} is already checked in.")
        info = netlog.lookup(calls[0])
        db.q("UPDATE checkins SET call=?, name=?, location=?, class=?, valid=? WHERE id=?",
             (calls[0], info.get("name", ""), info.get("location", ""), info.get("class", ""), info.get("valid"), cid))
    if "flags" in b:
        flags = [f for f in b["flags"] if f in FLAG_KEYS]
        db.q("UPDATE checkins SET flags=? WHERE id=?", (",".join(sorted(flags)), cid))
    if "recheck_done" in b:
        db.q("UPDATE checkins SET recheck_done=? WHERE id=?", (1 if b["recheck_done"] else 0, cid))
    h.send(200, {})


# ---------- node control ----------
def nodes(h):
    h.user()
    base = {"enabled": config.NODE_CONTROL, "logger_node": config.LOGGER_NODE, "default_node": config.DEFAULT_NODE}
    if not config.NODE_CONTROL:
        return h.send(200, {**base, "links": [], "error": None})
    s = ami.status()
    h.send(200, {**base, "links": s["links"], "error": s["error"]})


def node_action(h, action):
    u = h.user()
    b = h.json_body()
    node = str(b.get("node", "")).strip()
    need(config.NODE_CONTROL, 400, "Node control is off on this logger.")
    need(ami.valid_node(node), 400, "Node numbers are 3 to 7 digits.")
    try:
        (ami.connect if action == "connect" else ami.disconnect)(node)
    except ami.AMIError as e:
        raise HTTPError(502, str(e))
    print(f"{u['username']} {action}ed node {node}", flush=True)
    ami.invalidate()
    h.send(200, {})


# ---------- setup page ----------
def setup_status(h):
    h.user()
    last_tx = db.q("SELECT ts FROM transmissions ORDER BY id DESC LIMIT 1", one=True)
    node = {"configured": config.NODE_CONTROL, "reachable": None, "error": None, "links": []}
    if config.NODE_CONTROL:
        s = ami.status()
        node.update(reachable=s["error"] is None, error=s["error"], links=s["links"])
    h.send(200, {
        "version": __version__,
        "whisper_model": config.WHISPER_MODEL,
        "transcriber": audio.status["transcriber"],
        "last_packet": audio.status["last_packet"],
        "last_transmission": last_tx["ts"] if last_tx else None,
        "usrp_port": config.USRP_PORT,
        "http_port": config.HTTP_PORT,
        "logger_node": config.LOGGER_NODE,
        "default_node": config.DEFAULT_NODE,
        "ami_host": config.AMI_HOST,
        "ami_port": config.AMI_PORT,
        "ami_user": config.AMI_USER or "netlogger",
        "same_host": config.SAME_HOST,
        "node": node,
        "call_lookup": config.CALL_LOOKUP,
        "cookie_secure": config.COOKIE_SECURE,
    })


ROUTES = [
    ("GET", r"/api/auth/status", auth_status),
    ("POST", r"/api/auth/setup", auth_setup),
    ("POST", r"/api/auth/login", auth_login),
    ("POST", r"/api/auth/logout", auth_logout),
    ("POST", r"/api/me/password", me_password),
    ("GET", r"/api/users", users_list),
    ("POST", r"/api/users", users_create),
    ("POST", r"/api/users/(\d+)", users_update),
    ("GET", r"/api/state", state),
    ("GET", r"/api/export\.csv", export_csv),
    ("POST", r"/api/net/open", net_open),
    ("POST", r"/api/net/close", net_close),
    ("POST", r"/api/checkin", checkin_add),
    ("POST", r"/api/checkin/(\d+)", checkin_update),
    ("GET", r"/api/nodes", nodes),
    ("GET", r"/api/setup", setup_status),
    ("POST", r"/api/nodes/(connect|disconnect)", node_action),
]
