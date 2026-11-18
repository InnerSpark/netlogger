# 0001: AGPL-3.0 license

**Date:** 2026-09-27
**Status:** Accepted

## Context
The logger is free for the ham community. Mike didn't want anyone taking it and charging for it.

## Options
1. **MIT:** simplest, but anyone can close it and sell it as a service.
2. **GPL-3.0:** changes must be shared, but not for software run as a web service.
3. **AGPL-3.0:** changes must be shared even when it's only run as a service.

## Decision
AGPL-3.0.

## Why
- No open-source license can ban charging, but AGPL makes a closed paid fork impossible.
- Hosted copies must offer their source; the dashboard footer links to it.

## Risks and follow-ups
- Some companies avoid AGPL code. Fine for this audience.
- Every new dependency must be AGPL-compatible (see licensing.md).
