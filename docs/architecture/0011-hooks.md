# ADR 0011 — Pre-commit hook running ruff

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

The project uses Poetry to manage dependencies, with `ruff` pinned in the dev group (ADR 0005). Contributors need a reliable, low-friction way to keep the codebase linted and formatted before each commit. Some contributors (including this machine) do not have `poetry` on their global PATH, so the hook must degrade gracefully.

## Decision

- Add a **pre-commit hook** that runs `ruff check --fix` and `ruff format` over the staged Python files only.
- Ship the hook as committed scripts under `scripts/hooks/`:
  - `pre-commit.sh` — the hook logic (POSIX `sh`).
  - `setup.sh` — POSIX installer that copies the hook into `.git/hooks/pre-commit` and makes it executable.
  - `setup.bat` — Windows installer (copies the same `.sh` body, because git runs hooks through its bundled `sh` even on Windows).
- The hook is **installed by running `setup.sh` / `setup.bat`** whenever the user wants; it is not auto-installed.
- If `poetry` is unavailable, the hook prints a warning and **fails open** (does not block the commit).
- If ruff finds errors, the hook blocks the commit and re-stages any files ruff formatted so the result is included.

## Consequences

- Ruff runs on every commit once installed, keeping formatting and linting consistent without manual steps.
- Fail-open behavior means a machine without `poetry` can still commit un-linted code.
- The hook is per-clone (lives in `.git/`), so a fresh clone must re-run the setup script to (re)install it.
- No change to `pyproject.toml` or a `.pre-commit-config.yaml`; a minimal plain-git-hook approach with no extra tooling dependency.
