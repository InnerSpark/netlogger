# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] - not yet released

First public release.

### Logging
- Receive-only logging from an AllStar private node over USRP. The logger never transmits.
- Local speech to text with Whisper (faster-whisper). Audio cleanup first: removes DC and low rumble, levels quiet signals.
- Whisper ignores static, tones and CW IDs: voice activity filter, drops low-confidence and looping segments, drops transcripts that only read the prompt back, strips stock caption phrases.
- Callsigns from any country (ITU format), spoken in phonetics or written: W6UXD, VE3ABC, G4XYZ, 2E0ABC, VK2ABC. Parser handles possessives ("Six's"), "whisky", "ex-ray", "fife", "tree", "niner".
- Whisper prompt includes the phonetic alphabet and calls this logger has seen. `KNOWN_CALLS` adds net regulars and net control.
- Clipped or garbled calls snap to a known call when only one fits (W6U -> W6UXD, "five K G X" -> KE5KGX).
- Traffic, short-time and recheck flags from speech.
- Name and license class lookup from callook.info for US calls.

### Dashboard
- Live roster, recheck list, last heard (with one-tap Add for calls not on the roster), manual add, fix call, CSV export.
- Node control over AMI: connect (monitor only), disconnect, list links, optional auto-connect.
- Scheduled nets: weekly, monthly or one time. Opens the net, links the node, closes on time and unlinks. The Dashboard shows the next one.
- Nets page: every past net with roster, searchable transcript, CSV and transcript downloads.
- Stats page: check-ins per net over time (returning vs first time), typical check-ins vs the previous period, stations heard, first-timers, regulars with attendance. Filter by range and scheduled net.
- Health page (admins): live health checks, plus an AllStar setup guide with your values filled in that opens itself when something breaks.
- Works on a phone, light and dark mode, screen reader and keyboard friendly (WCAG 2.2 AA).

### Accounts and security
- Accounts for licensed hams only: callsign checked against the FCC database (callook.info) at setup and when adding users, re-checked every 30 days. Admins confirm licenses from other countries; a first admin outside the US is accepted as entered. `REQUIRE_LICENSE=0` turns it off.
- Admin and operator roles, password change and reset, scrypt hashes, login throttling.
- Reverse proxy support (`TRUST_PROXY`, plus `CLIENT_IP_HEADER` for Cloudflare).
- `netlogger reset-password` for a locked-out admin.

### Install and operations
- `install.sh` for ASL3 servers: adds the logger node and AMI user through include files without editing existing node settings, backs up every file it touches, runs under systemd at lower priority than Asterisk, refuses to install with under 1 GB of free memory. `uninstall.sh` reverses it.
- `netlogger backup` copies the database safely while running. The installer backs up before every upgrade.
- Docker image and compose file.
- `SAVE_AUDIO` keeps recent transmissions as WAV, and `tools/tune.py` compares Whisper models on them. `tools/replay.py` plays a recording in for testing.
