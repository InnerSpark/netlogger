"""All settings come from environment variables (see .env.example)."""
import os
from pathlib import Path


def _bool(name, default=False):
    return os.environ.get(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


def _int(name, default):
    return int(os.environ.get(name, default))


DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "netlog.db"))
WEB_DIR = Path(os.environ.get("WEB_DIR", Path(__file__).resolve().parent.parent / "web" / "dist")).resolve()

HTTP_HOST = os.environ.get("HTTP_HOST", "0.0.0.0")
HTTP_PORT = _int("HTTP_PORT", 8080)
USRP_PORT = _int("USRP_PORT", 34001)

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
MIN_SECONDS = float(os.environ.get("MIN_SECONDS", 0.8))
CALL_LOOKUP = _bool("CALL_LOOKUP", True)
FAKE_TRANSCRIPTS = os.environ.get("NETLOG_FAKE_TRANSCRIPTS")  # testing only

# AllStar node control over the Asterisk Manager Interface. Off when AMI_HOST is blank.
AMI_HOST = os.environ.get("AMI_HOST", "").strip()
AMI_PORT = _int("AMI_PORT", 5038)
AMI_USER = os.environ.get("AMI_USER", "")
AMI_SECRET = os.environ.get("AMI_SECRET", "")
LOGGER_NODE = os.environ.get("LOGGER_NODE", "1999").strip()
DEFAULT_NODE = os.environ.get("DEFAULT_NODE", "").strip()
AUTO_CONNECT = _bool("AUTO_CONNECT", False)

# Accounts
COOKIE_SECURE = _bool("COOKIE_SECURE", False)  # set when serving over HTTPS
SESSION_DAYS = _int("SESSION_DAYS", 30)

NODE_CONTROL = bool(AMI_HOST and AMI_USER and AMI_SECRET)
