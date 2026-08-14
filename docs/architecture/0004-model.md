# ADR 0004 — Model: faster-whisper `base.en`, `int8`, CPU

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

The app must transcribe locally on end-user CPUs with no GPU and stay responsive enough for dictation. Larger models are more accurate but slower and heavier.

A key requirement: users **are not native English speakers**, which demands better phoneme and accent robustness than the smallest models provide.

## Decision

- **Model size:** `base.en` (~145 MB) — better generalization over `tiny` for accented/non-native speech, while remaining fast on CPU.
- **Engine config:** `device="cpu"`, `compute_type="int8"` for universal compatibility and low CPU load.
- **Language:** `base.en` is English-focused for cleaner results on English dictation.

## Consequences

- First run downloads `base.en` into the OS cache (see ADR 0008).
- `tiny` would be faster but noticeably worse on non-native accents; `small`/`medium` are more accurate but slower and heavier than needed for live dictation.
- `base.en` (English-only) trades multilingual support for speed/accuracy; if multilingual dictation is later required, switch to multilingual `base` (see the open note in ADR 0008).
- Model choice is kept behind a `Settings` value so it can be swapped without code changes.
