# ADR 0010 — Microphone selection with persisted settings

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

Whisper Desktop currently captures from the system's default input device only
(`AudioRecorder` opens `sd.InputStream(...)` with no `device`). Users with
multiple microphones (built-in, USB, headset) have no way to choose one, and
the choice is lost on every restart. The transcription engine's `Settings`
dataclass is in-memory only and is the wrong place for user-facing preferences
that must survive restarts.

## Decision

- **Device enumeration:** a small pure module (`src/audio/devices.py`) wraps
  `sd.query_devices()`, filtering to devices with `max_input_channels > 0`, and
  exposes `default_input_index()` and a human-friendly `device_label()`.
- **Recorder:** `AudioRecorder` accepts an integer `device` (PortAudio index)
  passed to `sd.InputStream`. If the saved device is no longer present
  (unplugged), it falls back to the default and surfaces a warning.
- **Persistence:** a new `AppConfig` dataclass (`src/config.py`) holds
  `input_device_id` and is serialized as JSON to
  `platformdirs.user_config_dir("whisper-desktop")/config.json` — the same OS
  config location implied by ADR 0008:
  - Windows: `%APPDATA%\whisper-desktop`
  - macOS: `~/Library/Application Support/whisper-desktop`
  - Linux: `~/.config/whisper-desktop`
- **GUI:** a modal settings window (`src/gui/settings_window.py`) with a
  left-hand navigation list. The first (and currently only) section is
  **Voice**, exposing a dropdown of input devices plus Save/Cancel. The layout
  is structured so future sections can be added without reshaping the dialog.

## Consequences

- The chosen microphone is remembered across restarts.
- Setting the device is decoupled from the engine's in-memory `Settings`,
  keeping persistence concerns in one place.
- `AppConfig.load()` merges stored values over defaults and tolerates unknown
  keys, corrupt JSON, and invalid indices, so a hand-edited or stale file never
  breaks startup.
- If the saved device is unplugged, capture gracefully falls back to the
  system default with a warning instead of crashing.
- Cost: a new config file and dialog; the voice section is a minimal single
  setting today but establishes the navigation pattern for future settings
  (e.g. model size, appearance).
