# ADR 0008 — Temp & cache paths via `tempfile` + `platformdirs`

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

The app needs (a) a place to write temporary WAV files and (b) a place to cache the Whisper model weights. Both must be correct on Windows, macOS, and Linux without hardcoding any OS-specific path.

## Decision

- **Temp files:** Python stdlib `tempfile` → `tempfile.gettempdir()` (and `NamedTemporaryFile(delete=False, suffix=".wav")`) for the recorded audio before transcription.
- **Model/config cache:** `platformdirs.user_cache_dir("whisper-desktop")`, which resolves to:
  - Windows: `%LOCALAPPDATA%\whisper-desktop`
  - macOS: `~/Library/Caches/whisper-desktop`
  - Linux: `~/.cache/whisper-desktop`

## Consequences

- No hardcoded `%LOCALAPPDATA%` / `~/Library` / `/home/...` paths in code.
- Temp WAVs are cleaned up after transcription (deleted in the worker), so they do not accumulate.
- faster-whisper already caches to the OS-appropriate dir via huggingface_hub; `platformdirs` gives us one consistent location and a path forward for future settings.
- **Open note:** if multilingual dictation is ever required, swap the cached `base.en` for `base` and expose language detection — this ADR keeps that change isolated to the cache/model selection layer.
