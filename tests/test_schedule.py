from datetime import datetime
from zoneinfo import ZoneInfo

from netlogger import db, schedule

CT = ZoneInfo("America/Chicago")


def sched(**kw):
    base = {"id": 1, "name": "Overland Net", "repeat": "weekly", "weekday": 4, "week_of_month": None,
            "date": None, "start": "19:00", "duration_min": 60, "node": None, "disconnect_after": 1,
            "tz": "America/Chicago", "enabled": 1, "last_run": None}
    return {**base, **kw}


def at(*a):
    return datetime(*a, tzinfo=CT)


def test_weekly_window_and_next():
    s = sched()  # Fridays 7 PM Central
    cur, nxt = schedule.window(s, at(2026, 10, 2, 18, 0))   # Friday 6 PM
    assert cur is None and nxt == at(2026, 10, 2, 19, 0)
    cur, nxt = schedule.window(s, at(2026, 10, 2, 19, 30))  # during the net
    assert cur == at(2026, 10, 2, 19, 0) and nxt == at(2026, 10, 9, 19, 0)
    cur, _ = schedule.window(s, at(2026, 10, 2, 20, 0))     # just ended
    assert cur is None


def test_net_across_midnight():
    s = sched(start="23:30", duration_min=90)
    cur, _ = schedule.window(s, at(2026, 10, 3, 0, 30))
    assert cur == at(2026, 10, 2, 23, 30)


def test_monthly_nth_and_last_weekday():
    first_tue = sched(repeat="monthly", weekday=1, week_of_month=1)
    assert schedule.window(first_tue, at(2026, 10, 2, 12, 0))[1] == at(2026, 10, 6, 19, 0)
    last_fri = sched(repeat="monthly", weekday=4, week_of_month=-1)
    assert schedule.window(last_fri, at(2026, 10, 2, 12, 0))[1] == at(2026, 10, 30, 19, 0)
    assert "last Friday" in schedule.describe(last_fri)


def test_once_and_dst():
    once = sched(repeat="once", weekday=None, date="2026-11-01", start="19:00")  # DST ends that morning
    nxt = schedule.window(once, at(2026, 10, 31, 12, 0))[1]
    assert nxt == at(2026, 11, 1, 19, 0) and nxt.utcoffset().total_seconds() == -6 * 3600
    assert schedule.window(once, at(2026, 11, 2, 12, 0)) == (None, None)


def _add(s):
    cols = [k for k in s if k != "id"]
    db.insert(f"INSERT INTO schedules ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", [s[k] for k in cols])


def test_tick_opens_links_and_closes(server, fake_ami):
    _add(sched(node="41234"))
    schedule.tick(at(2026, 10, 2, 18, 59))
    assert db.q("SELECT * FROM nets") == []
    schedule.tick(at(2026, 10, 2, 19, 0, 20))
    net = db.q("SELECT * FROM nets", one=True)
    assert net["name"] == "Overland Net 2026-10-02" and net["closed"] is None and net["schedule_id"] == 1
    assert fake_ami.commands[-1] == "rpt cmd 1999 ilink 2 41234"   # monitor only
    schedule.tick(at(2026, 10, 2, 19, 30))                          # no double open
    assert len(db.q("SELECT * FROM nets")) == 1
    schedule.tick(at(2026, 10, 2, 20, 0, 10))
    assert db.q("SELECT closed FROM nets", one=True)["closed"] is not None
    assert fake_ami.commands[-1] == "rpt cmd 1999 ilink 1 41234"


def test_tick_skips_when_manual_net_open(server):
    _add(sched())
    db.insert("INSERT INTO nets (name, opened) VALUES ('Manual', ?)", (at(2026, 10, 2, 18, 0).timestamp(),))
    schedule.tick(at(2026, 10, 2, 19, 5))
    assert [n["name"] for n in db.q("SELECT name FROM nets")] == ["Manual"]
    db.q("UPDATE nets SET closed=1")
    schedule.tick(at(2026, 10, 2, 19, 10))  # already skipped this occurrence: don't open late
    assert len(db.q("SELECT * FROM nets")) == 1


def test_manual_close_sticks(server):
    _add(sched())
    schedule.tick(at(2026, 10, 2, 19, 1))
    db.q("UPDATE nets SET closed=?", (at(2026, 10, 2, 19, 20).timestamp(),))
    schedule.tick(at(2026, 10, 2, 19, 25))
    assert len(db.q("SELECT * FROM nets")) == 1


def test_schedule_api_and_history(admin):
    bad = admin.post("/api/schedules", {"name": "X", "repeat": "weekly", "start": "25:00", "weekday": 4, "tz": "America/Chicago"})
    assert bad[0] == 400
    code, body = admin.post("/api/schedules", {"name": "Overland Net", "repeat": "monthly", "weekday": 4, "week_of_month": 1,
                                                "start": "19:00", "duration_min": 60, "node": "41234", "tz": "America/Chicago"})
    assert code == 200 and body["schedules"][0]["description"].startswith("The first Friday")
    assert body["schedules"][0]["next_start"] is not None
    sid = body["schedules"][0]["id"]
    assert admin.post(f"/api/schedules/{sid}", {"enabled": False})[1]["schedules"][0]["enabled"] == 0
    # history
    admin.post("/api/net/open", {"name": "Past Net"})
    admin.post("/api/checkin", {"call": "K5ABC"})
    from netlogger import netlog
    netlog.log_text("Kilo Five Alpha Bravo Charlie with traffic", 2.0)
    admin.post("/api/net/close")
    nets = admin.get("/api/nets")[1]["nets"]
    assert nets[0]["name"] == "Past Net" and nets[0]["checkin_count"] == 1
    detail = admin.get(f"/api/nets/{nets[0]['id']}")[1]
    assert detail["checkins"][0]["call"] == "K5ABC" and "traffic" in detail["transmissions"][0]["text"]
    code, txt = admin.get(f"/api/nets/{nets[0]['id']}/transcript.txt")
    assert code == 200 and "[K5ABC] Kilo Five" in txt
    code, csv = admin.get(f"/api/export.csv?net={nets[0]['id']}")
    assert "K5ABC" in csv
    assert admin.post(f"/api/schedules/{sid}", {"delete": True})[1]["schedules"] == []
