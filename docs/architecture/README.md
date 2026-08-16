# Architecture Decision Records

This folder records the key technical decisions for Whisper Desktop, the rationale behind each, and the alternatives that were rejected. Each document follows a lightweight ADR (Architecture Decision Record) format:

- **Status** — Accepted / Proposed / Superseded
- **Context** — the forces and constraints at the time of the decision
- **Decision** — what we chose
- **Consequences** — the trade-offs that decision brings

## Index

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
