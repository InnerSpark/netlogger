# Net Logger Design

## Design system
- System: stock shadcn/ui, neutral theme, light and dark. Not Flint: Flint is private and this repo is public ([decision 0005](decisions/0005-stock-shadcn-not-flint.md)).
- Tokens and components used: shadcn tokens (`--background`, `--foreground`, `--muted-foreground`, `--destructive`, `--ring`), Button, Card, Input, Label, Table, Dialog, AlertDialog, Badge, NativeSelect. Two chart colors (`--series-1`, `--series-2`), checked for color-blind separation.
- Custom components and why:
  - Scroll-aware Table: becomes a named, focusable region only when it scrolls sideways.
  - Phone Menu: a disclosure button, not a modal, so focus and reading order stay simple.
  - Stats chart: hand-built SVG with a table view, so every value is reachable without the picture.

## Accessibility standard
- WCAG 2.2 AAA wherever achievable. AA is the floor.
- Contrast: 7:1 normal text, 4.5:1 large text. Color is never the only signal (flags have text, chart has a legend and table).
- Type: line height 1.5 or more for body text, paragraphs under 80 characters, no justified text, no images of text.
- 200% zoom and 320px width without sideways page scrolling.
- Focus: visible 2px ring; skip link and page changes move focus to the page heading and keep it there.
- Errors: `role="alert"`, `aria-invalid`, focus moves to the field.
- Exceptions: muted text in light mode is 4.7:1 (AA, not AAA). See [accessibility-audit.md](accessibility-audit.md).

## Key flows
| Flow | Steps | Notes |
|---|---|---|
| First run | Open dashboard, enter setup code, callsign, password | Setup code is in the server log |
| Run a net | Open net (or let the schedule), watch roster, fix or flag calls, close net | Roster updates every 2 s |
| Link a node | Health or Dashboard, Listen to default node or another | Monitor only |
| Review a past net | Nets, View, search transcript, CSV | |
| Stats | Stats, pick range and net, Show table | |

## Open design questions
- Bring muted text to 7:1 in light mode without losing hierarchy.
- Whether operators should see Health in read-only form.
