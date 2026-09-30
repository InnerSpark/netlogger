import time

from netlogger import db


def seed(opened, calls, schedule_id=None, first=()):
    nid = db.insert("INSERT INTO nets (name, opened, closed, schedule_id) VALUES (?,?,?,?)",
                    ("Net", opened, opened + 3600, schedule_id))
    for i, c in enumerate(calls):
        db.insert("INSERT INTO checkins (net_id, ts, call, flags, first_time) VALUES (?,?,?,?,?)",
                  (nid, opened + i, c, "traffic" if i == 0 else "", 1 if c in first else 0))
    return nid


def test_stats(admin):
    now = time.time()
    sid = db.insert("INSERT INTO schedules (name, repeat, weekday, start, duration_min, tz) VALUES ('Overland','weekly',4,'19:00',60,'UTC')")
    seed(now - 100 * 86400, ["W6UXD"], sid)                         # previous period
    seed(now - 20 * 86400, ["W6UXD", "K5OPR"], sid, first={"K5OPR"})
    seed(now - 10 * 86400, ["W6UXD", "K5OPR", "KE5KGX", "N0CALL"], sid, first={"KE5KGX", "N0CALL"})
    seed(now - 5 * 86400, ["AA1AA"])                                 # not scheduled

    code, s = admin.get("/api/stats?days=90")
    assert code == 200
    assert [n["checkins"] for n in s["nets"]] == [2, 4, 1]           # oldest first
    assert s["summary"] == {"nets": 3, "median_checkins": 2, "stations": 5, "first_timers": 3,
                            "prev_median_checkins": 1}
    assert s["nets"][0]["traffic"] == 1 and s["nets"][0]["minutes"] == 60
    assert {(r["call"], r["nets"]) for r in s["regulars"][:2]} == {("W6UXD", 2), ("K5OPR", 2)}

    code, s = admin.get(f"/api/stats?days=90&schedule={sid}")
    assert [n["checkins"] for n in s["nets"]] == [2, 4]
    code, s = admin.get("/api/stats?days=0")
    assert s["summary"]["nets"] == 4 and s["summary"]["prev_median_checkins"] is None


def test_stats_empty(admin):
    code, s = admin.get("/api/stats")
    assert code == 200 and s["nets"] == [] and s["summary"]["median_checkins"] is None
