"""Check that a callsign belongs to a current amateur radio license.

Uses callook.info, which mirrors the FCC's license database (US calls only).
"""
import json
import re
import time
import urllib.request
from datetime import datetime

from . import config


class LookupUnavailable(Exception):
    """callook.info couldn't be reached or is refreshing its data. Not the user's fault."""


CALL_FORMAT = re.compile(r"^[A-Z0-9]{3,7}$")


def normalize(call):
    return re.sub(r"\s+", "", str(call or "")).upper()


def _parse_date(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            pass
    return None


def fetch(call):
    """Raw callook.info record. Split out so tests can replace it."""
    import os
    fake = os.environ.get("NETLOG_FAKE_LICENSES")  # testing only: JSON file of {CALL: record}
    if fake:
        return json.load(open(fake)).get(call, {"status": "INVALID"})
    try:
        with urllib.request.urlopen(f"https://callook.info/{call}/json", timeout=6) as r:
            return json.load(r)
    except Exception as e:
        raise LookupUnavailable(str(e))


def check(call):
    """Return {"ok": bool, "call", "name", "class", "expires", "reason"}.

    Raises LookupUnavailable when the check can't be done right now.
    """
    call = normalize(call)
    if not CALL_FORMAT.match(call):
        return {"ok": False, "call": call, "reason": "That doesn't look like a callsign."}
    d = fetch(call)
    status = str(d.get("status", "")).upper()
    if status == "UPDATING":
        raise LookupUnavailable("callook.info is updating its data")
    if status != "VALID":
        return {"ok": False, "call": call,
                "reason": f"{call} isn't an active license in the FCC database. Non-US calls need an admin to verify them."}
    expires = (d.get("otherInfo") or {}).get("expiryDate", "")
    exp = _parse_date(expires)
    if exp and exp < datetime.now():
        return {"ok": False, "call": call, "reason": f"The license for {call} expired on {expires}."}
    return {"ok": True, "call": call, "reason": "",
            "name": str(d.get("name", "")).title(),
            "class": str((d.get("current") or {}).get("operClass", "")).title(),
            "expires": expires}


def stale(user):
    """True when a callook-verified account is due for its periodic re-check."""
    return (user.get("verified_by") == "callook"
            and time.time() - (user.get("license_verified") or 0) > config.LICENSE_RECHECK_DAYS * 86400)
