# Net Logger Roadmap

## Now
- Pass the 1.0.0 pen test: live checks, then tag `v1.0.0` after a real net checks out.
- Move CI and the build to Node 24 and current GitHub Actions versions (Node 20 actions are gone).
- A real VoiceOver and NVDA pass through the main flows.

## Next
- Auto-update: the server checks for new tagged releases and installs them.
- Net report after each net (CSV or summary to the net's admins).
- Light-mode muted text to AAA contrast.
- Name lookups outside the US (HamQTH or QRZ with the owner's own account).
- Rate limits on signed-in actions (pen test #8).

## Later
- Radio sound-card input, for nets that aren't on AllStar.
- Info on demand (receive-only answers on the dashboard, never on air).
- Clearer name for the logger's node in the app ("Listener for 64658").

## Parked
| Idea | Why parked | Revisit when |
|---|---|---|
| Transmitting anything (announcements, IDs) | FCC rules and the receive-only promise | Never, by design |
| Native iOS app in this repo | It's Mike's private app, built on Flint | If Flint goes public |
