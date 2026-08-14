# ADR 0009 — Deployment model: native desktop app (not server)

- **Status:** Accepted
- **Date:** 2026-08-14
- **Supersedes:** the initial FastAPI transcription-server prototype

## Context

The earliest prototype (`main.py`) was a FastAPI server exposing a `/transcribe` endpoint. The target product is a self-contained desktop dictation app a user launches, presses Start, and expects an on-screen transcript.

## Decision

- Ship **one native desktop application** that captures the mic, transcribes locally, and shows the result in the same window. No HTTP server, no browser UI.
- The recorder runs on the native host OS to guarantee reliable mic access (command-line: `I can run the program inside windows with no problem`).

## Consequences

- Local, offline, privacy-preserving transcription — no audio leaves the machine.
- The FastAPI server prototype is **removed** from `main.py`; the app entry becomes the GUI (`main.py` → `GUIApp`).
- Reliable mic capture dictated the choice to run natively on the host rather than exclusively inside a limited-VM/WSL environment (see ADR 0003 for the threading implications).
