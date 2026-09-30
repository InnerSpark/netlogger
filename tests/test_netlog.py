from netlogger import netlog


def test_checkins_flow(admin):
    assert admin.post("/api/checkin", {"call": "K5ABC"})[1]["error"] == "Open a net first."
    admin.post("/api/net/open", {"name": "Test Net"})
    netlog.log_text("Kilo Five Alpha Bravo Charlie, Dana, with traffic.", 2.0)
    netlog.log_text("Kilo Five Alpha Bravo Charlie, short time.", 2.0)  # same call: merge flags
    assert admin.post("/api/checkin", {"call": "hello"})[1]["error"] == "That doesn't look like a callsign."
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


def test_setup_status(admin, client, fake_ami):
    assert client.get("/api/setup")[0] == 401
    code, s = admin.get("/api/setup")
    assert code == 200 and s["logger_node"] == "1999" and s["node"]["configured"] and s["node"]["reachable"]
    assert "AMI_SECRET" not in str(s) and "s3cret" not in str(s)


def test_head_requests(client):
    import urllib.request
    r = urllib.request.Request(client.base + "/", method="HEAD")
    with urllib.request.urlopen(r) as resp:
        assert resp.status == 200 and resp.read() == b""


def test_clipped_call_snaps_to_known(admin, monkeypatch):
    from netlogger import config
    monkeypatch.setattr(config, "KNOWN_CALLS", ["W6UXD"])
    admin.post("/api/net/open", {"name": "Test"})
    netlog.log_text("This is W6U, it's the testing room.", 2.0)
    s = admin.get("/api/state")[1]
    assert [c["call"] for c in s["checkins"]] == ["W6UXD"]
    assert s["heard"][0]["calls"] == "W6UXD"


def test_calls_from_other_countries(admin, monkeypatch):
    looked_up = []
    import types
    fake = types.SimpleNamespace(request=types.SimpleNamespace(urlopen=lambda *a, **k: looked_up.append(a)))
    monkeypatch.setattr(netlog, "urllib", fake)  # only the logger's lookups, not the test client
    admin.post("/api/net/open", {"name": "DX"})
    netlog.log_text("Victor Echo Three Alpha Bravo Charlie, Toronto.", 2.0)
    assert admin.post("/api/checkin", {"call": "g4xyz"})[0] == 200
    calls = [(c["call"], c["valid"]) for c in admin.get("/api/state")[1]["checkins"]]
    assert calls == [("VE3ABC", None), ("G4XYZ", None)]  # no "Not found": callook can't check them
    assert looked_up == []
