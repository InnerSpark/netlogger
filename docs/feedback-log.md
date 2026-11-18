# Net Logger Feedback Log

| Date | From | Feedback | Action taken | Status |
|---|---|---|---|---|
| 2026-09-29 | self | Whisper wrote "Niner. Stations." on static | Prompt echo and hallucination filters, voice activity filter | Done |
| 2026-09-29 | self | Users must hold a valid license | License-checked accounts | Done |
| 2026-09-29 | self | Need scheduled nets and old net logs | Schedules, Nets page, transcripts | Done |
| 2026-09-29 | self | Want stats over time | Stats page | Done |
| 2026-09-29 | self | "Stats" and "Status" look too alike | Status renamed Health | Done |
| 2026-09-29 | self | Net controllers and participants in other countries | Callsigns from any country, admin-confirmed licenses | Done |
| 2026-09-29 | self | Phone nav should be a hamburger | Menu button under 768px | Done |
| 2026-09-29 | AccessSpark scans | Reflow, focus, contrast, live regions | Fixed; see accessibility-audit.md | Done |
| 2026-11-04 | self | Last heard looked stale with only times | Day plus time ("Today 2:04 PM") | Done |
| 2026-11-04 | self | "This is W6UXD testing" came out "technical" | Common net words in the prompt | Done |
| 2026-11-04 | self | Confused why it uses node 1999, not 64658 | Explained; rename in the app is on the roadmap | Open |
| 2026-11-04 | self | Supermon site disappeared after an update | Same-server doc: re-check Apache sites after updates | Done |

## Patterns
- Speech to text quality comes up most. The prompt, known calls and the parser carry a lot.
- Words on screen matter: names that look alike and times without days caused confusion.
