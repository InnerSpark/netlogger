"""Scheduled nets: open (and link a node) at start time, close after the set length."""
import threading
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import ami, config, db

REPEATS = ("weekly", "monthly", "once")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", -1: "last"}


def tz(name):
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _nth_weekday(year, month, weekday, n):
    """Date of the nth weekday in a month (n=-1 for the last one), or None."""
    if n == -1:
        nxt = date(year + (month == 12), month % 12 + 1, 1)
        d = nxt - timedelta(days=1)
        return d - timedelta(days=(d.weekday() - weekday) % 7)
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    return d if d.month == month else None


def _dates_from(s, day):
    """Dates this schedule falls on, starting at `day` (a few, enough to find the next start)."""
    if s["repeat"] == "once":
        d = date.fromisoformat(s["date"])
        return [d] if d >= day else []
    if s["repeat"] == "weekly":
        first = day + timedelta(days=(s["weekday"] - day.weekday()) % 7)
        return [first + timedelta(weeks=i) for i in range(3)]
    out, y, m = [], day.year, day.month
    for _ in range(3):
        d = _nth_weekday(y, m, s["weekday"], s["week_of_month"])
        if d and d >= day:
            out.append(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def window(s, now):
    """(current_start, next_start) as aware datetimes. current_start is set while a net should be running."""
    zone = tz(s["tz"])
    local_now = now.astimezone(zone)
    hh, mm = (int(x) for x in s["start"].split(":"))
    length = timedelta(minutes=s["duration_min"])
    current, upcoming = None, None
    # start a day back so a net that began before midnight is still "current"
    for d in _dates_from(s, local_now.date() - timedelta(days=1)):
        start = datetime(d.year, d.month, d.day, hh, mm, tzinfo=zone)
        if start <= local_now < start + length:
            current = start
        elif start > local_now and upcoming is None:
            upcoming = start
    return current, upcoming


def describe(s):
    t = datetime.strptime(s["start"], "%H:%M").strftime("%-I:%M %p")
    if s["repeat"] == "weekly":
        when = f"Every {WEEKDAYS[s['weekday']]}"
    elif s["repeat"] == "monthly":
        when = f"The {ORDINALS.get(s['week_of_month'], '?')} {WEEKDAYS[s['weekday']]} of each month"
    else:
        when = date.fromisoformat(s["date"]).strftime("%A, %B %-d, %Y")
    return f"{when} at {t}, {s['duration_min']} minutes"


def public(s, now=None):
    now = now or datetime.now().astimezone()
    current, upcoming = window(s, now)
    return {**s, "description": describe(s), "running_now": bool(current),
            "next_start": upcoming.timestamp() if upcoming else None}


# ---------- the loop ----------
def tick(now=None):
    """Open or close nets for schedules. Runs every 30 seconds; safe to call any time."""
    now = now or datetime.now().astimezone()
    open_net = db.q("SELECT * FROM nets WHERE closed IS NULL ORDER BY id DESC LIMIT 1", one=True)

    # Close a scheduled net once its time is up
    if open_net and open_net.get("schedule_id"):
        s = db.q("SELECT * FROM schedules WHERE id=?", (open_net["schedule_id"],), one=True)
        ends = open_net["opened"] + (s["duration_min"] if s else 60) * 60
        if now.timestamp() >= ends:
            db.q("UPDATE nets SET closed=? WHERE id=?", (now.timestamp(), open_net["id"]))
            print(f"schedule: closed {open_net['name']!r}", flush=True)
            if s and s["node"] and s["disconnect_after"] and config.NODE_CONTROL:
                try:
                    ami.disconnect(s["node"])
                    ami.invalidate()
                except ami.AMIError as e:
                    print("schedule: disconnect failed:", e, flush=True)
            open_net = None

    for s in db.q("SELECT * FROM schedules WHERE enabled=1"):
        current, _ = window(s, now)
        if not current or (s["last_run"] or 0) >= current.timestamp():
            continue
        if open_net:
            print(f"schedule: {s['name']!r} is due but {open_net['name']!r} is still open, skipping", flush=True)
            db.q("UPDATE schedules SET last_run=? WHERE id=?", (current.timestamp(), s["id"]))
            continue
        name = f"{s['name']} {current.strftime('%Y-%m-%d')}"
        # Record the scheduled start, so a logger restarted mid-net still closes on time
        db.insert("INSERT INTO nets (name, opened, schedule_id) VALUES (?,?,?)",
                  (name, current.timestamp(), s["id"]))
        db.q("UPDATE schedules SET last_run=? WHERE id=?", (current.timestamp(), s["id"]))
        print(f"schedule: opened {name!r}", flush=True)
        open_net = True
        if s["node"] and config.NODE_CONTROL:
            try:
                ami.connect(s["node"])
                ami.invalidate()
                print(f"schedule: connected node {s['node']}", flush=True)
            except ami.AMIError as e:
                print("schedule: connect failed:", e, flush=True)
        if s["repeat"] == "once":
            db.q("UPDATE schedules SET enabled=0 WHERE id=?", (s["id"],))


def loop():
    while True:
        try:
            tick()
        except Exception as e:  # keep the scheduler alive no matter what
            print("schedule error:", repr(e), flush=True)
        time.sleep(30)


def start():
    threading.Thread(target=loop, daemon=True).start()
