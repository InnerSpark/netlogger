# 0005: Stock shadcn/ui theme, not Flint

**Date:** 2026-09-28
**Status:** Accepted

## Context
Mike's apps use Flint, but Flint is private and this repo is public.

## Options
1. **Flint:** matches Mike's other products, can't ship in a public repo.
2. **Stock shadcn/ui neutral theme:** public, accessible base, AA contrast.

## Decision
Stock shadcn/ui.

## Why
- Anyone can build and change the dashboard.
- Radix underneath gives solid keyboard and screen reader behavior.

## Risks and follow-ups
- Light-mode muted text is 4.7:1, AA not AAA. Logged as an exception in accessibility-audit.md.
- Revisit if Flint goes public.
