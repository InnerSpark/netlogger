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
WHISPER_THREADS = _int("WHISPER_THREADS", 0)  # 0 = all cores; cap it on a shared server
MIN_SECONDS = float(os.environ.get("MIN_SECONDS", 0.8))
CALL_LOOKUP = _bool("CALL_LOOKUP", True)
# Calls to expect (net regulars, NCS), comma separated. Helps speech to text and fixes clipped calls.
KNOWN_CALLS = [c.strip().upper() for c in os.environ.get("KNOWN_CALLS", "").split(",") if c.strip()]
# Keep the last N transmissions as WAV files in DATA_DIR/audio for tuning (0 = off)
SAVE_AUDIO = _int("SAVE_AUDIO", 0)
FAKE_TRANSCRIPTS = os.environ.get("NETLOG_FAKE_TRANSCRIPTS")  # testing only

# AllStar node control over the Asterisk Manager Interface. Off when AMI_HOST is blank.
AMI_HOST = os.environ.get("AMI_HOST", "").strip()
AMI_PORT = _int("AMI_PORT", 5038)
AMI_USER = os.environ.get("AMI_USER", "")
AMI_SECRET = os.environ.get("AMI_SECRET", "")
LOGGER_NODE = os.environ.get("LOGGER_NODE", "1999").strip()
DEFAULT_NODE = os.environ.get("DEFAULT_NODE", "").strip()
AUTO_CONNECT = _bool("AUTO_CONNECT", False)

# Set to 1 when a reverse proxy (Apache, nginx, Caddy) sits in front. The client IP is then
# read from X-Forwarded-For, so login throttling applies per person, not to the proxy.
TRUST_PROXY = _bool("TRUST_PROXY", False)
# Behind Cloudflare, set to CF-Connecting-IP so each visitor is throttled separately
CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "").strip()

# Accounts
# Dashboard accounts must belong to a licensed amateur (checked on callook.info, US calls)
REQUIRE_LICENSE = _bool("REQUIRE_LICENSE", True)
LICENSE_RECHECK_DAYS = _int("LICENSE_RECHECK_DAYS", 30)
COOKIE_SECURE = _bool("COOKIE_SECURE", False)  # set when serving over HTTPS
SESSION_DAYS = _int("SESSION_DAYS", 30)

NODE_CONTROL = bool(AMI_HOST and AMI_USER and AMI_SECRET)

# Push notifications and Live Activities for the iOS app (Apple Push Notification service).
# Off unless all four are set. The key is a .p8 from Apple Developer > Keys, with APNs enabled.
APNS_KEY_FILE = os.environ.get("APNS_KEY_FILE", "").strip()
APNS_KEY_ID = os.environ.get("APNS_KEY_ID", "").strip()
APNS_TEAM_ID = os.environ.get("APNS_TEAM_ID", "").strip()
APNS_TOPIC = os.environ.get("APNS_TOPIC", "").strip()  # the app's bundle ID
PUSH = bool(APNS_KEY_FILE and APNS_KEY_ID and APNS_TEAM_ID and APNS_TOPIC)
# During an open net, warn after this many minutes with no audio from AllStar (0 = never)
AUDIO_ALERT_MIN = _int("AUDIO_ALERT_MIN", 5)
# Running on the AllStar server itself (install.sh)
SAME_HOST = AMI_HOST in ("127.0.0.1", "localhost", "::1")
