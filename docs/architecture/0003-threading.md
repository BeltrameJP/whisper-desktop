# ADR 0003 — Threading model (recorder / worker / GUI)

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

Three latency-sensitive concerns cannot share a single thread:
1. Tk GUI responsiveness (must never block).
2. Microphone streaming (must never drop frames).
3. Whisper inference + model load (seconds; must not freeze the window).

CustomTkinter has no signal-slot mechanism like Qt's QThread/QObject, so coordination must be explicit.

## Decision

- **GUI main thread:** owns Tk; renders widgets; the only thread allowed to touch the UI.
- **Audio recorder thread:** a `sounddevice.InputStream` runs a callback on PortAudio's thread that only appends copies of incoming frames to a plain Python list.
- **Whisper worker thread:** a `threading.Thread` that lazily loads the model and performs transcription.
- **Communication:** results flow from the worker back to the GUI through a `queue.Queue`. The GUI polls it every ~100 ms via `root.after(100, poll)` and updates widgets only on the main thread.

## Consequences

- Explicit and simple; easy to reason about, no deadlocks from nested lock acquisition.
- The 100 ms poll adds negligible latency; results feel near-instant.
- Rule enforced by convention: callbacks list-append only; worker uses the queue only; GUI drains the queue only.
- Faster-whisper holds the GIL during ctranslate2 inference, but since it runs on the worker thread and the GUI only polls a queue, the GUI stays responsive.
