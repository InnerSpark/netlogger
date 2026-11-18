# 0008: Setup code and loopback-only audio

**Date:** 2026-11-18
**Status:** Accepted

## Context
The first pen test found the audio port open to anyone and a fresh install claimable by whoever found it first.

## Options
1. **Docs only:** tell people to firewall and set up fast.
2. **Safe defaults in code:** setup code in the log, audio on 127.0.0.1 for installer setups, source allowlist for remote setups.

## Decision
Safe defaults in code. `USRP_HOST=127.0.0.1` is written on install and added on upgrade; `USRP_ALLOW` for Docker and remote setups; a setup code for the first admin.

## Why
- Secure without the owner doing anything extra.
- Attacks for both are in the suite.

## Risks and follow-ups
- New installs need one extra step (read the setup code from the log). The installer prints it.
