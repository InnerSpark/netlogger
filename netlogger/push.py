"""Push notifications and Live Activities for the Net Logger iOS app, through Apple (APNs).

Off unless the APNS_* settings are set. The app registers three kinds of device token:
  alert     ordinary notifications (net open, first-time check-in, audio stopped)
  start     push-to-start: lets the logger start the app's Live Activity when a net opens
  activity  one running Live Activity, tied to a net, that the logger updates and ends
Sends happen on a background thread so a slow Apple never holds up logging.
"""
import base64
import json
import queue
import threading
import time

from . import config, db

HOSTS = {"production": "https://api.push.apple.com", "sandbox": "https://api.sandbox.push.apple.com"}
PREFS = ("net_start", "first_timer", "audio")  # alert kinds the app can turn on or off
ATTRIBUTES_TYPE = "NetActivityAttributes"  # the Swift type name of the app's ActivityAttributes


def enabled():
    return config.PUSH


# ---------- Apple's auth token: a JWT signed with the .p8 key (ES256), reused for 40 minutes ----------
_jwt = {"token": None, "at": 0.0}


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def auth_token(now=None):
    now = now or time.time()
    if _jwt["token"] and now - _jwt["at"] < 40 * 60:
        return _jwt["token"]
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    with open(config.APNS_KEY_FILE, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    head = _b64(json.dumps({"alg": "ES256", "kid": config.APNS_KEY_ID}).encode())
    claims = _b64(json.dumps({"iss": config.APNS_TEAM_ID, "iat": int(now)}).encode())
    r, s = decode_dss_signature(key.sign(f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256())))
    _jwt.update(token=f"{head}.{claims}.{_b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}", at=now)
    return _jwt["token"]


# ---------- sending ----------
_client = None


def _http():
    global _client
    if _client is None:
        import httpx
        _client = httpx.Client(http2=True, timeout=10)
    return _client


def deliver(device, payload, push_type, priority):
    """Send one push now. Returns Apple's status code. Drops tokens Apple says are dead."""
    topic = config.APNS_TOPIC + (".push-type.liveactivity" if push_type == "liveactivity" else "")
    r = _http().post(f"{HOSTS[device['env']]}/3/device/{device['token']}", content=json.dumps(payload),
                     headers={"authorization": f"bearer {auth_token()}", "apns-topic": topic,
                              "apns-push-type": push_type, "apns-priority": str(priority)})
    if r.status_code == 410 or (r.status_code == 400 and "BadDeviceToken" in r.text):
        db.q("DELETE FROM devices WHERE token=?", (device["token"],))
    elif r.status_code != 200:
        print(f"push: {r.status_code} {r.text[:200]}", flush=True)
    return r.status_code


_queue = queue.Queue()
_worker = None


def send(device, payload, push_type="alert", priority=10):
    """Queue a push for the background sender."""
    global _worker
    if _worker is None:
        _worker = threading.Thread(target=_drain, daemon=True)
        _worker.start()
    _queue.put((device, payload, push_type, priority))


def _drain():
    while True:
        job = _queue.get()
        try:
            deliver(*job)
        except Exception as e:  # never let one bad send stop the rest
            print("push error:", repr(e), flush=True)


# ---------- devices ----------
def register(user_id, token, kind, env, net_id=None, prefs=None):
    prefs = {k: bool((prefs or {}).get(k, True)) for k in PREFS}
    db.q("""INSERT INTO devices (user_id, token, kind, env, net_id, prefs, updated) VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(token) DO UPDATE SET user_id=excluded.user_id, kind=excluded.kind, env=excluded.env,
              net_id=excluded.net_id, prefs=excluded.prefs, updated=excluded.updated""",
         (user_id, token, kind, env, net_id, json.dumps(prefs), time.time()))


def devices(kind, pref=None, net_id=None):
    rows = db.q("SELECT * FROM devices WHERE kind=?" + (" AND net_id=?" if net_id else ""),
                (kind, net_id) if net_id else (kind,))
    return [d for d in rows if not pref or json.loads(d["prefs"] or "{}").get(pref, True)]


# ---------- what the Live Activity shows ----------
def content_state(net):
    """Matches NetActivityAttributes.ContentState in the app. Times are Unix seconds, not Dates,
    because ActivityKit decodes Dates from a different epoch."""
    rows = db.q("SELECT call, ts, first_time FROM checkins WHERE net_id=? ORDER BY ts", (net["id"],))
    last = rows[-1] if rows else None
    return {"name": net["name"], "opened": net["opened"], "checkins": len(rows),
            "firstTimers": sum(1 for r in rows if r["first_time"]),
            "lastCall": last["call"] if last else None, "lastAt": last["ts"] if last else None,
            "closed": bool(net.get("closed"))}


def _net(net_id):
    return db.q("SELECT * FROM nets WHERE id=?", (net_id,), one=True)


def _alert(pref, title, body):
    for d in devices("alert", pref=pref):
        send(d, {"aps": {"alert": {"title": title, "body": body}, "sound": "default"}})


# ---------- events, called by the logger ----------
def net_opened(net_id):
    if not enabled() or not (net := _net(net_id)):
        return
    _alert("net_start", f"{net['name']} is open", "Logging check-ins now.")
    payload = {"aps": {"timestamp": int(time.time()), "event": "start", "content-state": content_state(net),
                       "attributes-type": ATTRIBUTES_TYPE, "attributes": {"netId": net["id"]},
                       "alert": {"title": net["name"], "body": "Net open. Check-ins show on your Lock Screen."}}}
    for d in devices("start"):
        send(d, payload, "liveactivity", 10)


def net_changed(net_id):
    if not enabled() or not (net := _net(net_id)):
        return
    payload = {"aps": {"timestamp": int(time.time()), "event": "update", "content-state": content_state(net)}}
    for d in devices("activity", net_id=net_id):
        send(d, payload, "liveactivity", 5)


def checkin_added(net_id, call, first_time, name=""):
    if not enabled():
        return
    net_changed(net_id)
    if first_time:
        _alert("first_timer", "First-time check-in", f"{call}{', ' + name if name else ''}")


def net_closed(net_id):
    if not enabled() or not (net := _net(net_id)):
        return
    now = int(time.time())
    payload = {"aps": {"timestamp": now, "event": "end", "content-state": content_state(net),
                       "dismissal-date": now + 15 * 60}}
    for d in devices("activity", net_id=net_id):
        send(d, payload, "liveactivity", 10)
    db.q("DELETE FROM devices WHERE kind='activity' AND net_id=?", (net_id,))


# ---------- audio watchdog ----------
_quiet = {"warned_for": None}


def check_audio(now=None):
    """During an open net, warn once when no audio has come in for AUDIO_ALERT_MIN minutes."""
    from . import audio, netlog
    if not enabled() or not config.AUDIO_ALERT_MIN:
        return
    now = now or time.time()
    net = netlog.open_net()
    if not net:
        _quiet["warned_for"] = None
        return
    last = max(audio.status["last_packet"] or 0, net["opened"])
    if now - last < config.AUDIO_ALERT_MIN * 60:
        _quiet["warned_for"] = None  # audio is flowing again; warn again next time it stops
        return
    if _quiet["warned_for"] != last:
        _quiet["warned_for"] = last
        _alert("audio", f"No audio for {config.AUDIO_ALERT_MIN} minutes",
               f"{net['name']} is open but nothing is coming in. Check that the logger node is linked.")


def start_watchdog():
    def loop():
        while True:
            try:
                check_audio()
            except Exception as e:
                print("push watchdog error:", repr(e), flush=True)
            time.sleep(60)
    threading.Thread(target=loop, daemon=True).start()
