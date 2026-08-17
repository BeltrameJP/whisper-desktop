"""Modal settings window with a left-hand navigation list.

The window is deliberately structured around a section list so that future
setting categories (e.g. model, appearance) can be added by registering a new
page without restructuring the dialog.
"""

from __future__ import annotations

import threading
from tkinter import messagebox

import customtkinter as ctk

from ..audio import devices
from ..config import AppConfig
from ..whisper_engine import downloader
from ..whisper_engine.languages import language_options, model_for_language
from .level_meter import LevelMeter, level_to_rms, rms_to_level

_MODEL_SIZE_MB = {"base": "~145 MB", "base.en": "~145 MB"}


class SettingsWindow(ctk.CTkToplevel):
    """A modal dialog to edit and persist application settings.

    ``on_save`` is invoked with the edited :class:`AppConfig` when the user
    confirms; the caller is responsible for persisting it and applying the
    changes (e.g. to the recorder).

    ``recorder`` is used to run a live level meter while the dialog is open;
    it may be ``None`` (e.g. in tests) to disable monitoring.
    """

    def __init__(
        self,
        master: ctk.CTk,
        config: AppConfig,
        on_save,
        recorder=None,
    ) -> None:
        super().__init__(master)
        self.title("Settings")
        self.geometry("560x460")
        self.minsize(500, 380)
        self.transient(master)
        self.grab_set()

        self._working = AppConfig(
            input_device_id=config.input_device_id,
            live_mode=config.live_mode,
            live_threshold=config.live_threshold,
            language=config.language,
        )
        self._selected_language = config.language
        self._options = language_options()
        self._on_save = on_save
        self._recorder = recorder
        self._input_devices = devices.grouped_input_devices()
        self._selected_index = config.input_device_id
        self._current_page = "voice"
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._poll_job = None

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._build_layout()
        self._show_page("voice")
        self._start_monitoring()

    # ---- layout -----------------------------------------------------------
    def _build_layout(self) -> None:
        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=16, pady=16)

        self.nav = ctk.CTkFrame(body, width=170)
        self.nav.pack(side="left", fill="y", padx=(0, 12))

        self.content = ctk.CTkFrame(body)
        self.content.pack(side="left", fill="both", expand=True)

        self._add_nav_item("Voice", "voice", selected=True)
        self._add_nav_item("Transcription", "transcription")

    def _add_nav_item(self, label: str, key: str, *, selected: bool = False) -> None:
        btn = ctk.CTkButton(
            self.nav,
            text=label,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("#d5d5d5", "#333333"),
            command=lambda k=key: self._show_page(k),
        )
        btn.pack(fill="x", pady=2, padx=4)
        self._nav_buttons[key] = btn
        if selected:
            btn.configure(fg_color=("#c3c3c3", "#3d3d3d"))

    # ---- page switching -----------------------------------------------------
    def _show_page(self, key: str) -> None:
        self._current_page = key
        for child in self.content.winfo_children():
            child.destroy()

        if key == "voice":
            self._build_voice_page()
        elif key == "transcription":
            self._build_transcription_page()

        for btn in self._nav_buttons.values():
            btn.configure(fg_color="transparent")
        self._nav_buttons[key].configure(fg_color=("#c3c3c3", "#3d3d3d"))

    # ---- voice page ---------------------------------------------------------
    def _build_voice_page(self) -> None:
        heading = ctk.CTkLabel(self.content, text="Voice", font=("", 20, "bold"))
        heading.pack(anchor="w", padx=16, pady=(16, 4))

        subtitle = ctk.CTkLabel(
            self.content,
            text="Choose the microphone used for dictation.",
            font=("", 12),
            text_color="gray",
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 16))

        self._live_var = ctk.BooleanVar(value=bool(self._working.live_mode))
        live_row = ctk.CTkFrame(self.content, fg_color="transparent")
        live_row.pack(anchor="w", padx=16, pady=6)
        live_switch = ctk.CTkSwitch(live_row, text="Live transcription", variable=self._live_var)
        live_switch.pack(side="left", padx=(0, 12))
        live_hint = ctk.CTkLabel(
            self.content,
            text="Stream text while you speak. Off = transcribe on stop.",
            font=("", 11),
            text_color="gray",
        )
        live_hint.pack(anchor="w", padx=16, pady=(0, 8))

        sens_heading = ctk.CTkLabel(
            self.content,
            text="Input sensitivity",
            font=("", 13, "bold"),
        )
        sens_heading.pack(anchor="w", padx=16, pady=(12, 4))
        sens_hint = ctk.CTkLabel(
            self.content,
            text="Drag the marker just above your silence level; speech above it is captured.",
            font=("", 11),
            text_color="gray",
        )
        sens_hint.pack(anchor="w", padx=16, pady=(0, 8))

        self.level_meter = LevelMeter(
            self.content,
            width=320,
            height=26,
            threshold=self._working.live_threshold,
            on_change=self._on_threshold_change,
        )
        self.level_meter.pack(anchor="w", padx=16, pady=4)

        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(row, text="Microphone:").pack(side="left", padx=(0, 12))

        self.device_menu = ctk.CTkOptionMenu(
            row, values=self._device_labels(), command=self._on_pick_device
        )
        self.device_menu.pack(side="left")

        path_hint = ctk.CTkLabel(
            self.content,
            text=f"Saved to: {AppConfig.user_config_path()}",
            font=("", 11),
            text_color="gray",
        )
        path_hint.pack(anchor="w", padx=16, pady=(12, 0))

        footer = ctk.CTkFrame(self.content, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=16, pady=16)
        ctk.CTkButton(footer, text="Save", command=self._save).pack(side="right")
        ctk.CTkButton(footer, text="Cancel", fg_color="transparent", command=self._cancel).pack(
            side="right", padx=(0, 8)
        )

    def _device_labels(self) -> list[str]:
        labels = [devices.device_label(None)]
        labels += [devices.device_label(d.index, self._input_devices) for d in self._input_devices]
        return labels

    def _on_pick_device(self, label: str) -> None:
        if label == devices.device_label(None):
            self._selected_index = None
            return
        try:
            index = int(label.split(":", 1)[0])
        except ValueError:
            return
        if any(d.index == index for d in self._input_devices):
            self._selected_index = index

    # ---- transcription page ----------------------------------------------------
    def _build_transcription_page(self) -> None:
        heading = ctk.CTkLabel(self.content, text="Transcription", font=("", 20, "bold"))
        heading.pack(anchor="w", padx=16, pady=(16, 4))

        subtitle = ctk.CTkLabel(
            self.content,
            text="Choose the language to dictate in and manage its model.",
            font=("", 12),
            text_color="gray",
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 16))

        row = ctk.CTkFrame(self.content, fg_color="transparent")
        row.pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(row, text="Language:").pack(side="left", padx=(0, 12))

        self.language_combo = ctk.CTkComboBox(
            row,
            width=260,
            values=[label for _, label in self._options],
            command=self._on_pick_language,
        )
        self.language_combo.set(self._label_for(self._selected_language))
        self.language_combo.pack(side="left")
        self.language_combo.bind("<KeyRelease>", self._filter_languages)

        self.model_status_label = ctk.CTkLabel(
            self.content,
            text="",
            font=("", 11),
            text_color="gray",
        )
        self.model_status_label.pack(anchor="w", padx=16, pady=(10, 4))

        self.download_button = ctk.CTkButton(
            self.content, text="Download model", command=self._download_now
        )
        self.download_button.pack(anchor="w", padx=16, pady=4)

        self.progress_bar = ctk.CTkProgressBar(self.content, width=420)
        self.progress_bar.set(0)
        self._refresh_model_status()

        footer = ctk.CTkFrame(self.content, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=16, pady=16)
        ctk.CTkButton(footer, text="Save", command=self._save).pack(side="right")
        ctk.CTkButton(footer, text="Cancel", fg_color="transparent", command=self._cancel).pack(
            side="right", padx=(0, 8)
        )

    def _label_for(self, code: str | None) -> str:
        for option_code, label in self._options:
            if option_code == code:
                return label
        return self._options[0][1]

    def _on_pick_language(self, label: str) -> None:
        self._selected_language = self._code_from_label(label)
        self._refresh_model_status()

    def _code_from_label(self, label: str) -> str | None:
        if not label or label == "Auto":
            return None
        if label.endswith(")") and "(" in label:
            return label.rsplit("(", 1)[1][:-1].strip()
        return None

    def _filter_languages(self, _event) -> None:
        query = self.language_combo.get().strip().lower()
        filtered = [label for _, label in self._options if query in label.lower()]
        self.language_combo.configure(values=filtered or [label for _, label in self._options])

    def _refresh_model_status(self) -> None:
        model = model_for_language(self._selected_language)
        present = downloader.model_present(model)
        size = _MODEL_SIZE_MB.get(model, "")
        state = "downloaded" if present else "not downloaded"
        self.model_status_label.configure(text=f"Model: {model} ({state}, {size})")
        self.download_button.configure(state="disabled" if present else "normal")
        self.progress_bar.pack_forget()

    def _download_now(self) -> None:
        model = model_for_language(self._selected_language)
        if downloader.model_present(model):
            return
        self._run_download(model, on_done=self._refresh_model_status)

    def _run_download(self, model: str, on_done) -> None:
        size = _MODEL_SIZE_MB.get(model, "")
        if not messagebox.askyesno(
            "Download model",
            f"The {model} model ({size}) isn't downloaded yet.\n\nDownload it now?",
        ):
            on_done()
            return

        self._set_downloading(True)

        def _on_progress(done: int, total: int) -> None:
            frac = done / total if total else 0.0
            self.after(0, lambda: self.progress_bar.set(min(1.0, max(0.0, frac))))

        def _run() -> None:
            try:
                downloader.download_model(model, progress=_on_progress)
            except Exception as exc:
                self.after(0, lambda e=exc: self._download_error(e))
                return
            self.after(0, on_done)

        threading.Thread(target=_run, daemon=True).start()

    def _download_error(self, exc: Exception) -> None:
        self._set_downloading(False)
        messagebox.showerror("Download failed", str(exc))

    def _set_downloading(self, active: bool) -> None:
        state = "disabled" if active else "normal"
        self.download_button.configure(state=state)
        if active:
            self.progress_bar.set(0)
            self.progress_bar.pack(anchor="w", padx=16, pady=4)
        else:
            self.progress_bar.pack_forget()

    # ---- level meter / monitoring ---------------------------------------------
    def _on_threshold_change(self, level: float) -> None:
        self._working.live_threshold = level
        if self._recorder is not None:
            self._recorder.energy_threshold = level_to_rms(level)

    def _start_monitoring(self) -> None:
        if self._recorder is None:
            return
        if not self._recorder.is_recording:
            try:
                self._recorder.monitor()
            except Exception:
                pass  # monitoring is best-effort
        self._poll_job = self.after(100, self._poll_level)

    def _poll_level(self) -> None:
        if self._recorder is not None and self._current_page == "voice":
            self.level_meter.set_level(rms_to_level(self._recorder.last_rms))
        self._poll_job = self.after(100, self._poll_level)

    def _stop_monitoring(self) -> None:
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
        if self._recorder is not None:
            self._recorder.stop_monitor()

    # ---- actions -------------------------------------------------------------
    def _save(self) -> None:
        self._working.input_device_id = self._selected_index
        if hasattr(self, "level_meter") and self.level_meter.winfo_exists():
            self._working.live_mode = bool(self._live_var.get())
            self._working.live_threshold = self.level_meter.threshold
        self._working.language = self._selected_language

        model = model_for_language(self._working.language)
        if not downloader.model_present(model):
            self._run_download(model, on_done=self._finish_save)
            return
        self._finish_save()

    def _finish_save(self) -> None:
        self._stop_monitoring()
        self._on_save(self._working)
        self.destroy()

    def _cancel(self) -> None:
        self._stop_monitoring()
        self.destroy()
