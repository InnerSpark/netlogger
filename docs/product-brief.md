# Net Logger Product Brief

**One-liner:** A receive-only logger that listens to an AllStar node during a ham radio net, writes down every check-in, and gives net control a live roster.
**Status:** Beta (1.0.0 not tagged yet)
**Release type:** Public release, free and open source (AGPL-3.0)

## Problem
- Net control runs the net and logs check-ins by hand at the same time. Calls get missed or written down wrong.
- Logs end up on paper or in a spreadsheet, so nobody can see who checks in over time.
- Existing tools need a person typing, or a paid service.

## Audience
- Primary user: net control operators on AllStar-linked nets.
- Secondary user: club admins who keep records and stats, and hams who self-host.
- Accessibility needs: screen reader and keyboard users (some hams are blind or low vision), phone use outdoors, older eyes.

## What it does
- Listens to a node in monitor mode and transcribes speech locally (Whisper).
- Picks callsigns out of phonetics and plain speech, from any country, and builds the roster.
- Live dashboard: roster, flags, last heard, add or fix calls, node link control.
- Scheduled nets, past nets with transcripts, stats, CSV export.
- Optional push to a companion iOS app.
- Out of scope: transmitting, running the net for you, logging outside AllStar (radio sound card is on the roadmap).

## Competitors and alternatives
| Product | What it does well | Where it falls short | Price |
|---|---|---|---|
| Paper or spreadsheet | Zero setup | Manual, error-prone, no history | Free |
| NetLogger (the Windows program) | Long-standing, shared logging | Manual typing, Windows only | Free |
| Online check-in forms | Easy for participants | Doesn't hear the net, extra step | Free to paid |

## Why this wins
- Hands-free: it hears the net, nobody types.
- Runs on the AllStar server you already have. No cloud service, no subscription.
- Never transmits, so nothing changes on the air.

## Success looks like
- A full net logged with 95%+ of calls right without anyone typing.
- Other clubs install it from the README without help.
- Net control spends the net talking, not writing.
