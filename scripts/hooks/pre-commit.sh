#!/bin/sh
# Pre-commit hook: run ruff (check --fix + format) on staged Python files.
# Installed by scripts/hooks/setup.sh (POSIX) or setup.bat (Windows).

if ! command -v git >/dev/null 2>&1; then
  echo "pre-commit: git not found" >&2
  exit 1
fi

staged_files="$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')"

if [ -z "$staged_files" ]; then
  exit 0
fi

if ! command -v poetry >/dev/null 2>&1; then
  echo "pre-commit: poetry not found; skipping ruff checks (fail open)" >&2
  exit 0
fi

# Re-stage files after ruff mutates them (stays staged for the commit).
cleanup() {
  git add -- "$staged_files" 2>/dev/null
}
trap cleanup EXIT

if ! poetry run ruff check --fix $staged_files; then
  echo "pre-commit: ruff check failed; fix the issues above and re-commit" >&2
  exit 1
fi

if ! poetry run ruff format $staged_files; then
  echo "pre-commit: ruff format failed; fix the issues above and re-commit" >&2
  exit 1
fi

echo "pre-commit: ruff check + format passed"
