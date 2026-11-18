# Net Logger Accessibility Audit

**Standard:** WCAG 2.2 AAA where achievable, AAA required for contrast, color, and type
**Last full audit:** 2026-09-29 (automated and keyboard), plus two AccessSpark scans of the live site

## Test setup
- Devices and OS versions: Chromium (Playwright) at 1280px, 390px and 320px wide, light and dark.
- Screen readers: none by a person yet. Accessibility tree checked by script (names, roles, focus).
- Tools: axe-core (wcag2a, wcag2aa, wcag21aa, wcag22aa), AccessSpark, Playwright focus sampling over 700 ms.

## Results
| Date | Screen or flow | Criterion | Result | Notes |
|---|---|---|---|---|
| 2026-09-29 | All pages, light and dark, desktop and phone | axe WCAG 2.2 A/AA | Pass | 0 violations after fixes |
| 2026-09-29 | Skip link, nav, page changes | 2.4.3, 2.4.7 | Pass | Focus lands on the h1 and stays |
| 2026-09-29 | 320px width | 1.4.10 Reflow | Pass | Wide tables scroll inside a named region |
| 2026-09-29 | Phone Menu | 4.1.2 | Pass | aria-expanded, aria-controls, Escape returns focus |
| 2026-09-29 | Tap targets | 2.5.8 | Pass | 44px on phones, 24px minimum on desktop |
| 2026-09-29 | Error messages | 3.3.1, 4.1.3 | Pass | role=alert, focus to field |
| 2026-09-29 | Motion | 2.3.3 | Pass | prefers-reduced-motion respected |
| 2026-09-29 | Muted text, light mode | 1.4.6 Contrast (Enhanced) | Exception | 4.7:1, AA only |
| 2026-11-18 | Setup code field (new) | 1.3.1, 3.3.2 | Not tested | Label and hint added; re-run axe |

## Exceptions
| Criterion | Why it can't meet AAA | Decision record |
|---|---|---|
| 1.4.6 Contrast (Enhanced), light-mode muted text | Stock shadcn theme; changing it means leaving stock | [0005](decisions/0005-stock-shadcn-not-flint.md) |

## Needs re-testing
- First-run screen with the new setup code field.
- A real VoiceOver (macOS and iOS) and NVDA pass through: sign in, open a net, fix a call, close a net.

## Conformance summary
- The dashboard meets WCAG 2.2 AA in automated and keyboard testing, in light and dark, on desktop and phone. Muted text in light mode is AA, not AAA. Screen reader testing by a person is still to do.
