@echo off
REM Install the ruff pre-commit hook for this clone.
REM Run from anywhere:  scripts\hooks\setup.bat
REM Idempotent: safe to run whenever you want to reinstall/update the hook.
REM Note: git runs hooks via its bundled sh, so we install the .sh hook body.

setlocal

for /f "delims=" %%i in ('git rev-parse --show-toplevel') do set "REPO_ROOT=%%i"
if "%REPO_ROOT%"=="" (
  echo setup-hook: not a git repo
  exit /b 1
)

set "HOOKS_DIR=%REPO_ROOT%\.git\hooks"
set "SOURCE=%REPO_ROOT%\scripts\hooks\pre-commit.sh"
set "TARGET=%HOOKS_DIR%\pre-commit"

if not exist "%HOOKS_DIR%" (
  echo setup-hook: could not find %HOOKS_DIR%
  exit /b 1
)

if not exist "%SOURCE%" (
  echo setup-hook: missing %SOURCE%
  exit /b 1
)

copy /y "%SOURCE%" "%TARGET%" >nul

echo setup-hook: installed ruff pre-commit hook -^> %TARGET%
exit /b 0
