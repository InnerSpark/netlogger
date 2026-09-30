import sqlite3

from netlogger import __main__ as cli, config, db


def test_reset_password(admin, client, capsys):
    assert cli.reset_password("w6abc") == 0          # by callsign, any case
    pw = capsys.readouterr().out.split(": ", 1)[1].split()[0]
    assert admin.get("/api/state")[0] == 401         # old sessions are gone
    assert client.post("/api/auth/login", {"username": "ncs", "password": pw})[0] == 200
    assert cli.reset_password("nobody") == 1


def test_backup(admin, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")  # the server fixture's database
    db.insert("INSERT INTO nets (name, opened) VALUES ('Kept', 1)")
    for _ in range(12):
        (tmp_path / "backups").mkdir(exist_ok=True)
        cli.backup()
    files = sorted((tmp_path / "backups").glob("netlog-*.db"))
    assert 1 <= len(files) <= cli.KEEP_BACKUPS
    names = [r[0] for r in sqlite3.connect(files[-1]).execute("SELECT name FROM nets")]
    assert names == ["Kept"]
    out = tmp_path / "copy.db"
    assert cli.backup(str(out)) == 0 and out.exists()
