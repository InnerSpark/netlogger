# 0006: Accounts for licensed hams only

**Date:** 2026-09-29
**Status:** Accepted

## Context
The dashboard can link nodes and edit logs. Accounts should belong to real, licensed operators.

## Options
1. **Any account an admin makes:** simple, no check.
2. **FCC lookup at setup and when adding users, re-checked every 30 days:** proves a current US license.

## Decision
License check through callook.info for US calls; admins confirm other countries; first admin outside the US is accepted as entered. `REQUIRE_LICENSE=0` turns it off.

## Why
- Keeps control with licensed operators.
- Works for nets with operators in other countries.

## Risks and follow-ups
- callook.info outages: sign-in still works, the re-check waits.
