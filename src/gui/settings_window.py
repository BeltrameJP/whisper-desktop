"""Modal settings window with a left-hand navigation list.

The window is deliberately structured around a section list so that future
setting categories (e.g. model, appearance) can be added by registering a new
page without restructuring the dialog.
"""

from __future__ import annotations

import customtkinter as ctk

from ..audio import devices
from ..config import AppConfig


class SettingsWindow(ctk.CTkToplevel):
    """A modal dialog to edit and persist application settings.

    ``on_save`` is invoked with the chosen ``input_device_id`` (int or ``None``)
    when the user confirms; the caller is responsible for persisting the config
    and applying the change to the recorder.
    """

    def __init__(
        self,
        master: ctk.CTk,
        config: AppConfig,
        on_save,
    ) -> None:
        super().__init__(master)
        self.title("Settings")
        self.geometry("560x360")
        self.minsize(500, 300)
        self.transient(master)
        self.grab_set()

        self.config = config
        self._on_save = on_save
        self._input_devices = devices.grouped_input_devices()
        self._selected_index = config.input_device_id
        self._current_page = "voice"
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._build_layout()
        self._show_page("voice")

    # ---- layout -----------------------------------------------------------
    def _build_layout(self) -> None:
        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=16, pady=16)

        self.nav = ctk.CTkScrollableFrame(body, width=170)
        self.nav.pack(side="left", fill="y", padx=(0, 12))
        self.nav.pack_propagate(False)

        self.content = ctk.CTkFrame(body)
        self.content.pack(side="left", fill="both", expand=True)

        self._add_nav_item("Voice", "voice", selected=True)

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

    # ---- actions -------------------------------------------------------------
    def _save(self) -> None:
        self._on_save(self._selected_index)
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
