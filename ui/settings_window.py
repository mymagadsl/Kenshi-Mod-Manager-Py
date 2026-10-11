"""設定視窗（對應 C# Configuration.xaml）。"""
from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from kmm import loader, steam
from kmm.config import KenshiToolConfig

from . import i18n, theme


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, cfg: KenshiToolConfig, on_saved: Callable[[], None]):
        super().__init__(master, fg_color=theme.BG)
        self.cfg, self.on_saved = cfg, on_saved
        self.title(i18n.SET_TITLE)
        self.geometry("620x380")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)

        row = 0
        self.game_entry = self._path_row(row, i18n.SET_GAME_PATH, cfg.GamePath)
        row += 2
        self.steam_entry = self._path_row(row, i18n.SET_STEAM_PATH, cfg.SteamModsPath)
        row += 2
        ctk.CTkLabel(self, text=i18n.SET_MASTERLIST, font=theme.font(12)).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 2))
        row += 1
        self.ml_entry = ctk.CTkEntry(self, font=theme.font(12))
        self.ml_entry.insert(0, cfg.MasterlistSource)
        self.ml_entry.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16)

        row += 1
        lang_frame = ctk.CTkFrame(self, fg_color="transparent")
        lang_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 2))
        ctk.CTkLabel(lang_frame, text=i18n.SET_LANGUAGE, font=theme.font(12)).pack(
            side="left", padx=(0, 12)
        )
        self._label_to_lang = {label: code for code, label in i18n.LANGUAGES.items()}
        current_label = i18n.LANGUAGES.get(cfg.Language, i18n.LANGUAGES["zh_TW"])
        self.lang_var = ctk.StringVar(value=current_label)
        self.lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=list(i18n.LANGUAGES.values()),
            variable=self.lang_var,
            width=160,
            font=theme.font(12),
            dropdown_font=theme.font(12),
        )
        self.lang_menu.pack(side="left")

        row += 1
        self.auto_var = ctk.BooleanVar(value=cfg.CheckForUpdatesAutomatically)
        ctk.CTkCheckBox(self, text=i18n.SET_AUTO_UPDATE, variable=self.auto_var,
                        font=theme.font(12)).grid(row=row, column=0, sticky="w", padx=16, pady=10)

        row += 1
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=row, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 14))
        ctk.CTkButton(btns, text=i18n.SET_AUTODETECT, width=110, font=theme.font(12),
                      fg_color=theme.PANEL, command=self._autodetect).pack(side="left")
        ctk.CTkButton(btns, text=i18n.SET_CLEAR_LOGS, width=140, font=theme.font(12),
                      fg_color=theme.PANEL, command=self._clear_logs).pack(side="left", padx=(8, 0))
        ctk.CTkButton(btns, text=i18n.SET_SAVE, width=100, font=theme.font(12, "bold"),
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                      command=self._save).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btns, text=i18n.SET_CANCEL, width=90, font=theme.font(12),
                      fg_color=theme.PANEL, command=self.destroy).pack(side="right")

    def _path_row(self, row: int, label: str, initial: str) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=label, font=theme.font(12)).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 2))
        ent = ctk.CTkEntry(self, font=theme.font(12))
        ent.insert(0, initial or "")
        ent.grid(row=row + 1, column=0, sticky="ew", padx=(16, 6))
        ctk.CTkButton(self, text=i18n.SET_BROWSE, width=80, font=theme.font(12),
                      command=lambda e=ent: self._browse(e)).grid(row=row + 1, column=1, padx=(0, 16))
        return ent

    def _browse(self, entry: ctk.CTkEntry) -> None:
        folder = filedialog.askdirectory(parent=self, initialdir=entry.get() or None)
        if folder:
            entry.delete(0, "end")
            entry.insert(0, folder)

    def _autodetect(self) -> None:
        found = steam.find_kenshi()
        if not found:
            messagebox.showwarning(i18n.MSG_TITLE_INFO, i18n.SET_DETECT_FAIL, parent=self)
            return
        game, ws = found
        for ent, val in ((self.game_entry, str(game)), (self.steam_entry, str(ws))):
            ent.delete(0, "end")
            ent.insert(0, val)

    def _clear_logs(self) -> None:
        removed = loader.clear_logs_and_backups()
        messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.SET_LOGS_CLEARED.format(n=removed), parent=self)

    def _save(self) -> None:
        self.cfg.GamePath = self.game_entry.get().strip()
        self.cfg.SteamModsPath = self.steam_entry.get().strip() or "NONE"
        self.cfg.MasterlistSource = self.ml_entry.get().strip() or self.cfg.MasterlistSource
        self.cfg.CheckForUpdatesAutomatically = bool(self.auto_var.get())
        self.cfg.Language = self._label_to_lang.get(self.lang_var.get(), "zh_TW")
        i18n.set_language(self.cfg.Language)
        self.cfg.save()
        self.on_saved()
        self.destroy()
