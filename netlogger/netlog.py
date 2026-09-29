"""Nets, check-ins, and callsign lookups."""
import json
import time
import urllib.request

from . import config, db
from .parser import extract_calls, extract_flags, match_known, resolve


def open_net():
    return db.q("SELECT * FROM nets WHERE closed IS NULL ORDER BY id DESC LIMIT 1", one=True)


def current_or_last_net():
    return open_net() or db.q("SELECT * FROM nets ORDER BY id DESC LIMIT 1", one=True)


_cache = {}


def lookup(call):
    """Name, license class and location from callook.info (US only). {} if unreachable."""
    if not config.CALL_LOOKUP:
        return {}
    if call in _cache:
        return _cache[call]
    try:
        with urllib.request.urlopen(f"https://callook.info/{call}/json", timeout=4) as r:
            d = json.load(r)
    except Exception:
        return {}  # offline: don't cache, try again next time
    if d.get("status") == "VALID":
        info = {"valid": 1, "name": d.get("name", "").title(),
                "class": (d.get("current") or {}).get("operClass", ""),
                "location": (d.get("address") or {}).get("line2", "")}
    else:
        info = {"valid": 0}
    _cache[call] = info
    return info


def known_calls(limit=200):
    """Calls logged before (most recent first) plus KNOWN_CALLS from settings."""
    rows = db.q("SELECT call FROM checkins GROUP BY call ORDER BY MAX(ts) DESC LIMIT ?", (limit,))
    return list(dict.fromkeys([r["call"] for r in rows] + config.KNOWN_CALLS))


def calls_in(text):
    """Calls in a transcript, with clipped or garbled ones snapped to known calls where it's clear."""
    known = set(known_calls())
    calls = [resolve(c, known) for c in extract_calls(text)]
    if not calls:
        hit = match_known(text, known)
        calls = [hit] if hit else []
    return list(dict.fromkeys(calls))


def log_text(text, seconds):
    """Record one transmission. While a net is open, the first callsign heard is a check-in."""
    net = open_net()
    calls = calls_in(text)
    db.insert("INSERT INTO transmissions (net_id, ts, seconds, text, calls) VALUES (?,?,?,?,?)",
              (net["id"] if net else None, time.time(), seconds, text, ",".join(calls)))
    if net and calls:
        add_checkin(net["id"], calls[0], extract_flags(text), text)


def add_checkin(net_id, call, flags, text=""):
    existing = db.q("SELECT * FROM checkins WHERE net_id=? AND call=?", (net_id, call), one=True)
    if existing:
        merged = sorted(set(filter(None, existing["flags"].split(","))) | set(flags))
        db.q("UPDATE checkins SET flags=? WHERE id=?", (",".join(merged), existing["id"]))
        return existing["id"]
    seen = db.q("SELECT 1 FROM checkins WHERE call=? AND net_id<>? LIMIT 1", (call, net_id), one=True)
    info = lookup(call)
    return db.insert(
        """INSERT INTO checkins (net_id, ts, call, name, location, class, valid, first_time, flags, transcript)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (net_id, time.time(), call, info.get("name", ""), info.get("location", ""),
         info.get("class", ""), info.get("valid"), 0 if seen else 1, ",".join(flags), text))
