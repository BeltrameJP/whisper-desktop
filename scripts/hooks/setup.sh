#!/bin/sh
# Install the ruff pre-commit hook for this clone.
# Run from anywhere:  sh scripts/hooks/setup.sh
# Idempotent: safe to run whenever you want to reinstall/update the hook.

set -eu

repo_root="$(git rev-parse --show-toplevel)"
hooks_dir="$repo_root/.git/hooks"
source="$repo_root/scripts/hooks/pre-commit.sh"
target="$hooks_dir/pre-commit"

if [ ! -d "$hooks_dir" ]; then
  echo "setup-hook: could not find $hooks_dir (not a git repo?)" >&2
  exit 1
fi

if [ ! -f "$source" ]; then
  echo "setup-hook: missing $source" >&2
  exit 1
fi

cp "$source" "$target"
chmod +x "$target"

echo "setup-hook: installed ruff pre-commit hook -> $target"
