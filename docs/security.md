# Net Logger Security

## Secrets and keys
| Secret | Used for | Stored where | Rotated |
|---|---|---|---|
| `AMI_SECRET` | Linking and unlinking the node | `/etc/netlogger/netlogger.env` (root:netlogger 640) and Asterisk `manager.conf` include | Re-run `install.sh` |
| `APNS_KEY_FILE` (.p8) | Push to the iOS app | Server file, root:netlogger 640. Never in git (`*.p8` ignored, secret scan blocks it) | Revoke in Apple Developer, make a new key |
| Session tokens | Dashboard sign-in | SQLite, SHA-256 hashed. Raw token only in the HttpOnly cookie | On every sign-in; 30-day expiry |
| Passwords | Accounts | SQLite, scrypt (n=2^14) | User changes it, or `netlogger reset-password` |
| Setup code | Creating the first admin | Memory only, printed to the log at startup (or `SETUP_CODE`) | Cleared once an admin exists |

## Rules
- No secrets in the repo. Ever. `scripts/secret-scan.sh` runs in the release gate.
- Least access: the AMI user is limited to 127.0.0.1 and `command` rights.
- The logger never transmits. Node links are monitor only (`ilink 2`).
- No release without a passing pen test. See [pentest.md](pentest.md).

## Auth
- Users: username and password. Accounts need a current amateur license (FCC lookup for US calls, admin confirms others).
- Roles: admin (users, setup details) and operator (run nets). The server checks the role on every request.
- First run: creating the admin needs the setup code from the server log, so whoever finds the dashboard first can't claim it.
- Sign-in throttling: per client IP and per account (5 and 10 free tries, then 30 s doubling to 15 min).
- Sessions: random 32-byte token, cookie HttpOnly, SameSite=Strict, Secure when `COOKIE_SECURE=1`. Logout and password changes end sessions on the server.
- CSRF: POSTs must be `application/json`, which a cross-site form can't send without a preflight the server never answers.

## Attack surface
| Port or endpoint | Exposure | What an attacker could do | Guard |
|---|---|---|---|
| Dashboard HTTP (8080) | 127.0.0.1 behind a proxy (install.sh), container port (Docker) | Guess passwords, abuse an account | Throttling, roles, CSP, body limit 64 KB |
| USRP audio (UDP 34001) | 127.0.0.1 (install.sh) | Feed fake audio: fake check-ins, CPU load | `USRP_HOST`, `USRP_ALLOW`, firewall |
| AMI client | Outbound to 127.0.0.1:5038 | n/a (we're the client) | Node numbers must be 3 to 7 digits |
| callook.info, APNs, model download | Outbound HTTPS | n/a | Callsign format checked before lookup |

- With a CDN in front (Cloudflare), block the origin from everyone but the CDN, or use a tunnel. Otherwise anyone can reach the origin and fake the client-IP header. The per-account limit still holds.
- Docker publishes UDP 34001 on every interface. Set `USRP_ALLOW` to the AllStar server's address, or firewall the port.

## If something leaks
1. AMI secret: re-run `install.sh` (makes a new one) or change it in both the env file and the Asterisk include, then restart both.
2. APNs key: revoke it in Apple Developer > Keys, make a new one, update `APNS_KEY_FILE` and `APNS_KEY_ID`.
3. A user's password: `sudo netlogger reset-password <call>`. This ends all their sessions.
4. The database: it holds password hashes and callsigns. Reset everyone's password.
5. Check `journalctl -u netlogger` for sign-ins and node actions, then write a decision record with what happened and what changed.
