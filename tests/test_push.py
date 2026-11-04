import base64
import json
import time

import pytest

from netlogger import audio, config, db, push

TOKEN_A = "a" * 64  # alerts
TOKEN_S = "b" * 64  # push-to-start
TOKEN_L = "c" * 64  # a running Live Activity


class Sent(list):
    key = None


@pytest.fixture
def sent(monkeypatch, tmp_path):
    """Push on, with a real throwaway key, and every send captured instead of going to Apple."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    pem = tmp_path / "AuthKey.p8"
    pem.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()))
    for k, v in {"APNS_KEY_FILE": str(pem), "APNS_KEY_ID": "KEY1234567", "APNS_TEAM_ID": "TEAM123456",
                 "APNS_TOPIC": "com.example.netlogger", "PUSH": True}.items():
        monkeypatch.setattr(config, k, v)
    push._jwt.update(token=None, at=0)
    out = Sent()
    monkeypatch.setattr(push, "send", lambda d, p, t="alert", pr=10: out.append((d["token"], p, t, pr)))
    out.key = key
    return out


def register(client, token, kind, **extra):
    return client.post("/api/devices", {"token": token, "kind": kind, "env": "sandbox", **extra})


def test_off_by_default(admin):
    assert not config.PUSH
    assert admin.get("/api/push")[1]["enabled"] is False
    admin.post("/api/net/open", {"name": "Quiet"})  # no APNs settings: nothing is sent, nothing breaks


def test_device_validation(admin):
    assert register(admin, "not-hex", "alert")[0] == 400
    assert register(admin, TOKEN_A, "bogus")[0] == 400
    assert register(admin, TOKEN_L, "activity")[0] == 400  # needs its net_id
    assert register(admin, TOKEN_A, "alert")[0] == 200
    assert register(admin, TOKEN_A.upper(), "alert")[0] == 200  # same token, any case: one row
    assert db.q("SELECT COUNT(*) AS n FROM devices", one=True)["n"] == 1
    assert admin.post("/api/devices/remove", {"token": TOKEN_A})[0] == 200
    assert db.q("SELECT COUNT(*) AS n FROM devices", one=True)["n"] == 0


def test_auth_token_is_a_valid_es256_jwt(sent):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    tok = push.auth_token()
    head, claims, sig = tok.split(".")
    pad = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    assert json.loads(pad(head)) == {"alg": "ES256", "kid": "KEY1234567"}
    assert json.loads(pad(claims))["iss"] == "TEAM123456"
    raw = pad(sig)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    sent.key.public_key().verify(der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))  # raises if wrong
    assert push.auth_token() == tok  # reused, not re-signed on every push


def test_net_lifecycle(admin, sent):
    register(admin, TOKEN_A, "alert")
    register(admin, TOKEN_S, "start")
    admin.post("/api/net/open", {"name": "Overland Net"})
    net = db.q("SELECT * FROM nets", one=True)
    kinds = {(t, ty) for t, _, ty, _ in sent}
    assert (TOKEN_A, "alert") in kinds and (TOKEN_S, "liveactivity") in kinds
    start = next(p for t, p, _, _ in sent if t == TOKEN_S)["aps"]
    assert start["event"] == "start" and start["attributes-type"] == "NetActivityAttributes"
    assert start["attributes"] == {"netId": net["id"]} and start["content-state"]["checkins"] == 0

    # the started activity reports its own token; check-ins now update it
    register(admin, TOKEN_L, "activity", net_id=net["id"])
    sent.clear()
    admin.post("/api/checkin", {"call": "KE5KGX"})
    update = next(p for t, p, ty, _ in sent if t == TOKEN_L)["aps"]
    assert update["event"] == "update"
    assert update["content-state"]["checkins"] == 1 and update["content-state"]["lastCall"] == "KE5KGX"
    assert any(t == TOKEN_A and p["aps"]["alert"]["title"] == "First-time check-in" for t, p, _, _ in sent)

    sent.clear()
    admin.post("/api/net/close", {})
    end = next(p for t, p, _, _ in sent if t == TOKEN_L)["aps"]
    assert end["event"] == "end" and end["content-state"]["closed"] is True and end["dismissal-date"] > time.time()
    assert not db.q("SELECT * FROM devices WHERE kind='activity'")  # that activity is over


def test_prefs_turn_alerts_off(admin, sent):
    register(admin, TOKEN_A, "alert", prefs={"net_start": False, "first_timer": True, "audio": True})
    admin.post("/api/net/open", {"name": "Overland Net"})
    assert not [s for s in sent if s[0] == TOKEN_A]


def test_dead_token_removed(admin, sent, monkeypatch):
    register(admin, TOKEN_A, "alert")
    seen = {}

    class Resp:
        status_code, text = 410, '{"reason":"Unregistered"}'

    class Client:
        def post(self, url, content, headers):
            seen.update(url=url, headers=headers)
            return Resp()

    monkeypatch.setattr(push, "_http", lambda: Client())
    device = db.q("SELECT * FROM devices", one=True)
    assert push.deliver(device, {"aps": {}}, "liveactivity", 5) == 410
    assert seen["url"] == f"https://api.sandbox.push.apple.com/3/device/{TOKEN_A}"
    assert seen["headers"]["apns-topic"] == "com.example.netlogger.push-type.liveactivity"
    assert seen["headers"]["authorization"].startswith("bearer ")
    assert not db.q("SELECT * FROM devices")


def test_audio_watchdog(admin, sent, monkeypatch):
    register(admin, TOKEN_A, "alert")
    admin.post("/api/net/open", {"name": "Overland Net"})
    sent.clear()
    opened = db.q("SELECT opened FROM nets", one=True)["opened"]
    monkeypatch.setitem(audio.status, "last_packet", None)
    push._quiet["warned_for"] = None
    push.check_audio(now=opened + 60)  # 1 minute in: fine
    assert not sent
    push.check_audio(now=opened + 6 * 60)  # 6 minutes of nothing
    assert len(sent) == 1 and "No audio" in sent[0][1]["aps"]["alert"]["title"]
    push.check_audio(now=opened + 9 * 60)  # still quiet: no repeat
    assert len(sent) == 1
    monkeypatch.setitem(audio.status, "last_packet", opened + 10 * 60)  # audio back
    push.check_audio(now=opened + 11 * 60)
    push.check_audio(now=opened + 17 * 60)  # quiet again: warn again
    assert len(sent) == 2
