import json
import socket
import socketserver
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from netlogger import auth, config, db
from netlogger.web import Handler


class FakeAMI(socketserver.ThreadingTCPServer):
    """Speaks just enough AMI: Login, Command (rpt lstats / rpt cmd ilink), Logoff."""
    allow_reuse_address = True

    def __init__(self, secret="s3cret", new_style=True):
        self.secret, self.new_style, self.links, self.commands = secret, new_style, [], []
        self.no_app_rpt = False
        super().__init__(("127.0.0.1", 0), FakeAMIHandler)


class FakeAMIHandler(socketserver.StreamRequestHandler):
    def send(self, text):
        self.wfile.write(text.encode())

    def read_msg(self):
        msg = {}
        while True:
            line = self.rfile.readline().decode()
            if not line:
                return None
            line = line.strip()
            if not line:
                if msg:
                    return msg
                continue
            k, _, v = line.partition(":")
            msg[k.strip().lower()] = v.strip()

    def handle(self):
        srv = self.server
        self.send("Asterisk Call Manager/7.0.3\r\n")
        while (m := self.read_msg()) is not None:
            action = m.get("action", "").lower()
            if action == "login":
                ok = m.get("secret") == srv.secret
                self.send(f"Response: {'Success' if ok else 'Error'}\r\nMessage: {'Authentication accepted' if ok else 'Authentication failed'}\r\n\r\n")
                if not ok:
                    return
            elif action == "command":
                cmd = m["command"]
                srv.commands.append(cmd)
                parts = cmd.split()
                out = []
                if srv.no_app_rpt and parts[0] == "rpt":
                    self.send(f"Response: Error\r\nMessage: Command output follows\r\nOutput: No such command '{cmd}' (type 'core show help {cmd}' for other possible commands)\r\n\r\n")
                    continue
                if parts[:2] == ["rpt", "lstats"]:
                    out = ["NODE      PEER                RECONNECTS  DIRECTION  CONNECT TIME        CONNECT STATE",
                           "----      ----                ----------  ---------  ------------        -------------"]
                    out += [f"{n:<10}10.0.0.5            0           OUT        00:01:02:003        ESTABLISHED" for n in srv.links]
                elif parts[:2] == ["rpt", "cmd"] and parts[3] == "ilink":
                    node = parts[5]
                    if parts[4] == "2" and node not in srv.links:
                        srv.links.append(node)
                    if parts[4] == "1" and node in srv.links:
                        srv.links.remove(node)
                if srv.new_style:
                    body = "".join(f"Output: {l}\r\n" for l in out)
                    self.send(f"Response: Success\r\nMessage: Command output follows\r\n{body}\r\n")
                else:
                    self.send("Response: Follows\r\nPrivilege: Command\r\n" + "".join(l + "\n" for l in out) + "--END COMMAND--\r\n\r\n")
            elif action == "logoff":
                self.send("Response: Goodbye\r\n\r\n")
                return


@pytest.fixture
def fake_ami(monkeypatch):
    srv = FakeAMI()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "AMI_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "AMI_PORT", srv.server_address[1])
    monkeypatch.setattr(config, "AMI_USER", "netlogger")
    monkeypatch.setattr(config, "AMI_SECRET", "s3cret")
    monkeypatch.setattr(config, "LOGGER_NODE", "1999")
    monkeypatch.setattr(config, "NODE_CONTROL", True)
    from netlogger import ami
    ami.invalidate()
    yield srv
    srv.shutdown()


# Stand-in for callook.info so tests never touch the network
FAKE_LICENSES = {
    "W6ABC": {"status": "VALID", "name": "PAT SAMPLE", "current": {"operClass": "EXTRA"},
              "otherInfo": {"expiryDate": "01/01/2099"}},
    "K5OPR": {"status": "VALID", "name": "SAM OPERATOR", "current": {"operClass": "GENERAL"},
              "otherInfo": {"expiryDate": "01/01/2099"}},
    "KE5OLD": {"status": "VALID", "name": "OLD TIMER", "current": {"operClass": "GENERAL"},
               "otherInfo": {"expiryDate": "01/01/2001"}},
}


@pytest.fixture(autouse=True)
def fake_callook(monkeypatch):
    from netlogger import license
    state = {"down": False}

    def fetch(call):
        if state["down"]:
            raise license.LookupUnavailable("down")
        return FAKE_LICENSES.get(call, {"status": "INVALID"})
    monkeypatch.setattr(license, "fetch", fetch)
    return state


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CALL_LOOKUP", False)
    monkeypatch.setattr(config, "WEB_DIR", tmp_path)
    (tmp_path / "index.html").write_text("<!doctype html><title>t</title>")
    db.connect(tmp_path / "t.db")
    auth._fails.clear()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


class Client:
    """Tiny HTTP client that keeps the session cookie."""

    def __init__(self, base):
        self.base, self.cookie = base, None

    def req(self, method, path, body=None, ctype="application/json"):
        data = json.dumps(body or {}).encode() if method == "POST" else None
        r = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            r.add_header("Content-Type", ctype)
        if self.cookie:
            r.add_header("Cookie", self.cookie)
        try:
            with urllib.request.urlopen(r) as resp:
                code, raw, headers = resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            code, raw, headers = e.code, e.read(), e.headers
        sc = headers.get("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        try:
            return code, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return code, raw.decode()

    def get(self, path):
        return self.req("GET", path)

    def post(self, path, body=None, **kw):
        return self.req("POST", path, body, **kw)


@pytest.fixture
def client(server):
    return Client(server)


@pytest.fixture
def admin(server):
    c = Client(server)
    code, _ = c.post("/api/auth/setup", {"username": "ncs", "callsign": "W6ABC", "password": "correct horse"})
    assert code == 200
    return c
