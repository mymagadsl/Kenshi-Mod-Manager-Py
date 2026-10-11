"""資料夾管理視窗（對應 C# Tooling.xaml）：建立/移除 Steam 模組的目錄連接點、清除空資料夾。"""
from __future__ import annotations

import os
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

import customtkinter as ctk

from kmm import loader
from kmm.config import KenshiToolConfig
from kmm.models import Mod, Source

from . import i18n, theme


@dataclass
class _Entry:
    mod: Mod
    selected: bool = False
    linked: bool = False

    @property
    def link_path(self) -> Path:
        return Path(self.mod.file_path).stem  # 僅名稱，由視窗組合完整路徑


class FolderToolWindow(ctk.CTkToplevel):
    def __init__(self, master, cfg: KenshiToolConfig, on_changed: Callable[[], None]):
        super().__init__(master, fg_color=theme.BG)
        self.cfg, self.on_changed = cfg, on_changed
        self.title(i18n.FT_TITLE)
        self.geometry("760x640")
        self.minsize(640, 500)
        self.transient(master)

        self.entries: list[_Entry] = []
        self._by_uid: dict[str, _Entry] = {}
        self._search_hits: list[_Entry] = []
        self._search_idx = 0

        ctk.CTkLabel(self, text=i18n.FT_HELP, font=theme.font(12), justify="left",
                     text_color=theme.FG_DIM).pack(fill="x", padx=12, pady=(10, 4))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=4)
        self.search_entry = ctk.CTkEntry(top, placeholder_text=i18n.SEARCH_PLACEHOLDER, font=theme.font(12))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.search_entry.bind("<Return>", self._next_hit)
        self.lbl_found = ctk.CTkLabel(top, text="", font=theme.font(12), width=110)
        self.lbl_found.pack(side="left", padx=4)
        for text, cmd in ((i18n.BTN_REFRESH, self.reload),
                          (i18n.FT_SELECT_ALL, self._select_all),
                          (i18n.FT_INVERT, self._invert)):
            ctk.CTkButton(top, text=text, width=90, font=theme.font(12),
                          fg_color=theme.PANEL, command=cmd).pack(side="left", padx=3)

        # 列表
        frame = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        frame.pack(fill="both", expand=True, padx=12, pady=6)
        cols = ("sel", "link", "name", "source")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 selectmode="extended", style="KMM.Treeview")
        for c, t, w in (("sel", i18n.FT_COL_SELECTED, 60), ("link", i18n.FT_COL_LINK, 60),
                        ("name", i18n.COL_NAME, 420), ("source", i18n.COL_SOURCE, 120)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w" if c == "name" else "center", stretch=c == "name")
        self.tree.tag_configure("odd", background=theme.ROW_ALT)
        self.tree.tag_configure("search", background=theme.ROW_SEARCH)
        sb = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb.pack(side="right", fill="y", padx=(2, 4), pady=6)
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<space>", lambda e: (self._toggle_selected_rows(), "break")[1])
        self._build_menu()

        # 下方動作列
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(2, 12))
        for i, (text, cmd, accent) in enumerate((
            (i18n.FT_CLEAR_EMPTY, self._clear_empty, False),
            (i18n.FT_REMOVE_LINKS, lambda: self._run_links(add=False, remove=True), False),
            (i18n.FT_CREATE_LINKS, lambda: self._run_links(add=True, remove=False), True),
            (i18n.FT_TOGGLE_LINKS, lambda: self._run_links(add=True, remove=True), False),
        )):
            bot.grid_columnconfigure(i, weight=1)
            ctk.CTkButton(
                bot, text=text, font=theme.font(12, "bold" if accent else "normal"),
                fg_color=theme.ACCENT if accent else theme.PANEL,
                hover_color=theme.ACCENT_HOVER if accent else None,
                command=cmd,
            ).grid(row=0, column=i, sticky="ew", padx=4)

        self.reload()

    def _build_menu(self) -> None:
        m = tk.Menu(self)
        theme.style_menu(m)
        m.add_command(label=i18n.MENU_OPEN_FOLDER, command=self._open_selected_folders)
        m.add_separator()
        m.add_command(label=i18n.FT_SELECT_ALL, command=self._select_all)
        m.add_command(label=i18n.FT_INVERT, command=self._invert)
        m.add_separator()
        m.add_command(label=i18n.FT_CREATE_LINKS, command=lambda: self._run_links(True, False, from_selection=True))
        m.add_command(label=i18n.FT_REMOVE_LINKS, command=lambda: self._run_links(False, True, from_selection=True))
        m.add_command(label=i18n.FT_TOGGLE_LINKS, command=lambda: self._run_links(True, True, from_selection=True))
        self.tree.bind("<Button-3>", lambda e: m.tk_popup(e.x_root, e.y_root))

    def _link_target(self, mod: Mod) -> Path:
        return self.cfg.mod_folder / Path(mod.file_path).stem

    def reload(self) -> None:
        self.entries = []
        for m in loader.get_list_of_mods(self.cfg):
            lp = self._link_target(m)
            self.entries.append(_Entry(m, linked=lp.exists() and loader.is_link(lp)))
        self._by_uid = {e.mod.uid: e for e in self.entries}
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        hit_uids = {e.mod.uid for e in self._search_hits}
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.entries):
            tags = ["odd"] if i % 2 else []
            if e.mod.uid in hit_uids:
                tags.append("search")
            self.tree.insert("", "end", iid=e.mod.uid, tags=tags, values=(
                "☑" if e.selected else "☐",
                "🔗" if e.linked else "",
                e.mod.display_name, i18n.source_label(e.mod.source)))

    def _on_click(self, ev: tk.Event) -> None:
        row = self.tree.identify_row(ev.y)
        if row and self.tree.identify_column(ev.x) == "#1":
            e = self._by_uid[row]
            e.selected = not e.selected
            self._refresh_tree()

    def _toggle_selected_rows(self) -> None:
        for iid in self.tree.selection():
            self._by_uid[iid].selected = not self._by_uid[iid].selected
        self._refresh_tree()

    def _select_all(self) -> None:
        for e in self.entries:
            e.selected = True
        self._refresh_tree()

    def _invert(self) -> None:
        for e in self.entries:
            e.selected = not e.selected
        self._refresh_tree()

    def _on_search(self, ev: tk.Event) -> None:
        if ev.keysym == "Return":
            return
        q = self.search_entry.get().strip().lower()
        self._search_idx = 0
        self._search_hits = [e for e in self.entries
                             if q and (q in e.mod.display_name.lower() or q in e.mod.file_path.lower())]
        if not q:
            self.lbl_found.configure(text="")
        elif not self._search_hits:
            self.lbl_found.configure(text=i18n.SEARCH_NOT_FOUND)
        else:
            self._focus_hit()
        self._refresh_tree()

    def _next_hit(self, _ev=None) -> None:
        if self._search_hits:
            self._search_idx = (self._search_idx + 1) % len(self._search_hits)
            self._focus_hit()

    def _focus_hit(self) -> None:
        uid = self._search_hits[self._search_idx].mod.uid
        self.lbl_found.configure(text=i18n.SEARCH_FOUND.format(cur=self._search_idx + 1, total=len(self._search_hits)))
        if self.tree.exists(uid):
            self.tree.see(uid)
            self.tree.selection_set(uid)

    def _open_selected_folders(self) -> None:
        for iid in self.tree.selection():
            folder = self._by_uid[iid].mod.folder
            if os.path.isdir(folder):
                os.startfile(folder)

    def _clear_empty(self) -> None:
        removed = []
        if self.cfg.uses_steam and self.cfg.SteamModsPath:
            removed.extend(loader.folder_cleanup(Path(self.cfg.SteamModsPath)))
        if self.cfg.GamePath:
            removed.extend(loader.folder_cleanup(self.cfg.mod_folder))
        messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.FT_DONE_CLEAN.format(n=len(removed)), parent=self)
        self.reload()
        self.on_changed()

    def _run_links(self, add: bool, remove: bool, from_selection: bool = False) -> None:
        targets = ([self._by_uid[i] for i in self.tree.selection()]
                   if from_selection else [e for e in self.entries if e.selected])
        steam_targets = [e for e in targets if e.mod.source is Source.STEAM]
        if not steam_targets:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.FT_NOTHING, parent=self)
            return

        to_add: list[tuple[Path, Path]] = []
        removed = 0
        self.cfg.mod_folder.mkdir(parents=True, exist_ok=True)
        for e in steam_targets:
            lp = self._link_target(e.mod)
            if e.linked and remove:
                try:
                    loader.delete_folder(lp)
                    removed += 1
                except OSError:
                    pass
            elif not e.linked and add:
                to_add.append((lp, Path(e.mod.folder)))

        errors = loader.create_links(to_add) if to_add else []
        self.reload()
        self.on_changed()
        if errors:
            messagebox.showerror(i18n.MSG_TITLE_ERROR, i18n.FT_ERRORS.format(e="\n".join(errors[:5])), parent=self)
        elif to_add:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.FT_DONE_CREATE.format(n=len(to_add)), parent=self)
        elif removed:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.FT_DONE_REMOVE.format(n=removed), parent=self)
