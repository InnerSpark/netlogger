# 0004: Python standard-library server and SQLite

**Date:** 2026-09-27
**Status:** Accepted

## Context
It runs beside Asterisk on small servers, and other hams install it.

## Options
1. **Django or FastAPI with Postgres:** more features, more to install and patch.
2. **Standard library HTTP server and SQLite:** few dependencies, one file of data.

## Decision
ThreadingHTTPServer, SQLite, a small route table.

## Why
- Fewer packages to audit and keep patched.
- Backup is one file.

## Risks and follow-ups
- We write our own auth, throttling and headers; the attack suite covers them.
- Should sit behind a reverse proxy for HTTPS.
