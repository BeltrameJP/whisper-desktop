# Whisper Desktop

An offline, cross-platform desktop app that turns your microphone into text — powered by local speech recognition. No cloud, no account, your audio stays on your machine.

## What it does

Click **Start Recording**, speak, click **Stop**, and your words appear as text in seconds. From there you can copy the text, save it to a file, or clear the box and start again.

It runs locally and works on Windows, macOS, and Linux.

## Installation

You'll need **Python 3.11 or 3.12** and **Poetry**.

```bash
git clone https://github.com/<you>/whisper-desktop.git
cd whisper-desktop

poetry install
poetry run python main.py
```

On first run the app downloads a small speech model (~145 MB) so it can understand you. After that it works completely offline.

> **Trouble launching?** On Linux/macOS you may need to install the audio and interface libraries first:
> - **Linux:** `sudo apt install python3-tk libportaudio2`
> - **macOS:** `brew install portaudio`

## Using the app

1. Click the **Start Recording** button (it turns into **Stop**).
2. Speak clearly.
3. Click **Stop** — the app transcribes and shows your text.
4. Use **Copy**, **Save As…**, or **Clear** below the text box.

## Building a standalone app

You can also package it as a standalone executable (no Python install needed) using PyInstaller. Build scripts are included for each platform.

- **Windows:** `build_windows.bat`
- **Linux:** `build_linux.sh`
- **macOS/Linux/Windows (builds made in CI):** see the GitHub Actions workflow

The produced app lands in the `dist/` folder.

> **macOS Gatekeeper:** releases are unsigned/not-notarized. If macOS blocks the app on first launch, right-click it and choose **Open** (then confirm), or run:
> ```bash
> xattr -d com.apple.quarantine /Applications/WhisperDesktop.app
> ```

## Project layout

```
main.py              # entry point
src/
├── audio/           # microphone capture
├── whisper_engine/  # local speech recognition
└── gui/             # the desktop window
```

## License

MIT — see [LICENSE](LICENSE).
