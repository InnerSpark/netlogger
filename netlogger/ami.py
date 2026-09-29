"""Control the logger's private AllStar node through the Asterisk Manager Interface (AMI).

The logger node only ever links in monitor mode (ilink 2): it hears the other node
and never sends audio back. Each call opens a short AMI session and closes it.
"""
import re
import socket
import threading
import time

from . import config

NODE_RE = re.compile(r"^\d{3,7}$")


class AMIError(Exception):
    pass


def valid_node(node) -> bool:
    return bool(NODE_RE.match(str(node or "").strip()))


def _read_message(f):
    """One AMI message: 'Key: value' lines ending in a blank line."""
    lines = []
    while True:
        line = f.readline()
        if not line:
            raise AMIError("AllStar server closed the connection.")
        line = line.rstrip("\r\n")
        if line == "":
            if lines:
                return lines
            continue
        lines.append(line)


def command(cmd: str) -> str:
    """Run one Asterisk CLI command over AMI and return its output."""
    if not config.NODE_CONTROL:
        raise AMIError("Node control is off. Set AMI_HOST, AMI_USER and AMI_SECRET.")
    try:
        with socket.create_connection((config.AMI_HOST, config.AMI_PORT), timeout=5) as s:
            f = s.makefile("rw", encoding="utf-8", newline="")
            f.readline()  # banner
            f.write(f"Action: Login\r\nUsername: {config.AMI_USER}\r\nSecret: {config.AMI_SECRET}\r\nEvents: off\r\n\r\n")
            f.flush()
            resp = _read_message(f)
            if not any(l.lower() == "response: success" for l in resp):
                raise AMIError("AllStar server rejected the AMI login. Check AMI_USER and AMI_SECRET.")
            f.write(f"Action: Command\r\nCommand: {cmd}\r\nActionID: nl{int(time.time()*1000)}\r\n\r\n")
            f.flush()
            out = []
            first = _read_message(f)
            if any(l.lower() == "response: error" for l in first):
                output = " ".join(l.split(":", 1)[1].strip() for l in first if l.startswith("Output:"))
                if "No such command" in output:
                    raise AMIError("The AllStar server doesn't know 'rpt' commands. Is app_rpt (ASL3) running?")
                raise AMIError(output or next((l.split(":", 1)[1].strip() for l in first
                                                if l.lower().startswith("message:")), "Command failed."))
            if any(l.lower() == "response: follows" for l in first):
                # Older Asterisk: raw output ending in --END COMMAND--, usually all in one message
                done = False
                for l in first:
                    if l.startswith("--END COMMAND--"):
                        done = True
                        break
                    if not l.lower().startswith(("response:", "privilege:", "actionid:")):
                        out.append(l)
                while not done:
                    line = f.readline()
                    if not line or line.startswith("--END COMMAND--"):
                        break
                    out.append(line.rstrip("\r\n"))
            else:
                # Asterisk 14+: each line comes back as "Output: ..."
                out += [l.split(":", 1)[1][1:] if l.startswith("Output:") else l
                        for l in first if l.startswith("Output:")]
            f.write("Action: Logoff\r\n\r\n")
            f.flush()
            return "\n".join(out)
    except AMIError:
        raise
    except OSError as e:
        raise AMIError(f"Can't reach the AllStar server at {config.AMI_HOST}:{config.AMI_PORT} ({e.strerror or e}).")


def connect(node):
    node = str(node).strip()
    if not valid_node(node):
        raise AMIError("Node numbers are 3 to 7 digits.")
    command(f"rpt cmd {config.LOGGER_NODE} ilink 2 {node}")  # 2 = connect, monitor only


def disconnect(node):
    node = str(node).strip()
    if not valid_node(node):
        raise AMIError("Node numbers are 3 to 7 digits.")
    command(f"rpt cmd {config.LOGGER_NODE} ilink 1 {node}")  # 1 = disconnect


def parse_lstats(text: str):
    """Rows of `rpt lstats`: NODE PEER RECONNECTS DIRECTION CONNECT-TIME CONNECT-STATE."""
    links = []
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0].isdigit():
            links.append({
                "node": parts[0],
                "direction": parts[3] if len(parts) > 3 else "",
                "connected_for": parts[4] if len(parts) > 4 else "",
                "state": parts[5] if len(parts) > 5 else "",
            })
    return links


def links():
    """Nodes linked directly to the logger node."""
    return parse_lstats(command(f"rpt lstats {config.LOGGER_NODE}"))


# ---------- status cache, so every open dashboard doesn't hit AMI ----------
_status = {"links": [], "error": None, "at": 0}
_status_lock = threading.Lock()


def status(max_age=3):
    with _status_lock:
        if time.time() - _status["at"] < max_age:
            return dict(_status)
    try:
        result = {"links": links(), "error": None}
    except AMIError as e:
        result = {"links": [], "error": str(e)}
    with _status_lock:
        _status.update(result, at=time.time())
        return dict(_status)


def invalidate():
    with _status_lock:
        _status["at"] = 0


def auto_connect_loop():
    """At startup, link DEFAULT_NODE when AUTO_CONNECT is on. Retries until it works, then stops,
    so a manual disconnect from the dashboard sticks."""
    while True:
        try:
            if not any(l["node"] == config.DEFAULT_NODE for l in links()):
                connect(config.DEFAULT_NODE)
                print(f"auto-connected to node {config.DEFAULT_NODE}", flush=True)
                invalidate()
            return
        except AMIError as e:
            print("auto-connect, retrying in 30s:", e, flush=True)
        time.sleep(30)
