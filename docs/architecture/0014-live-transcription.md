# ADR 0014 — Live/streaming transcription via buffered chunks (mimicked async)

- **Status:** Proposed
- **Date:** 2026-08-16

## Context

Today the app records audio into a single temporary WAV and transcribes it only when the user clicks **Stop** (one-shot mode, see ADR 0003). This gives a blank screen while speaking — the user asked for text to appear on screen while they talk, as if transcription were asynchronous.

faster-whisper does not provide true streaming inference, so we must mimic it: capture audio continuously, break it into chunks, and transcribe each chunk incrementally so results stream onto the screen.

## Decision

Introduce a **Live mode** (new toggle in Settings, **default ON**) that streams audio to a growing temp WAV on disk and transcribes it in buffered chunks:

- **Storage — stream to disk, not RAM.** PCM frames are appended to a growing temporary WAV file. Only a short rolling tail (~2s) is held in RAM for voice detection and chunk overlap. RAM stays flat regardless of recording length, so no hard buffer cap is required.
- **Voice detection — simple energy threshold.** Flush the current chunk when the RMS energy stays below a threshold for ~300ms. No new dependencies; the detector lives behind a small interface so it can be swapped for a more robust VAD (e.g. `webrtcvad`) later without touching the recorder.
- **Chunk overlap.** When a chunk is flushed, keep ~0.5–1s of the previous audio in the next chunk and discard the duplicated leading words so mid-word cuts and boundary tokens don't break the transcript.
- **Cross-chunk context.** Enable `condition_on_previous_text=True` in `transcribe()` so each chunk uses the prior text as context, reducing repeated/hallucinated boundary tokens.
- **Concurrency — never stop recording.** Completed chunks are queued to the existing `WhisperWorker` (now segment-based) which transcribes them sequentially, running slightly behind live capture. The GUI continues to poll results via a `queue.Queue` every ~100ms (ADR 0003).
- **Appending.** Each result is appended to the textbox, building a running transcript. While a chunk is in flight, the textbox shows a **"Transcribing…"** placeholder.
- **Stop behavior.** On Stop, the final partial chunk is flushed and transcribed so no trailing words are lost, then the session ends.
- **Mode coexistence.** One-shot (transcribe-on-stop) behavior is retained and selectable in Settings. Live mode is the new default.

## Consequences

- Text streams onto the screen as the user speaks, matching the async feel the user wanted, with only the latency of one chunk (~300ms silence + transcribe time).
- RAM usage is bounded because audio lives on disk, not in a `deque`; long continuous dictation no longer grows memory.
- Chunk boundaries are smoothed via overlap + `condition_on_previous_text`, at the cost of transcribing a small amount of redundant audio per chunk.
- Disk I/O increases (continuous WAV writes + per-chunk reads), acceptable for local desktop usage.
- Adds a new Live toggle and VAD tunables to Settings; requires threading the "live vs one-shot" mode through the recorder, worker, and GUI.
- Simple energy VAD may mis-segment noisy or variable-loudness speech; the swappable interface is the escape hatch for a more robust detector later.

## Open notes / future work

- Consider a `webrtcvad`-based detector behind the VAD interface if the energy threshold proves unreliable in noisy environments.
- Expose VAD tunables (`silence_ms`, `energy_threshold`, `overlap_ms`) in Settings once the defaults are validated in the field.
