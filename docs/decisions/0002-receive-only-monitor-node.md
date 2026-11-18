# 0002: Receive only, through a private monitor node

**Date:** 2026-09-27
**Status:** Accepted

## Context
FCC Part 97 rules on automated transmissions, and nobody wants a bot keying up a repeater.

## Options
1. **Transmit-capable assistant:** more features, real rule and safety risk.
2. **Receive-only private node linked in monitor mode:** hears everything, can't transmit.

## Decision
A private node (default 1999) with USRP audio out and links made with `ilink 2` (monitor) only.

## Why
- Nothing the logger does can reach the air.
- Doesn't touch the owner's node settings; installed through include files.

## Risks and follow-ups
- A schedule that unlinks after a net leaves the logger deaf until the next net or restart (AUTO_CONNECT covers reboots).
