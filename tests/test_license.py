import time

from netlogger import db, license
from tests.conftest import Client


def test_check_results():
    assert license.check("w6abc")["ok"] and license.check("W6ABC")["class"] == "Extra"
    assert "expired" in license.check("KE5OLD")["reason"]
    assert "isn't an active license" in license.check("K1NOPE")["reason"]
    assert "doesn't look like" in license.check("hello world!")["reason"]


def test_setup_needs_real_license(client, fake_callook):
    assert client.post("/api/auth/setup", {"callsign": "K1NOPE", "password": "correct horse"})[0] == 400
    assert client.post("/api/auth/setup", {"callsign": "KE5OLD", "password": "correct horse"})[0] == 400
    fake_callook["down"] = True
    code, body = client.post("/api/auth/setup", {"callsign": "W6ABC", "password": "correct horse"})
    assert code == 503 and "Try again" in body["error"]
    fake_callook["down"] = False
    code, body = client.post("/api/auth/setup", {"callsign": "w6abc", "password": "correct horse"})
    assert code == 200 and body["user"]["username"] == "w6abc" and body["user"]["callsign"] == "W6ABC"


def test_admin_adds_users(admin, server, fake_callook):
    assert admin.post("/api/users", {"callsign": "K1NOPE", "password": "operator pass", "role": "operator"})[0] == 400
    # non-US or lookup down: admin vouches for it
    code, body = admin.post("/api/users", {"callsign": "VE3XYZ", "password": "operator pass", "role": "operator", "manual": True})
    assert code == 200
    ve = next(u for u in body["users"] if u["callsign"] == "VE3XYZ")
    assert ve["verified_by"] == "admin:ncs" and ve["license_ok"]
    assert admin.post("/api/users", {"callsign": "W6ABC", "password": "operator pass", "role": "operator"})[0] == 409


def test_existing_account_without_call_must_verify(server):
    from netlogger import auth
    uid = auth.create_user("legacy", "correct horse", "admin")  # made before license checks existed
    c = Client(server)
    assert c.post("/api/auth/login", {"username": "legacy", "password": "correct horse"})[0] == 200
    assert c.get("/api/auth/status")[1]["user"]["license_ok"] is False
    assert c.get("/api/state")[0] == 403           # locked out of the dashboard
    assert c.post("/api/me/license", {"callsign": "K1NOPE"})[0] == 400
    assert c.post("/api/me/license", {"callsign": "K5OPR"})[0] == 200
    assert c.get("/api/state")[0] == 200


def test_expired_license_loses_access_at_recheck(admin, server):
    from netlogger import auth, config
    from tests.conftest import FAKE_LICENSES
    old = time.time() - (config.LICENSE_RECHECK_DAYS + 1) * 86400
    db.q("UPDATE users SET license_verified=? WHERE callsign='W6ABC'", (old,))
    FAKE_LICENSES["W6ABC"]["otherInfo"]["expiryDate"] = "01/01/2001"
    try:
        c = Client(server)
        c.post("/api/auth/login", {"username": "ncs", "password": "correct horse"})
        assert c.get("/api/auth/status")[1]["user"]["license_ok"] is False
        assert c.get("/api/state")[0] == 403
    finally:
        FAKE_LICENSES["W6ABC"]["otherInfo"]["expiryDate"] = "01/01/2099"


def test_recheck_lookup_down_keeps_access(admin, server, fake_callook):
    from netlogger import config
    db.q("UPDATE users SET license_verified=0 WHERE callsign='W6ABC'")
    fake_callook["down"] = True
    c = Client(server)
    c.post("/api/auth/login", {"username": "ncs", "password": "correct horse"})
    assert c.get("/api/state")[0] == 200


def test_license_off(client, monkeypatch):
    from netlogger import config
    monkeypatch.setattr(config, "REQUIRE_LICENSE", False)
    code, body = client.post("/api/auth/setup", {"username": "ncs", "password": "correct horse"})
    assert code == 200 and body["user"]["license_ok"]


def test_migrates_1_0_database(tmp_path):
    import sqlite3
    old = tmp_path / "old.db"
    c = sqlite3.connect(old)
    c.executescript("""CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                       pw_hash TEXT NOT NULL, role TEXT NOT NULL, created REAL NOT NULL);
                       INSERT INTO users VALUES (1, 'admin', 'x', 'admin', 0);""")
    c.commit(); c.close()
    db.connect(old)
    u = db.q("SELECT * FROM users WHERE id=1", one=True)
    assert u["username"] == "admin" and u["callsign"] is None and "verified_by" in u
