# Contributing

Thanks for helping. Bug reports, parser fixes, and new callsign formats are the most useful contributions.

## Ground rules

- **Receive-only stays receive-only.** Pull requests that make Net Logger transmit won't be merged into the core. Transmitting needs station ID, a control operator, and trustee approval, and belongs in a separate, opt-in project.
- **Accessibility is required.** UI changes must work with a keyboard and a screen reader (VoiceOver or NVDA) and pass WCAG 2.2 AA.
- **Keep it simple.** Small, focused changes. No new dependency without a good reason.
- **Update docs and tests in the same pull request** as the behavior change.

## Layout

| Path | What |
|---|---|
| `netlogger/` | Python backend (standard library HTTP server, SQLite) |
| `netlogger/parser.py` | Transcript → callsigns and flags. Most fixes land here |
| `netlogger/audio.py` | USRP listener and Whisper transcription |
| `netlogger/ami.py` | AllStar node control over AMI |
| `netlogger/auth.py` | Accounts, passwords, sessions |
| `netlogger/web.py` | API routes |
| `web/` | Dashboard: React, Vite, Tailwind, shadcn/ui |
| `tests/` | pytest suite, including a fake AMI server |
| `tools/replay.py` | Replays a recording as if it came from a node |

## Run it locally

Python 3.11 and Node 22 (see `.nvmrc`).

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cd web && npm ci && npm run build && cd ..
DATA_DIR=./data python3 -m netlogger
```

Dashboard at http://localhost:8080.

For UI work, run the dev server alongside it (hot reload, proxies `/api` to :8080):

```
cd web && npm run dev
```

Without a node, set `NETLOG_FAKE_TRANSCRIPTS=path/to/lines.txt` (one line per transmission) and replay any audio with `python3 tools/replay.py some.wav`.

## Tests

```
python3 -m pytest
cd web && npm run build    # typecheck + build
```

Parser bugs: add the exact transcript line to `tests/test_parser.py` first, see it fail, then fix.

## Pull requests

1. Fork, branch from `main`.
2. Make the change with tests.
3. `python3 -m pytest` and `npm run build` pass.
4. Add a line to `CHANGELOG.md` under **Unreleased**.
5. Open the pull request with what changed and how you tested it.

By contributing, you agree your work is licensed under AGPL-3.0, the same as the project.
