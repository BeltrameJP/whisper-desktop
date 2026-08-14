# ADR 0006 — Cross-platform target and packaging

- **Status:** Accepted
- **Date:** 2026-08-14

## Context

Whisper Desktop must ship to Windows, macOS, and Linux. Python source is inherently portable, but native binaries, system audio libraries, and installers differ per OS. Packaging must be reproducible and, ideally, automated.

## Decision

- Target all three OSes from a **single shared codebase** (no per-OS forks).
- **Primary packaging:** PyInstaller `--onefile` per OS.
  - Windows: `build_windows.bat` (bundles the sounddevice PortAudio DLL shipped with the Windows wheel).
  - Linux: `build_linux.sh` (ELF binary).
  - macOS: `.app`/binary.
- **Automation:** a GitHub Actions workflow with a 3-OS matrix (`windows-latest`, `macos-latest`, `ubuntu-latest`) that runs `poetry install --with dev` + PyInstaller and uploads artifacts per push.
- **System deps documented per OS:**
  - Linux: `sudo apt install python3-tk libportaudio2`
  - macOS: `brew install portaudio`

## Consequences

- CI produces macOS and Linux artifacts that cannot be built on a Windows-only dev machine.
- PyInstaller is build-per-OS: artifacts must be produced on (or CI-targeted to) each platform.
- GUI runs inside WSL actively in development; the native-Linux build is validated via the GitHub Actions `ubuntu-latest` runner.
- PortAudio DLL bundling must be verified so the packaged Windows exe still captures audio.
