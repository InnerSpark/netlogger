from netlogger import auth
from tests.conftest import Client


def test_password_hash_roundtrip():
    h = auth.hash_password("correct horse")
    assert h.startswith("scrypt$")
    assert auth.verify_password("correct horse", h)
    assert not auth.verify_password("wrong horse!", h)
    assert not auth.verify_password("x", "garbage")


def test_everything_needs_login(client):
    for path in ["/api/state", "/api/nodes", "/api/users", "/api/export.csv"]:
        assert client.get(path)[0] == 401, path
    assert client.post("/api/net/open")[0] == 401


def test_first_run_setup_then_locked(client, server):
    code, body = client.get("/api/auth/status")
    assert body["setup_needed"] is True and body["user"] is None
    assert client.post("/api/auth/setup", {"username": "ncs", "callsign": "W6ABC", "password": "short"})[0] == 400
    assert client.post("/api/auth/setup", {"username": "ncs", "password": "correct horse"})[0] == 400  # no call
    code, body = client.post("/api/auth/setup", {"username": "ncs", "callsign": "W6ABC", "password": "correct horse"})
    assert code == 200 and body["user"]["role"] == "admin" and body["user"]["license_ok"]
    assert client.get("/api/state")[0] == 200
    # second setup is refused
    other = Client(server)
    assert other.post("/api/auth/setup", {"username": "evil", "callsign": "K5OPR", "password": "correct horse"})[0] == 409


def test_login_logout_and_throttle(admin, server):
    c = Client(server)
    assert c.post("/api/auth/login", {"username": "NCS", "password": "correct horse"})[0] == 200  # case-insensitive
    assert c.get("/api/state")[0] == 200
    assert c.post("/api/auth/logout")[0] == 200
    assert c.get("/api/state")[0] == 401
    bad = Client(server)
    codes = [bad.post("/api/auth/login", {"username": "ncs", "password": "nope nope nope"})[0] for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_json_only_posts(admin):
    # a cross-site form post can't set application/json
    assert admin.post("/api/net/open", {}, ctype="application/x-www-form-urlencoded")[0] == 415


def test_user_management(admin, server):
    code, body = admin.post("/api/users", {"username": "kilo", "callsign": "K5OPR", "password": "operator pass", "role": "operator"})
    assert code == 200 and {u["username"] for u in body["users"]} == {"ncs", "kilo"}
    assert admin.post("/api/users", {"username": "KILO", "callsign": "K5OPR", "password": "operator pass", "role": "operator"})[0] == 409
    op = Client(server)
    assert op.post("/api/auth/login", {"username": "kilo", "password": "operator pass"})[0] == 200
    assert op.get("/api/users")[0] == 403  # operators can't manage users
    assert op.get("/api/state")[0] == 200
    # operators see audio health only, not server details
    code, st = op.get("/api/setup")
    assert code == 200 and set(st) == {"transcriber", "last_packet", "last_transmission"}
    assert "ami_host" in admin.get("/api/setup")[1]
    me = next(u for u in admin.get("/api/users")[1]["users"] if u["username"] == "ncs")
    kilo = next(u for u in admin.get("/api/users")[1]["users"] if u["username"] == "kilo")
    assert admin.post(f"/api/users/{me['id']}", {"delete": True})[0] == 400  # not yourself
    assert admin.post(f"/api/users/{me['id']}", {"role": "operator"})[0] == 400  # last admin
    # admin resets operator password: operator's sessions end
    assert admin.post(f"/api/users/{kilo['id']}", {"password": "brand new pass"})[0] == 200
    assert op.get("/api/state")[0] == 401


def test_change_own_password(admin, server):
    assert admin.post("/api/me/password", {"current": "wrong", "new": "another good one"})[0] == 400
    assert admin.post("/api/me/password", {"current": "correct horse", "new": "another good one"})[0] == 200
    assert admin.get("/api/state")[0] == 200  # this session stays
    c = Client(server)
    assert c.post("/api/auth/login", {"username": "ncs", "password": "another good one"})[0] == 200


def test_throttle_per_client_behind_proxy(admin, server, monkeypatch):
    from netlogger import config
    import json, urllib.request
    monkeypatch.setattr(config, "TRUST_PROXY", True)

    def login(ip, pw):
        r = urllib.request.Request(server + "/api/auth/login", method="POST",
                                   data=json.dumps({"username": "ncs", "password": pw}).encode(),
                                   headers={"Content-Type": "application/json", "X-Forwarded-For": f"9.9.9.9, {ip}"})
        try:
            return urllib.request.urlopen(r).status
        except urllib.error.HTTPError as e:
            return e.code

    assert [login("203.0.113.5", "wrong password!") for _ in range(6)][-1] == 429
    assert login("198.51.100.7", "correct horse") == 200  # someone else isn't locked out


def test_cloudflare_client_ip_header(admin, server, monkeypatch):
    from netlogger import config
    import json, urllib.request
    monkeypatch.setattr(config, "TRUST_PROXY", True)
    monkeypatch.setattr(config, "CLIENT_IP_HEADER", "CF-Connecting-IP")

    def login(ip, pw):
        r = urllib.request.Request(server + "/api/auth/login", method="POST",
                                   data=json.dumps({"username": "ncs", "password": pw}).encode(),
                                   headers={"Content-Type": "application/json", "CF-Connecting-IP": ip,
                                            "X-Forwarded-For": "162.158.0.1"})  # same Cloudflare edge for both
        try:
            return urllib.request.urlopen(r).status
        except urllib.error.HTTPError as e:
            return e.code

    assert [login("203.0.113.5", "wrong password!") for _ in range(6)][-1] == 429
    assert login("198.51.100.7", "correct horse") == 200
