# ADR 0005 — Dependency management with Poetry (`pyproject.toml`)

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

Contributors should be able to clone the repo and get every dependency with a single command, regardless of OS. The project also needs to keep build/test tooling separate from runtime dependencies.

## Decision

- Manage dependencies with **Poetry** via a single `pyproject.toml`.
- Poetry **creates its own virtualenv** automatically — no manual `venv`/`venv-win` creation needed.
- Dependency groups:
  - `[tool.poetry.dependencies]` — runtime app (customtkinter, sounddevice, scipy, faster-whisper, platformdirs).
  - `[tool.poetry.group.dev.dependencies]` — build tooling (pyinstaller, ruff).
  - `[tool.poetry.group.test.dependencies]` — pytest.

## Consequences

- One command to bootstrap: `poetry install`.
- `poetry.lock` pins exact transitive versions for reproducible installs across OSes.
- Contributors do **not** hand-create virtualenvs — Poetry manages them.
- `python = ">=3.10,<3.13"` constrains versions to those fully supported by faster-whisper/ctranslate2.
