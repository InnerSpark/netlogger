# Net Logger Support

**Contact:** GitHub issues on InnerSpark/netlogger. Security problems: see SECURITY.md (private reporting).

## FAQ
**Q:** Does the logger ever transmit?
**A:** No. Its node links in monitor mode only and has no transmit path.

**Q:** Why does it use node 1999 and not my node?
**A:** 1999 is the logger's own private node. It links to your node to listen. Your node's settings don't change.

**Q:** Where's the setup code?
**A:** The installer prints it. Or run `journalctl -u netlogger | grep "Setup code"` (Docker: `docker compose logs netlogger`).

**Q:** Last heard is empty.
**A:** The logger's node isn't linked to anything. Use Listen to your node on the Dashboard, or set `AUTO_CONNECT=1`.

**Q:** It misheard a call.
**A:** Fix it on the roster. Add your regulars to `KNOWN_CALLS` so clipped calls snap to them.

**Q:** I'm locked out.
**A:** `sudo netlogger reset-password <your call>` on the server.

## Known issues
| Issue | Workaround | Fix status |
|---|---|---|
| Name lookups only for US calls | Calls from other countries log without a name | Roadmap |
| A schedule with "disconnect after" leaves the node unlinked between nets | Turn it off, or set AUTO_CONNECT=1 | By design |
| Server updates can disable other Apache sites on shared servers | Re-check with `sudo apache2ctl -S` (same-server.md) | Doc |

## Troubleshooting
1. Health page (admins): transcriber, last audio, node link.
2. `journalctl -u netlogger -f` while someone keys up.
3. `sudo asterisk -rx "rpt lstats 1999"` shows what the logger's node is linked to.
