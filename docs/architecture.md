# Net Logger Architecture

## Stack
- Platform: Linux server (an ASL3 AllStar server, or any machine with Docker).
- Language and frameworks: Python 3.11 standard library HTTP server, SQLite, faster-whisper (CTranslate2), numpy. Dashboard: React 19, Vite, Tailwind v4, stock shadcn/ui, TypeScript.
- Hosting and backend: self-hosted. `install.sh` (systemd service) or Docker. A reverse proxy (Apache, nginx, Caddy, Cloudflare) adds HTTPS.

## Data flow
1. AllStar node links to the logger's private node (default 1999) in **monitor** mode. The logger never transmits.
2. `app_rpt` sends that node's audio to the logger as USRP packets (UDP 34001, 8 kHz).
3. `audio.listener` groups packets into transmissions. `audio.transcriber` cleans the audio and runs Whisper.
4. `netlog.log_text` saves every transcript. While a net is open, `parser` pulls callsigns and flags and `add_checkin` adds the first call to the roster.
5. `netlog.lookup` fills name and class from callook.info (US calls only).
6. The dashboard polls `/api/state` every 2 seconds. The iOS app polls every 3.
7. `schedule.tick` (every 30 s) opens and closes scheduled nets and links or unlinks the node over AMI.
8. With push on, `push.py` sends alerts and Live Activity updates through Apple's push service.

## Integrations
| Service or device | How we connect | Auth | Notes |
|---|---|---|---|
| Asterisk / app_rpt | USRP audio in, UDP | Source address (`USRP_HOST`, `USRP_ALLOW`) | Receive only |
| Asterisk Manager (AMI) | TCP 5038 | `AMI_USER` / `AMI_SECRET`, 127.0.0.1 only | `rpt cmd ilink 2/1`, `rpt lstats` |
| callook.info | HTTPS GET | None | US license check and lookups |
| Apple Push (APNs) | HTTPS, HTTP/2 | ES256 token from a `.p8` key | Optional, off by default |
| Hugging Face (model download) | HTTPS, first run | None | Whisper weights cached in `DATA_DIR/models` |

## Local setup
1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`
2. `cd web && npm ci && npm run build`
3. `cp .env.example .env`, then `python -m netlogger`
4. Tests: `python -m pytest`. Attacks only: `python -m pytest tests/test_pentest.py`
5. Without a radio: `tools/replay.py some.wav` plays a recording into the USRP port.

## Known limits
- One open net at a time.
- Name lookups are US only.
- Speech to text needs 2+ CPU cores and 2+ GB of free memory for useful accuracy.
- Polling, not push, for the dashboard.
