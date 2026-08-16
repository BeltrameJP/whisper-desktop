# Whisper Desktop — Roadmap

Plain, prioritized feature list for future changes. Each item links to its Architecture Decision Record (ADR) under `docs/architecture/`, where the detailed rationale, decisions, and trade-offs live. Items marked **Proposed** are decided in principle but not yet implemented.

## Legend

- **P1** — next up, high value
- **P2** — planned
- **P3** — future / stretch

---

## 1. Live / streaming transcription (mimicked async)

- **Priority:** P1
- **Status:** Proposed
- **ADR:** [0014-live-transcription.md](architecture/0014-live-transcription.md)

Stream text onto the screen while the user speaks, as if transcription were asynchronous. faster-whisper is not a streaming model, so live mode mimics it by buffering audio into chunks and transcribing them incrementally.

**Key behavior:**
- New **Live mode** toggle in Settings, **default ON**; one-shot (transcribe-on-stop) mode is retained.
- Audio is appended to a growing temp WAV on disk; only a short ~2s rolling tail is held in RAM, so memory stays flat no matter how long the user speaks.
- A chunk is flushed when RMS energy stays below a threshold for ~300ms; ~0.5–1s of audio overlap is kept and duplicate leading words are discarded for smooth boundaries.
- `condition_on_previous_text` is enabled so each chunk uses prior text as context, reducing repeated boundary tokens.
- Results append to the textbox, building a running transcript; a **"Transcribing…"** placeholder shows while a chunk is in flight.
- Recording never stops while chunks transcribe in sequence; **Stop** flushes and transcribes the final partial chunk.

**Why it matters:** turns the blank-while-speaking experience into a live, dictation-like workflow — the core usability win for this app.

---

## 2. Multi-language dictation with on-demand model download

- **Priority:** P1
- **Status:** Proposed
- **ADR:** [0015-multilingual-dictation.md](architecture/0015-multilingual-dictation.md)

Let users dictate in languages other than English. The default `base.en` model is English-only, so selecting a non-English language switches to a multilingual model and downloads it on demand.

**Key behavior:**
- All ~99 Whisper languages exposed through a **searchable/filtered dropdown** in Settings, labeled `Name (code)` (e.g. `Portuguese (pt)`).
- **Model is auto-selected:** `Auto`/`English` keep `base.en`; any other language uses multilingual `base` (~145 MB).
- A new Settings **"Transcription"** page provides an explicit **Download** button with a **progress bar**; saving a language that needs an undownloaded model auto-downloads it after a confirmation warning.
- If skipped, the model **lazily downloads on first transcription** as a fallback. Models cache under `platformdirs.user_cache_dir("whisper-desktop")/models` (per ADR 0008).
- Changing language **restarts the worker** so it applies immediately.

**Why it matters:** removes the English-only ceiling on dictation while keeping the fast English path intact and making the multilingual download explicit and visible.

---

## 3. More robust voice detection (swap-in VAD)

- **Priority:** P3
- **Status:** Proposed (as an escape hatch within ADR 0014)
- **ADR:** [0014-live-transcription.md](architecture/0014-live-transcription.md) (Open notes)

The v1 voice detector uses a simple RMS-energy threshold. If it mis-segments in noisy or variable-loudness environments, swap in a more robust VAD (e.g. `webrtcvad`) behind the same interface without touching the recorder.

---

## 4. Configurable live-transcription tuning

- **Priority:** P3
- **Status:** Proposed (as Open notes within ADR 0014)
- **ADR:** [0014-live-transcription.md](architecture/0014-live-transcription.md) (Open notes)

Once defaults are validated in the field, expose live-mode tunables in Settings: `silence_ms`, `energy_threshold`, and `overlap_ms`.

---

## Index of related ADRs

| ADR | Title | Status |
|-----|-------|--------|
| 0001 | Stack: CustomTkinter + faster-whisper (CPU) | Accepted |
| 0002 | Audio capture via PortAudio (sounddevice) | Accepted |
| 0003 | Threading model (recorder / worker / GUI) | Accepted |
| 0004 | Model: faster-whisper `base.en`, `int8`, CPU | Accepted |
| 0005 | Dependency management with Poetry (`pyproject.toml`) | Accepted |
| 0006 | Cross-platform target and packaging | Accepted |
| 0007 | License: MIT | Accepted |
| 0008 | Temp & cache paths via `tempfile` + `platformdirs` | Accepted |
| 0009 | Deployment model: native desktop app (not server) | Accepted |
| 0010 | Microphone selection with persisted settings | Accepted |
| 0011 | Pre-commit hook running ruff | Accepted |
| 0012 | CI/CD with GitHub Actions | Accepted |
| 0013 | CI performance: fast ruff gate and dependency caching | Accepted |
| 0014 | Live/streaming transcription via buffered chunks (mimicked async) | Proposed |
| 0015 | Multi-language dictation with on-demand model download | Proposed |
