# 0007: Optional Apple push for the iOS app

**Date:** 2026-11-04
**Status:** Accepted

## Context
A companion iOS app wanted alerts and a Live Activity during nets.

## Options
1. **Polling only:** no keys, but no alerts with the app closed.
2. **APNs from the logger with the owner's own key:** real alerts, off by default.

## Decision
Push through APNs (HTTP/2, ES256 token), only when all four APNS_* settings are set.

## Why
- Nothing goes to Apple on installs that don't opt in.
- The key stays on the owner's server.

## Risks and follow-ups
- Two new dependencies (httpx[http2], cryptography).
- Push tokens are per user; see pen test finding #7.
