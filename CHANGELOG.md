# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Scheduled nets: weekly, monthly or one time. Opens the net, links the node in monitor mode, closes on time and unlinks. Dashboard shows the next one.
- Nets page: past nets with roster, searchable transcript, CSV and transcript downloads.
- Accounts require a current amateur license: callsign checked against the FCC database (callook.info) at setup and when adding users, re-checked every 30 days at login. Admins can vouch for non-US licenses. Older accounts verify once at next login. `REQUIRE_LICENSE=0` turns it off.
- Audio cleanup before speech to text: removes DC and low rumble, levels quiet signals.
- Whisper prompt includes the phonetic alphabet and calls this logger has seen, so it leans toward them.
- `KNOWN_CALLS` setting for net regulars and net control.
- Clipped or garbled calls snap to a known call when only one fits (W6U -> W6UXD, "five K G X" -> KE5KGX).
- Last heard shows calls not yet on the roster with a one-tap Add button.
- `SAVE_AUDIO` keeps recent transmissions as WAV files, and `tools/tune.py` compares Whisper models on them.

### Fixed
- Whisper no longer invents text for static, tones and CW IDs: voice activity filter, drops low-confidence and looping segments, drops transcripts that only read the prompt back, and strips stock caption phrases ("New videos every week!").
- Parser handles possessives ("Six's"), "Whisky", "ex-ray", "fife", "tree", "niner".

## [1.0.0] - 2026-10-02

### Added
- Receive-only logging from an AllStar private node over USRP.
- Local speech to text with Whisper (faster-whisper).
- Callsign parser for spoken phonetics and written calls (US formats).
- Traffic, short-time, and recheck flags from speech.
- Live dashboard: roster, recheck list, last heard, manual add, fix call, CSV export.
- Name and license class lookup from callook.info.
- Node control over AMI: connect (monitor only), disconnect, list links, optional auto-connect.
- Accounts: first-run admin setup, admin and operator roles, password change and reset.
- Setup page: live status checklist and AllStar setup steps with your values filled in and copy buttons.
- `install.sh` for ASL3 servers: adds the logger node and AMI user through include files without editing existing node settings, backs up every file, runs under systemd at lower priority than Asterisk, and refuses to install with under 1 GB of free memory. `uninstall.sh` reverses it.
- Reverse proxy support (`TRUST_PROXY`, plus `CLIENT_IP_HEADER` for Cloudflare) so login throttling works per person behind Apache, nginx, or Caddy.
- Docker image and compose file.
