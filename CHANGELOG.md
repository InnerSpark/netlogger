# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
- `install.sh` for ASL3 servers: adds the logger node and AMI user through include files without editing existing node settings, backs up every file, runs under systemd at lower priority than Asterisk. `uninstall.sh` reverses it.
- Reverse proxy support (`TRUST_PROXY`) so login throttling works per person behind Apache, nginx, or Caddy.
- Docker image and compose file.
