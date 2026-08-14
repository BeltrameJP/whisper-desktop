# ADR 0001 — Stack: CustomTkinter + faster-whisper (CPU)

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

We are building a cross-platform (Windows, macOS, Linux) desktop voice-dictation app that transcribes microphone audio locally without cloud services. The UI and the heavy STT inference both need to run on end-user hardware (no GPU assumption).

Two candidate UI frameworks were considered: PySide6 (Qt for Python) and CustomTkinter.

## Decision

- **UI framework:** CustomTkinter — modern-looking native widgets without a heavy Qt runtime.
- **STT engine:** faster-whisper — efficient CPU runtime via ctranslate2, faster than the reference OpenAI Whisper implementation.

## Consequences

- CustomTkinter depends on Tk/Tkinter, which is a **system package** on Linux (`python3-tk`) and macOS — not always pre-installed. Install steps must document this.
- faster-whisper is fast and accurate on CPU but downloads model weights on first run (~145 MB for `base.en`).
- Chosen over PySide6, which offers richer widgets and first-class Qt signals but carries a large (~600 MB+) Qt dependency and heavier packaging — outweighing the benefit for this focused app.
