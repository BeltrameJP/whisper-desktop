# ADR 0013 — CI performance: fast ruff gate and dependency caching

- **Status:** Accepted
- **Date:** 2026-08-16

## Context

The `test.yml` workflow (ADR 0012) was slow for the size of the codebase: the `lint` job took ~27s and each OS test job ~30s–1m. Most of that time was spent spinning up a container and running `poetry install` for the full dependency group before the actual lint/test work (ruff and the unit tests are each near-instant). Ruff should fail fast, before any tests run, with minimal overhead.

## Decision

- **Fast, standalone lint gate.** The `lint` job no longer installs Poetry or the project dependencies. It installs only `ruff` directly via `pip install ruff==0.5.7` (pinned to the version in `poetry.lock`) and runs `ruff check .` + `ruff format --check .`. The `test` job keeps `needs: lint`, so ruff still runs first and gates the test matrix.
- **Dependency caching for tests.** Each `test` matrix job sets `poetry config virtualenvs.in-project true` and caches the resulting `.venv` (keyed on `poetry.lock` and `runner.os`), so repeated dependency installs are reused across runs on each OS.
- **Trigger reduced to `push`.** `test.yml` now triggers on `push` only (previously `push` and `pull_request`), which eliminated duplicate workflow runs caused by a branch push firing both events.

## Consequences

- Lint now completes in a few seconds rather than ~27s, and still blocks the test matrix on failure.
- Test jobs avoid re-installing dependencies on cache hits, shortening later runs (first run on a fresh lock/OS still installs).
- PRs from forks no longer trigger the workflow; this is acceptable because releases are manual and the owner creates PRs from branches they push.
- Requires manually keeping the `ruff==0.5.7` pin in sync with `poetry.lock` when the lint version changes.
