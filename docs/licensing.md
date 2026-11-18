# Net Logger Licensing

**Project license:** AGPL-3.0
**Why:** [decisions/0001-agpl-license.md](decisions/0001-agpl-license.md). Free for every ham; anyone who runs a changed copy as a service has to share their changes.

## Dependencies and assets
### Server (Python, shipped)
| Name | Type | License | Copyleft? | Notes |
|---|---|---|---|---|
| faster-whisper | package | MIT | No | Speech to text |
| CTranslate2 | package | MIT | No | Pulled in by faster-whisper |
| PyAV | package | BSD-3-Clause | Weak, bundled | Its wheels bundle FFmpeg libraries under LGPL-2.1. Dynamically linked; fine for AGPL. We don't decode files with it (USRP audio is raw PCM) |
| onnxruntime | package | MIT | No | Silero VAD in faster-whisper |
| tokenizers, huggingface_hub | package | Apache-2.0 | No | Model loading |
| numpy | package | BSD-3-Clause | No | Audio math |
| tzdata | package | Apache-2.0 | No | Time zones for schedules |
| httpx, httpcore | package | BSD-3-Clause | No | Apple push over HTTP/2 |
| h2, hpack, hyperframe | package | MIT | No | HTTP/2 |
| cryptography | package | Apache-2.0 or BSD-3-Clause | No | ES256 token for Apple push |
| Whisper model weights (Systran faster-whisper conversions of OpenAI Whisper) | model | MIT | No | Downloaded on first run, not in the repo |
| Silero VAD model | model | MIT | No | Ships inside faster-whisper |

### Dashboard (shipped in `web/dist`)
| Name | Type | License | Copyleft? | Notes |
|---|---|---|---|---|
| React, React DOM | package | MIT | No | |
| Radix UI (alert-dialog, dialog, label, slot, toggle) | package | MIT | No | |
| shadcn/ui components | copied source | MIT | No | Stock theme, in `web/src/components/ui` |
| lucide-react | icons | ISC | No | |
| class-variance-authority | package | Apache-2.0 | No | |
| clsx, tailwind-merge, tw-animate-css | package | MIT | No | |

### Build and test only (not shipped)
| Name | License |
|---|---|
| Vite, @vitejs/plugin-react, Tailwind CSS, @tailwindcss/vite | MIT |
| TypeScript | Apache-2.0 |
| pytest | MIT |
| pip-audit | Apache-2.0 |

## Rules
- Flag GPL, AGPL, or any restrictive license before adding it.
- Fonts and icon sets need a license that allows embedding. The dashboard uses system fonts only.
- No trademarks or logos from other companies without permission.
- Flint (the private design system) stays out of this repo.

## Third-party trademarks and APIs
- **AllStarLink, Asterisk:** named to say what the logger works with. No logos.
- **callook.info:** free public API. One lookup per new callsign, cached in memory. Credited in the README.
- **Apple Push:** used only when the server owner adds their own key.
- **Cloudflare, Apache:** named in setup docs only.
