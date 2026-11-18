# 0003: Local speech to text with faster-whisper

**Date:** 2026-09-27
**Status:** Accepted

## Context
Transcribing a whole net needs speech to text. Cloud APIs cost money per minute and send audio off the server.

## Options
1. **Cloud API:** best accuracy, ongoing cost, audio leaves the server.
2. **faster-whisper on the server:** free, private, needs CPU.

## Decision
faster-whisper, int8 on CPU, model sized to the machine by the installer (tiny.en to small.en).

## Why
- Free to run forever, which fits a free project.
- Audio never leaves the server.

## Risks and follow-ups
- Needs 2+ cores and 2+ GB free for good results.
- Accuracy is lower than the best cloud models; the callsign parser and known-calls list make up for it.
