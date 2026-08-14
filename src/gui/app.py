"""Desktop GUI for Whisper Desktop (CustomTkinter)."""
from __future__ import annotations

import queue
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..audio.recorder import AudioRecorder
from ..whisper_engine.engine import Transcription, WhisperWorker
from ..whisper_engine.settings import Settings

_STATUS_IDLE = "Idle"
_STATUS_RECORDING = "Recording…"
_STATUS_TRANSCRIBING = "Transcribing…"

_MODEL_START = "🎤 Start Recording"
_MODEL_STOP = "⏹ Stop Recording"


class GUIApp(ctk.CTk):
    """Main application window."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.title("Whisper Desktop — Voice Dictation")
        self.geometry("640x480")
        self.minsize(520, 380)

        self.settings = settings or Settings()
        self.recorder = AudioRecorder()
        self._jobs: "queue.Queue[str | None]" = queue.Queue()
        self._results: "queue.Queue[Transcription]" = queue.Queue()
        self.worker = WhisperWorker(self.settings, self._jobs, self._results)
        self.worker.start()

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

    def _stop_and_transcribe(self) -> None:
        try:
            path = self.recorder.stop()
        except ValueError as exc:
            messagebox.showwarning("Nothing recorded", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Stop failed", str(exc))
            return

        self.record_button.configure(state="disabled", text=_MODEL_START)
        self.status_label.configure(text=_STATUS_TRANSCRIBING)
        self._jobs.put(path)

    # ---- result polling (runs on the Tk main thread) ----------------------
    def _poll_results(self) -> None:
        try:
            while True:
                result = self._results.get_nowait()
                self._apply_result(result)
        except queue.Empty:
            pass
        self.after(100, self._poll_results)

    def _apply_result(self, result: Transcription) -> None:
        if result.error:
            messagebox.showerror("Transcription failed", result.error)
            self.status_label.configure(text=_STATUS_IDLE)
            self.record_button.configure(state="normal")
            return

        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", result.text)
        self.detail_label.configure(
            text=f"{result.elapsed_seconds}s · {result.language or 'auto'}"
        )
        self.status_label.configure(text=_STATUS_IDLE)
        self.record_button.configure(state="normal")

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
        self.textbox.delete("1.0", "end")
        self.detail_label.configure(text="")

    # ---- teardown ------------------------------------------------------------
    def destroy(self) -> None:
        """Signal the worker to stop, then close the window."""
        self._jobs.put(None)
        super().destroy()
