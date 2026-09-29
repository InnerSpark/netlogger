from netlogger import netlog


def test_checkins_flow(admin):
    assert admin.post("/api/checkin", {"call": "K5ABC"})[1]["error"] == "Open a net first."
    admin.post("/api/net/open", {"name": "Test Net"})
    netlog.log_text("Kilo Five Alpha Bravo Charlie, Dana, with traffic.", 2.0)
    netlog.log_text("Kilo Five Alpha Bravo Charlie, short time.", 2.0)  # same call: merge flags
    assert admin.post("/api/checkin", {"call": "hello"})[1]["error"] == "That's not a valid US callsign."
    assert admin.post("/api/checkin", {"call": "w5bo"})[0] == 200
    s = admin.get("/api/state")[1]
    assert [(c["call"], c["flags"]) for c in s["checkins"]] == [("K5ABC", "short_time,traffic"), ("W5BO", "")]
    cid = s["checkins"][1]["id"]
    assert admin.post(f"/api/checkin/{cid}", {"call": "K5ABC"})[0] == 400  # duplicate
    assert admin.post(f"/api/checkin/{cid}", {"flags": ["recheck", "bogus"]})[0] == 200
    assert admin.get("/api/state")[1]["checkins"][1]["flags"] == "recheck"
    code, csv = admin.get("/api/export.csv")
    assert code == 200 and "K5ABC" in csv and "W5BO" in csv
    admin.post("/api/net/close")
    netlog.log_text("November Five X-ray Yankee Zulu", 2.0)  # net closed: heard, not logged
    s = admin.get("/api/state")[1]
    assert len(s["checkins"]) == 2 and s["heard"][0]["text"].startswith("November")


def test_first_time_tag(admin):
    admin.post("/api/net/open", {"name": "One"})
    admin.post("/api/checkin", {"call": "K5ABC"})
    admin.post("/api/net/close")
    admin.post("/api/net/open", {"name": "Two"})
    admin.post("/api/checkin", {"call": "K5ABC"})
    admin.post("/api/checkin", {"call": "W5BO"})
    c = {x["call"]: x["first_time"] for x in admin.get("/api/state")[1]["checkins"]}
    assert c == {"K5ABC": 0, "W5BO": 1}


def test_security_headers_and_spa(client):
    import urllib.request
    with urllib.request.urlopen(client.base + "/some/page") as r:
        assert r.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        assert b"<title>t</title>" in r.read()
    with urllib.request.urlopen(client.base + "/../../etc/passwd") as r:
        assert b"<title>t</title>" in r.read()
