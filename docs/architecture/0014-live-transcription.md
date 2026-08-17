# ADR 0014 — Live/streaming transcription via buffered chunks (mimicked async)

- **Status:** Proposed
- **Date:** 2026-08-16

## Context

Today the app records audio into a single temporary WAV and transcribes it only when the user clicks **Stop** (one-shot mode, see ADR 0003). This gives a blank screen while speaking — the user asked for text to appear on screen while they talk, as if transcription were asynchronous.

faster-whisper does not provide true streaming inference, so we must mimic it: capture audio continuously, break it into chunks, and transcribe each chunk incrementally so results stream onto the screen.

## Decision

Introduce a **Live mode** (new toggle in Settings, **default ON**) that streams audio to a growing temp WAV on disk and transcribes it in buffered chunks:

- **Storage — stream to disk, not RAM.** PCM frames are appended to a growing temporary WAV file. Only a short rolling tail (~2s) is held in RAM for voice detection and chunk overlap. RAM stays flat regardless of recording length, so no hard buffer cap is required.
- **Voice detection — user-adjustable energy threshold with a live level meter.** Flush the current chunk when the RMS energy stays below a user-set threshold for ~300ms. Instead of a hidden constant, the threshold is controlled by a Discord-style **input sensitivity** control on the Settings "Voice" page: a live input-level bar with a draggable marker. The recorder exposes the current input RMS (`last_rms`); while Settings is open and not recording, a lightweight **monitor** stream feeds the meter. The threshold is stored as `live_threshold` (normalized 0–1, default `0.25`) in `AppConfig` and converted to an RMS value (`energy_threshold`) the recorder compares against. Detection accumulates leftover samples across PortAudio callbacks so it runs on full ~100ms blocks regardless of the device's buffer size (typical callbacks are 32–64ms). The check is implemented inline in the recorder (a unit-testable `_process_audio` helper); a more robust VAD (e.g. `webrtcvad`) can replace it later (see Open notes).
- **Flush only on speech — never on silence/overlap alone.** A chunk is emitted only when real speech (a block at/above the threshold) has occurred since the previous flush. Pure silence, trailing overlap, or a long quiet pause never trigger a chunk, so redundant silence/overlap clips — a known source of Whisper boundary hallucination — are not produced.
- **Storage — raw PCM on disk, WAV chunk files.** The growing session file is written as headerless int16 PCM (simplest for byte-exact slicing). Completed chunks are emitted as proper WAV files for the worker. Only a ~2s rolling tail is held in RAM.
- **Chunking — recorder pump thread.** The PortAudio callback stays append-only (ADR 0003). A dedicated recorder thread (the "pump") drains incoming frames, runs energy detection, writes to the disk file, and emits finished chunk WAV paths to a `ready_chunks` queue. The GUI's existing ~100ms poll forwards those paths to the worker, so recording never stops while chunks transcribe.
- **Chunk overlap.** When a chunk is flushed, keep ~0.75s of the previous audio in the next chunk and discard the duplicated leading words so mid-word cuts and boundary tokens don't break the transcript.
- **Cross-chunk context.** Enable `condition_on_previous_text=True` in `transcribe()` so each chunk uses the prior text as context, reducing repeated/hallucinated boundary tokens.
- **Concurrency — never stop recording.** Completed chunks are queued to the `WhisperWorker` which transcribes them sequentially, running slightly behind live capture. The GUI continues to poll results via a `queue.Queue` every ~100ms (ADR 0003).
- **Appending — incremental results.** The worker emits only the newly decoded text per chunk (it tracks a running transcript and dedups overlapping leading words), tagged with `append=True`. The GUI appends each result to the textbox, building a running transcript. While a chunk is in flight, the textbox shows a **"Transcribing…"** placeholder.
- **Stop behavior — refined final pass.** On Stop, the final partial chunk is **not** flushed. Instead the whole session is written to a single WAV and re-transcribed from scratch as a full-context pass (`live=False`, no prior conditioning, higher beam size) once every streaming chunk has drained. Its refined result **replaces** the incremental draft, so the final transcript is cleaner than the sum of live chunks.
- **Mode coexistence.** One-shot (transcribe-on-stop) behavior is retained and selectable in Settings. Live mode is the new default.
- **Persistence.** The live toggle is stored as `live_mode: bool = True` in the persisted `AppConfig` (ADR 0008) and shown as a switch on the existing "Voice" settings page. A `null` value in the config file falls back to the default (on), so stale or hand-edited configs never break startup.

## Consequences

- Text streams onto the screen as the user speaks, matching the async feel the user wanted, with only the latency of one chunk (~300ms silence + transcribe time).
- RAM usage is bounded because audio lives on disk, not in a `deque`; long continuous dictation no longer grows memory.
- Chunk boundaries are smoothed via overlap + `condition_on_previous_text`, at the cost of transcribing a small amount of redundant audio per chunk.
- Disk I/O increases (continuous WAV writes + per-chunk reads), acceptable for local desktop usage.
- Adds a new Live toggle and a threshold level-meter to Settings; requires threading the "live vs one-shot" mode through the recorder, worker, and GUI.
- The user must tune the input-sensitivity marker once per environment; if it is misplaced, speech may not be segmented into live chunks. There is no max-duration fallback: chunks flush only on a detected silence gap (or the final flush on Stop), so continuous no-pause speech streams only when the user pauses or stops. This deliberately favours fewer chunk boundaries (and fewer hallucinated boundary tokens) over streaming during uninterrupted speech.
- Simple energy VAD may mis-segment noisy or variable-loudness speech; the swappable interface is the escape hatch for a more robust detector later.
- On Stop the entire session is transcribed a second time (once as streaming chunks, then once as a refined full pass), roughly doubling final transcription cost; the refined pass replaces the draft so the user pays for quality on the final result.

## Open notes / future work

- Consider a `webrtcvad`-based detector behind the VAD interface if the energy threshold proves unreliable in noisy environments.
- Remaining tunables are kept internal: `silence_ms` (300ms gap) and `overlap_ms` (~0.75s). These could be exposed in Settings once the defaults are validated in the field.
