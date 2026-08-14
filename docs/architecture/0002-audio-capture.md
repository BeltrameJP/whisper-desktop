# ADR 0002 — Audio capture via PortAudio (sounddevice)

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

Microphone input must be captured without stalling the GUI. A recording is a raw stream of samples that must be assembled and saved as a WAV before transcription.

Candidates: `pyaudio` (PortAudio for Python) or `sounddevice` (PortAudio via cffi).

## Decision

- **`sounddevice`** for stream capture (samplerate 16 kHz, mono, `int16`), using its **callback (InputStream)** mode so sampling happens on PortAudio's own thread.
- The captured buffer is written to a temp `.wav` via **scipy** (`scipy.io.wavfile`).

## Consequences

- sounddevice ships a **bundled PortAudio** on Windows (wheel) but needs a **system PortAudio** on Linux/macOS:
  - Linux: `sudo apt install libportaudio2`
  - macOS: `brew install portaudio`
- Using a callback stream keeps capture non-blocking — the GUI thread never performs I/O, avoiding freezes.
- Chosen over pyaudio for a cleaner async model and first-class WAV/sample handling via scipy.
