"""Desktop GUI for Whisper Desktop (CustomTkinter)."""

from __future__ import annotations

import queue
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..audio.recorder import AudioRecorder
from ..config import AppConfig
from ..whisper_engine.engine import Job, Transcription, WhisperWorker
from ..whisper_engine.languages import model_for_language
from ..whisper_engine.settings import Settings
from .level_meter import level_to_rms
from .settings_window import SettingsWindow

_STATUS_IDLE = "Idle"
_STATUS_RECORDING = "Recording…"
_STATUS_TRANSCRIBING = "Transcribing…"

_MODEL_START = "🎤 Start Recording"
_MODEL_STOP = "⏹ Stop Recording"

_PLACEHOLDER = "Transcribing…"


class GUIApp(ctk.CTk):
    """Main application window."""

    def __init__(
        self,
        settings: Settings | None = None,
        config: AppConfig | None = None,
    ) -> None:
        super().__init__()
        self.title("Whisper Desktop — Voice Dictation")
        self.geometry("640x480")
        self.minsize(520, 380)

        self.settings = settings or Settings()
        self.config = config or AppConfig()
        self.recorder = AudioRecorder(
            device=self.config.input_device_id, live=self.config.live_mode
        )
        self.recorder.energy_threshold = level_to_rms(self.config.live_threshold)
        self._jobs: "queue.Queue[Job | None]" = queue.Queue()
        self._results: "queue.Queue[Transcription]" = queue.Queue()
        self.worker = WhisperWorker(self.settings, self._jobs, self._results)
        self.worker.start()

        self._session_active = False
        self._live_jobs_pending = 0
        self._transcript: list[str] = []
        self._pending_full_path: str | None = None
        self._refining = False

        self._build_ui()
        self.after(100, self._poll_results)

    # ---- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        controls = ctk.CTkFrame(self)
        controls.pack(fill="x", padx=16, pady=(16, 8))

        self.status_label = ctk.CTkLabel(controls, text=_STATUS_IDLE)
        self.status_label.pack(side="left", padx=(12, 20))

        self.record_button = ctk.CTkButton(
            controls, text=_MODEL_START, command=self._on_toggle_record, width=170
        )
        self.record_button.pack(side="right", padx=12, pady=10)

        self.settings_button = ctk.CTkButton(
            controls, text="⚙ Settings", command=self._open_settings, width=90
        )
        self.settings_button.pack(side="right", padx=(0, 4), pady=10)

        self.textbox = ctk.CTkTextbox(self, wrap="word", font=("", 15))
        self.textbox.pack(fill="both", expand=True, padx=16, pady=(8, 8))
        self.textbox.insert("1.0", "")

        actions = ctk.CTkFrame(self)
        actions.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(actions, text="📋 Copy", command=self._copy).pack(
            side="left", padx=(12, 8), pady=10
        )
        ctk.CTkButton(actions, text="💾 Save As…", command=self._save).pack(
            side="left", padx=8, pady=10
        )
        ctk.CTkButton(actions, text="🧹 Clear", command=self._clear).pack(
            side="left", padx=8, pady=10
        )

        self.detail_label = ctk.CTkLabel(actions, text="")
        self.detail_label.pack(side="right", padx=12)

    # ---- recording control ------------------------------------------------
    def _on_toggle_record(self) -> None:
        if self.recorder.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        try:
            self.recorder.start()
        except Exception as exc:
            messagebox.showerror("Start failed", str(exc))
            return
        self.record_button.configure(text=_MODEL_STOP)
        self.status_label.configure(text=_STATUS_RECORDING)
        self._session_active = True
        self._live_jobs_pending = 0
        self._transcript = []
        self.textbox.delete("1.0", "end")
        self.detail_label.configure(text="")
        if self.recorder.live:
            self._jobs.put(Job(reset=True))

    def _stop_and_transcribe(self) -> None:
        try:
            path = self.recorder.stop()
        except ValueError as exc:
            messagebox.showwarning("Nothing recorded", str(exc))
            self._end_session()
            return
        except Exception as exc:
            messagebox.showerror("Stop failed", str(exc))
            return

        self._session_active = False
        self.record_button.configure(state="disabled", text=_MODEL_START)

        if self.recorder.live:
            # ``stop()`` returns the full-session WAV. Defer its refined
            # re-transcription until every streaming chunk has drained, so it
            # replaces the draft instead of being overwritten by it.
            self._pending_full_path = path
            self.status_label.configure(text=_STATUS_TRANSCRIBING)
            self._maybe_submit_full()
            self._refresh()
            return

        self.status_label.configure(text=_STATUS_TRANSCRIBING)
        self._jobs.put(Job(wav_path=path, live=False))

    # ---- settings -------------------------------------------------------------
    def _open_settings(self) -> None:
        SettingsWindow(self, self.config, self._on_settings_saved, recorder=self.recorder)

    def _on_settings_saved(self, config: AppConfig) -> None:
        self.config = config
        self.config.save()
        self.recorder.select_device(config.input_device_id)
        self.recorder.live = config.live_mode
        self.recorder.energy_threshold = level_to_rms(config.live_threshold)

        new_settings = Settings(
            model_size=model_for_language(config.language),
            language=config.language,
        )
        if (new_settings.model_size, new_settings.language) != (
            self.settings.model_size,
            self.settings.language,
        ):
            self._restart_worker(new_settings)

    def _restart_worker(self, settings: Settings) -> None:
        """Stop the current worker and start a fresh one with new settings."""
        self._jobs.put(None)
        self.worker.join(timeout=5)
        self.settings = settings
        self.worker = WhisperWorker(settings, self._jobs, self._results)
        self.worker.start()

    # ---- result polling (runs on the Tk main thread) ----------------------
    def _poll_results(self) -> None:
        if self.recorder.live:
            forwarded = False
            try:
                while True:
                    chunk = self.recorder.ready_chunks.get_nowait()
                    self._jobs.put(Job(wav_path=chunk, live=True))
                    self._live_jobs_pending += 1
                    forwarded = True
            except queue.Empty:
                pass
            if forwarded:
                self._refresh()

        try:
            while True:
                result = self._results.get_nowait()
                self._apply_result(result)
        except queue.Empty:
            pass
        self._maybe_submit_full()
        self.after(100, self._poll_results)

    def _maybe_submit_full(self) -> None:
        """Submit the refined full-session re-transcription once streaming drains."""
        if (
            self._pending_full_path is None
            or self._session_active
            or self._live_jobs_pending > 0
            or not self.recorder.ready_chunks.empty()
        ):
            return
        path = self._pending_full_path
        self._pending_full_path = None
        if path:
            self._refining = True
            self._jobs.put(Job(wav_path=path, live=False, refine=True))
        else:
            self._end_session()

    def _apply_result(self, result: Transcription) -> None:
        if result.error:
            messagebox.showerror("Transcription failed", result.error)
            if result.append:
                self._live_jobs_pending = max(0, self._live_jobs_pending - 1)
            self._end_session()
            return

        self.detail_label.configure(
            text=f"{result.elapsed_seconds}s · {result.language or 'auto'}"
        )

        if result.append:
            self._live_jobs_pending = max(0, self._live_jobs_pending - 1)
            if result.text.strip():
                self._transcript.append(result.text.strip())
            self._refresh()
            self._maybe_submit_full()
            return

        # Full-session (one-shot or refined) result replaces the draft.
        self._refining = False
        self._transcript = [result.text.strip()]
        self._end_session()

    def _refresh(self) -> None:
        """Re-render the transcript, appending a placeholder while work flies."""
        parts = list(self._transcript)
        if self._live_jobs_pending > 0 or self._refining:
            parts.append(_PLACEHOLDER)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", "\n".join(parts))

    def _end_session(self) -> None:
        self._session_active = False
        self._live_jobs_pending = 0
        self._pending_full_path = None
        self._refining = False
        self._refresh()
        self.status_label.configure(text=_STATUS_IDLE)
        self.record_button.configure(state="normal", text=_MODEL_START)

    # ---- actions ------------------------------------------------------------
    def _copy(self) -> None:
        text = self.textbox.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)

    def _save(self) -> None:
        text = self.textbox.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("Nothing to save", "The text area is empty.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _clear(self) -> None:
        self._transcript = []
        self.textbox.delete("1.0", "end")
        self.detail_label.configure(text="")

    # ---- teardown ------------------------------------------------------------
    def destroy(self) -> None:
        """Signal the worker to stop, then close the window."""
        self._jobs.put(None)
        super().destroy()
