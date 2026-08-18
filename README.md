# Whisper Desktop

An offline, cross-platform desktop app that turns your microphone into text — powered by local speech recognition. No cloud, no account, no uploads: your audio never leaves your machine.

Works on Windows, macOS, and Linux.

## Features

### Record & transcribe

- One-click **Start Recording** button that turns into **Stop** while you're live.
- Clear on-screen status — **Idle**, **Recording…**, **Transcribing…** — so you always know what's happening.
- An elapsed-time and detected-language readout next to your transcript (e.g. `12.3s · en`).

### Live transcription

- **Live transcription is on by default**: text streams onto the screen as you speak, instead of waiting for you to hit Stop.
- On Stop, the app runs a refined pass over the full session for a cleaner final result.
- Turn live mode off anytime in Settings to transcribe only when you press Stop.

### Multilingual dictation

- Dictate in any of **~99 Whisper languages** plus **Auto** (automatic language detection).
- Type-ahead filtering in the language picker — start typing and it narrows the list.
- The right model is chosen for you automatically; English and Auto keep the fast model, other languages switch to the multilingual one.
- If a needed model isn't downloaded yet, the app downloads it on demand with a visible progress bar — then it's cached and stays fully offline.

### Microphone & input control

- Pick your microphone from a dropdown, with the system default and unplugged devices clearly marked.
- If your chosen mic disappears, the app falls back to the system default instead of failing.
- A Discord-style **Input sensitivity** slider with a live level meter — drag it just above your silence level so only real speech is captured.

### Output & sharing

- **Copy** your transcript to the clipboard with one click.
- **Save As…** writes it to a `.txt` file wherever you choose.
- **Clear** wipes the text box and starts fresh.

### Privacy by design

- Everything runs locally — speech recognition happens on your own hardware.
- No account, no telemetry, no cloud round-trip.
- Settings are stored as a small JSON file in your user config folder.

## Using the app

1. Click **Start Recording**.
2. Speak clearly.
3. Click **Stop** (or just watch the text stream in live mode).
4. Use **Copy**, **Save As…**, or **Clear** below the text box.

## Settings

The **⚙ Settings** window is organized into two pages:

- **Voice** — live transcription toggle, input sensitivity, and microphone selection.
- **Transcription** — language picker, model status, and manual model download.

## Download & install

The easiest way to get Whisper Desktop is to grab a ready-made build from the [GitHub Releases](https://github.com/BeltrameJP/whisper-desktop/releases) page:

- **Windows** — `WhisperDesktop-windows-x64.exe`
- **Linux** — `WhisperDesktop-linux`
- **macOS** — `WhisperDesktop-macOS-arm64.zip` (Apple Silicon, i.e. M-series chips and newer)

On first run the app downloads a small speech model (~145 MB) so it can understand you. After that it works completely offline.

> **macOS Gatekeeper:** releases are unsigned and not notarized. If macOS blocks the app on first launch, right-click it and choose **Open**, then confirm.
>
> **macOS microphone permission:** on first launch macOS asks for microphone access — click **Allow**. If you ever miss the prompt (or audio is silent), enable it manually under **System Settings → Privacy & Security → Microphone** for *Whisper Desktop*, then relaunch the app.

### For developers

Want to run it from source? You'll need **Python 3.11 or 3.12** and **Poetry**. Clone the repo, run `poetry install`, then `poetry run python main.py`. On Linux you may also need `libportaudio2`; on macOS, `portaudio`.

## License

MIT — see [LICENSE](LICENSE).
