# Net Logger Privacy

Everything stays on the server that runs the logger. There's no Net Logger service and nothing phones home.

## Data we collect
| Data | Why | Stored where | Shared with | Linked to user? |
|---|---|---|---|---|
| Audio from the linked node | Speech to text | Memory only. WAV copies only if `SAVE_AUDIO` is on (last N, on the server) | No one | No |
| Transcripts of what was said on air | Last heard, net logs, search | Server SQLite | Signed-in users of that logger | No (on-air speech, public by license rules) |
| Callsigns, names, locations, license class of stations heard | Roster and stats | Server SQLite | Signed-in users | Yes, per callsign |
| Dashboard accounts: username, callsign, license name and class, password hash | Sign-in and the license check | Server SQLite | Admins see the user list | Yes |
| Session tokens (hashed) | Staying signed in | Server SQLite, 30 days | No one | Yes |
| Client IP of failed sign-ins | Throttling and the log | Memory, plus the server log | Server owner | No |
| Push device tokens (optional) | Alerts to the iOS app | Server SQLite | Apple, to deliver the push | Yes |

## Data we don't collect
- No analytics, tracking pixels, ads or crash reporting.
- No location from devices.
- No audio leaves the server.

## Outside services
- **callook.info:** gets a callsign, to look up a US license. Nothing else.
- **Apple Push:** gets a device token and the alert text, only if the server owner turns push on.
- **Hugging Face:** model download on first run. No user data.

## Tracking
- Analytics: none
- Ads: none
- Crash reporting: none

## App Store privacy label summary
n/a: the logger isn't an App Store app. See netlogger-ios for the iOS app's label.

## Privacy policy URL
- Each server owner is responsible for their install. This page is the template they can link to.
