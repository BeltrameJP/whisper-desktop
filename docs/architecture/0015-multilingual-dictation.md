# ADR 0015 — Multi-language dictation with on-demand model download

- **Status:** Proposed
- **Date:** 2026-08-16

## Context

The app currently transcribes with `base.en` (ADR 0004), which is **English-only** and cannot transcribe other languages. Users want to dictate in languages other than English, and the default model must change when they do. Whisper's multilingual models (`base`, `small`, `medium`, `large-v3`, …) cover all ~99 supported languages in a single model, so there is no per-language model — one multilingual model serves every language.

Two concerns follow:

1. **Language selection:** users need a way to choose a language from the full Whisper set, not just a hidden `str` setting.
2. **Model download:** selecting a non-English language requires a multilingual model, which must be downloaded on demand (and the download should be visible and user-controlled).

This ADR records how the app exposes languages and handles the multilingual model download. It intentionally does **not** modify the historical decisions in ADR 0004 (model) or ADR 0008 (paths).

## Decision

### Language selection

- Expose **all ~99 Whisper languages** (ISO-639-1 codes) through a **searchable/filtered dropdown** in Settings, so the full set is available without a long, unusable list.
- Each language is labeled **`Name (code)`** (e.g. `Portuguese (pt)`) for clarity and to disambiguate same-name locales.
- Persist the selection as `language` in `AppConfig` (default `None` = auto-detect), so it survives restarts.

### Model auto-selection

The user picks a **language**, not a **model**. The model is chosen automatically:

- `Auto` or `English` → `base.en` (the existing fast English-only model, preserving ADR 0004's intent for non-native English speakers).
- Any other language → multilingual **`base`** (~145 MB).

This keeps the English path unchanged while enabling multilingual dictation with a single extra model.

### Model download

- New Settings **"Transcription"** page with an explicit **Download** button and a **progress bar**.
- When a selected language needs a model that is not yet present, saving **auto-downloads it after a confirmation warning** (showing the size / what will be downloaded); the explicit Download button does the same.
- If the user skips the download, the engine **lazily downloads on first transcription** as a fallback.
- Models are cached under `platformdirs.user_cache_dir("whisper-desktop")/models`, consistent with ADR 0008. Both the downloader and the engine use this directory (as `cache_dir`/`download_root`), so there are no duplicate downloads and the cache location stays consistent with the rest of the app.

### Applying changes

- A language change **restarts the `WhisperWorker`** (stop sentinel + a new worker) so the new language/model applies immediately, because the loaded model is cached against the worker's settings.

## Consequences

- **English path unchanged:** `Auto`/`English` still use `base.en`, so existing behavior and performance are preserved (ADR 0004 remains valid for the English case).
- **Multilingual support:** choosing a non-English language transparently switches to multilingual `base` and downloads it only when first needed.
- **Download cost:** multilingual `base` adds ~145 MB on first use for non-English dictation; larger multilingual models are intentionally not offered now.
- **Download UX:** the download is explicit and visible (progress bar + confirmation), with a lazy fallback if skipped.
- **Live apply:** changing language triggers a brief worker reload on the next transcription.
- **Isolation:** historical ADRs 0004 and 0008 are left untouched; the multilingual switch and cache handling are scoped here.
