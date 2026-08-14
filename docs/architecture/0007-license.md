# ADR 0007 — License: MIT

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

The app is a portfolio piece and reuses dependencies whose licenses must remain respected when distributing binaries.

## Decision

- License the project under the **MIT License** (`LICENSE`, © 2026 beltramejp).

## Consequences

- Permissive: anyone can use, modify, distribute, and sell with attribution.
- Compatible with all direct/transitive dependencies:
  - faster-whisper / ctranslate2 — MIT
  - sounddevice — MIT
  - scipy — BSD-3-Clause
  - CustomTkinter — MIT
  - OpenAI `base.en` model weights — MIT
- No copyleft obligations; ideal for a portfolio repo that others will clone and build.
