"""主視窗（對應 C# KenshiModTool/MainWindow.xaml.cs）。"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from kmm import conflicts, constants, loader, logging_util, name_translator, rules, steam
from kmm.config import KenshiToolConfig
from kmm.models import Mod, Source

from . import i18n, theme
from .about_window import AboutWindow
from .detail_panel import DetailPanel
from .folder_tool_window import FolderToolWindow
from .mod_list import ModListView
from .settings_window import SettingsWindow


class MainWindow(ctk.CTk):
    def __init__(self):
        theme.setup()
        super().__init__(fg_color=theme.BG)
        theme.style_treeview(self)

        self.cfg = KenshiToolConfig.load()
        i18n.set_language(self.cfg.Language)

        self.title(f"[v{constants.APP_VERSION}] {i18n.APP_TITLE}")
        self.geometry("1040x820")
        self.minsize(760, 640)

        self.mods: list[Mod] = []
        self.conflict_index: dict[str, conflicts.ConflictDetail] = {}
        self.translation_map: dict[str, list[str]] = {}
        self.patch_map: dict[str, list[str]] = {}
        self.search_hits: list[Mod] = []
        self.search_idx = 0
        self.dirty = False
        self._busy = False
        self._search_after: str | None = None
        self._i18n_bindings: list[tuple[object, str]] = []

        self._build_ui()
        self._build_context_menu()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.after(50, self._startup)

    # ------------------------------------------------------------ 版面
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=3)
        self.grid_rowconfigure(4, weight=2)

        # Row 0：工具列
        bar = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        for key, cmd, accent in (
            ("BTN_SAVE_ORDER", self.save_mod_list, True),
            ("BTN_AUTO_ORDER", self.auto_order_mods, False),
            ("BTN_CHECK_CONFLICTS", self.check_conflicts, False),
            ("BTN_UPDATE_RULES", self.update_rules_manual, False),
            ("BTN_FCS", self.start_fcs, False),
            ("BTN_SETTINGS", self.open_settings, False),
        ):
            btn = ctk.CTkButton(
                bar, text=getattr(i18n, key), height=34, font=theme.font(13, "bold" if accent else "normal"),
                fg_color=theme.ACCENT if accent else "transparent",
                hover_color=theme.ACCENT_HOVER if accent else "#2f333a",
                command=cmd,
            )
            btn.pack(side="left", padx=6, pady=6)
            self._i18n_bindings.append((btn, key))
        self.lbl_status = ctk.CTkLabel(bar, text="", font=theme.font(12), text_color=theme.FG_DIM)
        self.lbl_status.pack(side="right", padx=12)

        # Row 1：搜尋 + 篩選
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        sf.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(sf, placeholder_text=i18n.SEARCH_PLACEHOLDER,
                                         height=32, font=theme.font(12))
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", self._on_search_enter)
        btn_refresh = ctk.CTkButton(sf, text=i18n.BTN_REFRESH, width=100, height=32, font=theme.font(12),
                                    fg_color=theme.PANEL, command=self.reload_mods)
        btn_refresh.grid(row=0, column=1)
        self._i18n_bindings.append((btn_refresh, "BTN_REFRESH"))

        ff = ctk.CTkFrame(sf, fg_color="transparent")
        ff.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        lbl_filter = ctk.CTkLabel(ff, text=i18n.FILTER_LABEL, font=theme.font(12))
        lbl_filter.pack(side="left", padx=(0, 8))
        self._i18n_bindings.append((lbl_filter, "FILTER_LABEL"))
        self.var_steam = ctk.BooleanVar(value=True)
        self.var_regular = ctk.BooleanVar(value=True)
        self.var_active_only = ctk.BooleanVar(value=False)
        self.var_conflict_only = ctk.BooleanVar(value=False)
        self.var_ignore_translation = ctk.BooleanVar(value=True)
        self.var_ignore_patch = ctk.BooleanVar(value=True)
        self.var_show_zh = ctk.BooleanVar(value=True)
        for key, var, cmd in (
            ("FILTER_STEAM", self.var_steam, self.refresh_view),
            ("FILTER_REGULAR", self.var_regular, self.refresh_view),
            ("FILTER_ACTIVE_ONLY", self.var_active_only, self.refresh_view),
            ("FILTER_CONFLICT_ONLY", self.var_conflict_only, self.refresh_view),
            ("FILTER_IGNORE_TRANSLATION", self.var_ignore_translation, self._on_toggle_conflict_filter),
            ("FILTER_IGNORE_PATCH", self.var_ignore_patch, self._on_toggle_conflict_filter),
            ("FILTER_SHOW_ZH_NAME", self.var_show_zh, self.refresh_view),
        ):
            chk = ctk.CTkCheckBox(ff, text=getattr(i18n, key), variable=var, font=theme.font(12),
                                  checkbox_width=18, checkbox_height=18,
                                  command=cmd)
            chk.pack(side="left", padx=8)
            self._i18n_bindings.append((chk, key))
        self.lbl_search = ctk.CTkLabel(ff, text="", font=theme.font(12), text_color=theme.ACCENT)
        self.lbl_search.pack(side="right", padx=4)

        # Row 2：模組列表
        self.mod_list = ModListView(
            self,
            on_select=lambda sel: self.detail.show(sel[0] if sel else None),
            on_toggle=self._toggle_mods,
            on_reorder=self._drag_reorder,
            on_order_edit=self._manual_order,
            on_context=self._show_context_menu,
            on_drag_blocked=lambda: self._flash_status(i18n.MSG_DRAG_NEED_ORDER_SORT),
        )
        self.mod_list.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        self.mod_list.bind("<<ResortRequested>>", lambda e: self.refresh_view())

        # Row 3：資料夾捷徑列
        folders = ctk.CTkFrame(self, fg_color="transparent")
        folders.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
        for col, (key, cmd) in enumerate((
            ("BTN_OPEN_GAME", self.open_game_folder),
            ("BTN_OPEN_GAME_MODS", self.open_game_mods_folder),
            ("BTN_OPEN_STEAM_MODS", self.open_steam_mods_folder),
            ("BTN_FOLDER_TOOL", self.open_folder_tool),
        )):
            folders.grid_columnconfigure(col, weight=1)
            fbtn = ctk.CTkButton(folders, text=getattr(i18n, key), height=30, font=theme.font(12),
                                 fg_color=theme.PANEL, command=cmd)
            fbtn.grid(row=0, column=col, sticky="ew", padx=3)
            self._i18n_bindings.append((fbtn, key))

        # Row 4：詳細資訊面板
        self.detail = DetailPanel(
            self,
            dep_ok=lambda mod, dep: loader.dependency_ok(self.mods, mod, dep),
            url_of=lambda mod: mod.url(self.cfg.SteamPageUrl, self.cfg.NexusPageUrl),
            conflict_of=lambda key: self.conflict_index.get(key),
            translation_of=lambda mod: self.translation_map.get(mod.file_name),
            patch_of=lambda mod: self.patch_map.get(mod.file_name),
            on_mod_click=self._jump_to_mod_by_name,
        )
        self.detail.grid(row=4, column=0, sticky="nsew", padx=10, pady=4)

        # Row 5：設定檔 + 關於 + 啟動遊戲
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=5, column=0, sticky="ew", padx=10, pady=(2, 10))
        for col, (key, cmd, accent) in enumerate((
            ("BTN_SAVE_PROFILE", self.save_profile, False),
            ("BTN_LOAD_PROFILE", self.load_profile, False),
            ("BTN_ABOUT", self.open_about, False),
            ("BTN_LAUNCH", self.launch_game, True),
        )):
            bottom.grid_columnconfigure(col, weight=1)
            bbtn = ctk.CTkButton(
                bottom, text=getattr(i18n, key), height=36,
                font=theme.font(13, "bold" if accent else "normal"),
                fg_color=theme.ACCENT if accent else theme.PANEL,
                hover_color=theme.ACCENT_HOVER if accent else None,
                command=cmd,
            )
            bbtn.grid(row=0, column=col, sticky="ew", padx=3)
            self._i18n_bindings.append((bbtn, key))

    def apply_language(self) -> None:
        """根據目前 i18n 語言設定，即時重新整理主視窗所有介面文字。"""
        i18n.set_language(self.cfg.Language)
        self.title(f"[v{constants.APP_VERSION}] {i18n.APP_TITLE}")
        for widget, key in self._i18n_bindings:
            widget.configure(text=getattr(i18n, key))
        self.search_entry.configure(placeholder_text=i18n.SEARCH_PLACEHOLDER)
        self.mod_list._update_headings()
        self._build_context_menu()
        self._run_search()
        self.refresh_view()

    def _build_context_menu(self) -> None:
        m = tk.Menu(self)
        theme.style_menu(m)
        m.add_command(label=i18n.MENU_VISIT_PAGE, command=self.visit_mod_page)
        m.add_command(label=i18n.MENU_OPEN_FOLDER, command=self.open_selected_mod_folders)
        m.add_command(label=i18n.MENU_EDIT_ZH_NAME, command=self.edit_selected_zh_name)
        m.add_command(label=i18n.MENU_TRANSLATE_MISSING, command=self.translate_missing_mods)
        m.add_separator()
        m.add_command(label=i18n.MENU_ACTIVATE, command=lambda: self._set_active_selected(True))
        m.add_command(label=i18n.MENU_DEACTIVATE, command=lambda: self._set_active_selected(False))
        m.add_command(label=i18n.MENU_TOGGLE, command=lambda: self._set_active_selected(None))
        m.add_separator()
        m.add_command(label=i18n.MENU_MOVE_TOP, command=lambda: self._move_edge(top=True))
        m.add_command(label=i18n.MENU_MOVE_BOTTOM, command=lambda: self._move_edge(top=False))
        m.add_separator()
        m.add_command(label=i18n.MENU_UNSUBSCRIBE, command=self.unsubscribe_selected)
        self._unsub_idx = m.index("end")
        m.add_separator()
        m.add_command(label=i18n.MENU_REMOVE_MISSING, command=self.remove_missing_mods)
        m.add_command(label=i18n.MENU_REMOVE_INACTIVE, command=self.remove_inactive_mods)
        self.ctx_menu = m

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-s>", lambda e: self.save_mod_list())
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.bind("<F5>", lambda e: self.reload_mods())
        self.bind("<Alt-Up>", lambda e: self._nudge(-1))
        self.bind("<Alt-Down>", lambda e: self._nudge(1))

    # ------------------------------------------------------------ 啟動流程
    def _startup(self) -> None:
        logging_util.reset(constants.ERROR_FILE)
        logging_util.reset(constants.LOG_FILE)

        if not self.cfg.GamePath:
            found = steam.find_kenshi()
            if found:
                self.cfg.GamePath, self.cfg.SteamModsPath = str(found[0]), str(found[1])
            elif not messagebox.askyesno(i18n.MSG_TITLE_CONFIRM, i18n.MSG_ASK_STEAM, parent=self):
                self.cfg.SteamModsPath = "NONE"

        if not self.cfg.GamePath or not Path(self.cfg.GamePath).is_dir():
            guess = steam.guess_kenshi_folder()
            chosen = filedialog.askdirectory(
                parent=self, title=i18n.MSG_ASK_GAME_FOLDER,
                initialdir=str(guess) if guess else None,
            )
            if chosen:
                self.cfg.GamePath = chosen

        self.cfg.save()
        self.reload_mods(first_load=True)

        if self.cfg.CheckForUpdatesAutomatically:
            threading.Thread(target=self._bg_update_rules, daemon=True).start()

    def _bg_update_rules(self) -> None:
        if rules.check_masterlist_update(self.cfg):
            self.cfg.save()

    # ------------------------------------------------------------ 清單操作
    def reload_mods(self, first_load: bool = False) -> None:
        self.lbl_status.configure(text=i18n.MSG_LOADING)
        self.update_idletasks()
        self.mods = loader.get_list_of_mods(self.cfg)
        self.translation_map = conflicts.detect_translation_map(self.mods)
        self.patch_map = conflicts.detect_patch_map(self.mods, self.translation_map)
        name_translator.populate_zh_names(self.mods, self.translation_map, self.patch_map)
        self.conflict_index.clear()
        self.dirty = False
        if first_load and self.mods:
            loader.backup_subscribed_list(self.cfg, self.mods)
        self._run_search()
        self.refresh_view()

    def _on_toggle_conflict_filter(self) -> None:
        if self.conflict_index or any(m.conflicts for m in self.mods):
            self.check_conflicts(silent=True)
        else:
            self.refresh_view()

    def refresh_view(self) -> None:
        show_s, show_r = self.var_steam.get(), self.var_regular.get()
        active_only = self.var_active_only.get()
        conflict_only = self.var_conflict_only.get()
        visible = [
            m for m in self.mods
            if ((show_s and m.source is Source.STEAM) or (show_r and m.source is Source.GAME_FOLDER)
                or (not show_s and not show_r))
            and (not active_only or m.active)
            and (not conflict_only or bool(m.conflicts))
        ]
        missing = {m.uid for m in self.mods if m.active and loader.missing_dependencies(self.mods, m)}
        search = {m.uid for m in self.search_hits}
        self.mod_list.set_items(visible, search=search, missing=missing, show_zh=self.var_show_zh.get())

        sel = self.mod_list.selected()
        self.detail.show(sel[0] if sel else None)

        active_count = sum(1 for m in self.mods if m.active)
        cmods = sum(1 for m in self.mods if m.conflicts)
        mark = " *" if self.dirty else ""
        if self.conflict_index:
            summary = i18n.STATUS_SUMMARY_CONFLICTS.format(
                total=len(self.mods), active=active_count, cmods=cmods, citems=len(self.conflict_index)
            )
        else:
            summary = i18n.STATUS_SUMMARY.format(total=len(self.mods), active=active_count)
        self.lbl_status.configure(text=summary + mark)

    def _flash_status(self, msg: str) -> None:
        self.lbl_status.configure(text=msg)

    def _mark_dirty(self) -> None:
        self.dirty = True
        self.refresh_view()

    def _toggle_mods(self, targets: list[Mod]) -> None:
        if not targets:
            return
        loader.set_active(self.mods, targets, None)
        self._mark_dirty()

    def _set_active_selected(self, state: bool | None) -> None:
        sel = self.mod_list.selected()
        if sel:
            loader.set_active(self.mods, sel, state)
            self._mark_dirty()

    def _drag_reorder(self, dragged: Mod, target: Mod) -> None:
        if not dragged.active:
            dragged.active = True
        new_order = target.order if target.active else 0
        loader.set_new_order(self.mods, dragged, new_order)
        self._mark_dirty()

    def _manual_order(self, mod: Mod, raw: str) -> None:
        try:
            value = int(raw)
        except ValueError:
            messagebox.showwarning(i18n.MSG_TITLE_ERROR, i18n.MSG_NUMBERS_ONLY, parent=self)
            return
        mod.active = value >= 0
        if mod.active:
            loader.set_new_order(self.mods, mod, value)
        else:
            mod.order = -1
            loader.normalize_orders(self.mods)
        self._mark_dirty()

    def _move_edge(self, top: bool) -> None:
        for mod in self.mod_list.selected():
            if not mod.active:
                mod.active = True
            loader.set_new_order(self.mods, mod, 0 if top else len(self.mods))
        self._mark_dirty()

    def _nudge(self, delta: int) -> None:
        sel = self.mod_list.selected()
        if len(sel) == 1 and sel[0].active:
            loader.set_new_order(self.mods, sel[0], max(0, sel[0].order + delta))
            self._mark_dirty()
            self.mod_list.see(sel[0], select=True)

    # ------------------------------------------------------------ 搜尋
    def _on_search_key(self, e: tk.Event) -> None:
        if e.keysym == "Return":
            return
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(180, self._run_search_and_refresh)

    def _run_search(self) -> None:
        q = self.search_entry.get().strip().lower()
        self.search_idx = 0
        if not q:
            self.search_hits = []
            self.lbl_search.configure(text="")
            return
        self.search_hits = sorted(
            (m for m in self.mods
             if q in m.display_name.lower()
             or q in (m.zh_name or "").lower()
             or q in (m.title or "").lower()
             or q in m.file_path.lower()
             or (m.id or "").lower() == q),
            key=lambda m: (not m.active, m.order),
        )
        if not self.search_hits:
            self.lbl_search.configure(text=i18n.SEARCH_NOT_FOUND)
        else:
            self.lbl_search.configure(text=i18n.SEARCH_FOUND.format(cur=1, total=len(self.search_hits)))

    def _run_search_and_refresh(self) -> None:
        self._run_search()
        self.refresh_view()
        if self.search_hits:
            self.mod_list.see(self.search_hits[0], select=True)

    def _on_search_enter(self, _e=None) -> None:
        if not self.search_hits:
            return
        self.search_idx = (self.search_idx + 1) % len(self.search_hits)
        self.lbl_search.configure(
            text=i18n.SEARCH_FOUND.format(cur=self.search_idx + 1, total=len(self.search_hits)))
        self.mod_list.see(self.search_hits[self.search_idx], select=True)

    def _jump_to_mod_by_name(self, mod_name: str) -> None:
        """從衝突明細點擊模組名稱時，自動捲動並選取主清單中的對應模組。"""
        q = mod_name.strip().lower()
        target = next(
            (m for m in self.mods if m.active and (m.file_name.lower() == q or m.display_name.lower() == q)),
            None,
        ) or next(
            (m for m in self.mods if m.file_name.lower() == q or m.display_name.lower() == q),
            None,
        )
        if target is None:
            return
        filter_changed = False
        if target.source is Source.STEAM and not self.var_steam.get():
            self.var_steam.set(True)
            filter_changed = True
        elif target.source is Source.GAME_FOLDER and not self.var_regular.get():
            self.var_regular.set(True)
            filter_changed = True
        if not target.active and self.var_active_only.get():
            self.var_active_only.set(False)
            filter_changed = True
        if not target.conflicts and self.var_conflict_only.get():
            self.var_conflict_only.set(False)
            filter_changed = True
        if filter_changed:
            self.refresh_view()
        self.mod_list.see(target, select=True)
        self.detail.show(target)

    # ------------------------------------------------------------ 右鍵選單
    def _show_context_menu(self, e: tk.Event) -> None:
        row = self.mod_list.tree.identify_row(e.y)
        if row and row not in self.mod_list.tree.selection():
            self.mod_list.tree.selection_set(row)
        sel = self.mod_list.selected()
        has_steam = any(m.source is Source.STEAM and m.id for m in sel)
        self.ctx_menu.entryconfigure(self._unsub_idx, state="normal" if has_steam else "disabled")
        self.ctx_menu.tk_popup(e.x_root, e.y_root)

    def visit_mod_page(self) -> None:
        for m in self.mod_list.selected():
            webbrowser.open(m.url(self.cfg.SteamPageUrl, self.cfg.NexusPageUrl))

    def open_selected_mod_folders(self) -> None:
        bad = False
        for m in self.mod_list.selected():
            if os.path.isdir(m.folder):
                os.startfile(m.folder)
            else:
                bad = True
        if bad:
            messagebox.showerror(i18n.MSG_TITLE_ERROR, i18n.MSG_GAME_FOLDER_BAD, parent=self)

    def edit_selected_zh_name(self) -> None:
        """讓使用者自訂選取模組的繁體中文別名，並儲存至 mod_names_zh.json。"""
        sel = self.mod_list.selected()
        if not sel:
            return
        mod = sel[0]
        new_zh = simpledialog.askstring(
            i18n.DLG_EDIT_ZH_TITLE,
            i18n.DLG_EDIT_ZH_PROMPT.format(name=mod.display_name),
            initialvalue=mod.zh_name or "",
            parent=self,
        )
        if new_zh is None:
            return
        name_translator.save_custom_zh_name(mod.display_name, new_zh)
        name_translator.populate_zh_names(self.mods, self.translation_map, self.patch_map)
        self._run_search()
        self.refresh_view()

    def translate_missing_mods(self) -> None:
        """將目前尚未有中文譯名的英文模組透過線上翻譯轉為繁體中文並快取。"""
        if self._busy:
            return
        missing = [
            m for m in self.mods
            if m.has_extension and not m.zh_name and not name_translator.has_chinese(m.display_name)
        ]
        if not missing:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_TRANSLATE_NONE, parent=self)
            return
        self._busy = True

        def progress(cur: int, total: int, name: str) -> None:
            self.after(0, lambda c=cur, t=total, n=name: self.lbl_status.configure(
                text=i18n.MSG_TRANSLATING_MODS.format(cur=c, total=t, name=n)
            ))

        def worker() -> None:
            count = name_translator.translate_missing_mods_online(self.mods, progress_cb=progress)
            name_translator.populate_zh_names(self.mods, self.translation_map, self.patch_map)
            self.after(0, lambda: self._on_translate_done(count))

        threading.Thread(target=worker, daemon=True).start()

    def _on_translate_done(self, count: int) -> None:
        self._busy = False
        self._run_search()
        self.refresh_view()
        messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_TRANSLATE_DONE.format(n=count), parent=self)

    def unsubscribe_selected(self) -> None:
        """開啟工作坊頁面讓使用者在 Steam 上取消訂閱，並記錄到 unsubscribedMods。"""
        ids: list[str] = []
        for m in self.mod_list.selected():
            if m.source is Source.STEAM and m.id:
                ids.append(m.id)
                webbrowser.open(self.cfg.SteamPageUrl + m.id)
        if ids:
            with open(constants.BASE_DIR / "unsubscribedMods", "a", encoding="utf-8") as f:
                for mid in ids:
                    f.write(f"{mid}\n")
        else:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_NO_STEAM_ID, parent=self)

    @staticmethod
    def _preview_mods(targets: list[Mod], limit: int = 10) -> str:
        lines = [f"• {m.display_name}  ({m.folder})" for m in targets[:limit]]
        if len(targets) > limit:
            lines.append(f"…以及其他 {len(targets) - limit} 個模組")
        return "\n".join(lines)

    def remove_missing_mods(self) -> None:
        """移除資料夾不存在或缺少 .mod 檔案的無效模組。"""
        targets = loader.find_invalid_mods(self.mods)
        if not targets:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_NO_MISSING_MODS, parent=self)
            return
        msg = i18n.MSG_CONFIRM_REMOVE_MISSING.format(
            n=len(targets), preview=self._preview_mods(targets)
        )
        if not messagebox.askyesno(i18n.MSG_TITLE_CONFIRM, msg, parent=self):
            return
        self._execute_remove(targets)

    def remove_inactive_mods(self) -> None:
        """移除所有未勾選（未啟用）的模組與其資料夾。"""
        targets = [m for m in self.mods if not m.active]
        if not targets:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_NO_INACTIVE_MODS, parent=self)
            return
        msg = i18n.MSG_CONFIRM_REMOVE_INACTIVE.format(
            n=len(targets), preview=self._preview_mods(targets)
        )
        if not messagebox.askyesno(i18n.MSG_TITLE_CONFIRM, msg, parent=self):
            return
        self._execute_remove(targets)

    def _execute_remove(self, targets: list[Mod]) -> None:
        removed, errors = loader.remove_mods_and_folders(self.cfg, self.mods, targets)
        self._run_search()
        self.refresh_view()
        if errors:
            messagebox.showwarning(
                i18n.MSG_TITLE_ERROR,
                i18n.MSG_REMOVE_ERRORS.format(n=removed, e="\n".join(errors[:5])),
                parent=self,
            )
        else:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_REMOVE_DONE.format(n=removed), parent=self)

    # ------------------------------------------------------------ 按鈕動作
    def save_mod_list(self) -> None:
        try:
            loader.save_mods_cfg(self.cfg, self.mods)
        except FileNotFoundError:
            messagebox.showerror(i18n.MSG_NOT_SAVED, i18n.MSG_GAME_FOLDER_BAD, parent=self)
            return
        except OSError as exc:
            logging_util.write(constants.ERROR_FILE, "儲存 mods.cfg 失敗（權限不足或檔案被鎖定）。")
            logging_util.write_exception(constants.ERROR_FILE, exc)
            messagebox.showerror(
                i18n.MSG_NOT_SAVED,
                i18n.MSG_SAVE_PERMISSION_DENIED.format(err=exc),
                parent=self,
            )
            return
        self.dirty = False
        self.refresh_view()
        n = len(loader.active_file_names(self.mods))
        messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_SAVED.format(n=n), parent=self)

    def auto_order_mods(self) -> None:
        if not self.mods:
            return
        if not messagebox.askyesno(i18n.MSG_TITLE_CONFIRM, i18n.MSG_AUTO_ORDER_CONFIRM, parent=self):
            return
        self.mods = rules.order_mods(list(self.mods))
        loader.normalize_orders(self.mods)
        self._mark_dirty()
        messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_AUTO_ORDER_DONE, parent=self)

    def check_conflicts(self, silent: bool = False) -> None:
        if self._busy:
            return
        if sum(1 for m in self.mods if m.active) < 2:
            if not silent:
                messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_NEED_ACTIVE_FOR_CONFLICT, parent=self)
            return
        self._busy = True
        ignore_trans = self.var_ignore_translation.get()
        ignore_patch = self.var_ignore_patch.get()

        def progress(cur: int, total: int, name: str) -> None:
            self.after(0, lambda c=cur, t=total, n=name: self.lbl_status.configure(
                text=i18n.MSG_CHECKING_CONFLICTS.format(cur=c, total=t, name=n)
            ))

        def worker() -> None:
            t0 = time.perf_counter()
            self.translation_map = conflicts.detect_translation_map(self.mods)
            self.patch_map = conflicts.detect_patch_map(self.mods, self.translation_map)
            idx = conflicts.analyze_conflicts(
                self.mods,
                progress_cb=progress,
                ignore_translations=ignore_trans,
                ignore_patches=ignore_patch,
            )
            elapsed = time.perf_counter() - t0
            self.after(0, lambda: self._on_conflicts_done(idx, elapsed, ignore_trans, ignore_patch, silent))

        threading.Thread(target=worker, daemon=True).start()

    def _on_conflicts_done(
        self,
        idx: dict[str, conflicts.ConflictDetail],
        elapsed: float,
        ignore_trans: bool = True,
        ignore_patch: bool = True,
        silent: bool = False,
    ) -> None:
        self._busy = False
        self.conflict_index = idx
        self.refresh_view()
        if silent:
            return
        cmods = sum(1 for m in self.mods if m.conflicts)
        skipped_trans = (
            sum(1 for m in self.mods if m.active and m.file_name in self.translation_map)
            if ignore_trans else 0
        )
        skipped_patch = (
            sum(1 for m in self.mods if m.active and m.file_name in self.patch_map)
            if ignore_patch else 0
        )
        if idx:
            msg = (
                i18n.MSG_CONFLICTS_DONE_SKIPPED.format(
                    cmods=cmods,
                    citems=len(idx),
                    skipped_trans=skipped_trans,
                    skipped_patch=skipped_patch,
                    sec=elapsed,
                )
                if (skipped_trans > 0 or skipped_patch > 0)
                else i18n.MSG_CONFLICTS_DONE.format(cmods=cmods, citems=len(idx), sec=elapsed)
            )
            messagebox.showinfo(i18n.MSG_TITLE_INFO, msg, parent=self)
        else:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_CONFLICTS_NONE, parent=self)

    def update_rules_manual(self) -> None:
        ver = rules.get_latest_version(self.cfg)
        if not ver:
            messagebox.showwarning(i18n.MSG_TITLE_ERROR, i18n.MSG_RULES_FAILED, parent=self)
            return
        if ver != self.cfg.MasterlistVersion or not constants.MASTERLIST_FILE.exists():
            self.cfg.MasterlistVersion = ver
            if rules.update_master_file(self.cfg):
                self.cfg.save()
                messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_RULES_UPDATED.format(v=ver), parent=self)
            else:
                messagebox.showwarning(i18n.MSG_TITLE_ERROR, i18n.MSG_RULES_FAILED, parent=self)
        else:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.MSG_RULES_LATEST.format(v=ver), parent=self)

    def save_profile(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, initialfile="mod profile.cfg", defaultextension=".cfg",
            filetypes=[("設定檔 (*.cfg)", "*.cfg"), ("所有檔案", "*.*")],
        )
        if path:
            try:
                loader.write_profile(Path(path), self.mods)
            except OSError as exc:
                logging_util.write(constants.ERROR_FILE, f"儲存設定檔失敗：{path}")
                logging_util.write_exception(constants.ERROR_FILE, exc)
                messagebox.showerror(
                    i18n.MSG_NOT_SAVED,
                    i18n.MSG_SAVE_PERMISSION_DENIED.format(err=exc),
                    parent=self,
                )

    def load_profile(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, initialfile="mod profile.cfg",
            filetypes=[("設定檔 (*.cfg)", "*.cfg"), ("所有檔案", "*.*")],
        )
        if not path:
            return
        names = loader.read_profile(Path(path))
        hit = loader.apply_profile(self.mods, names)
        self._mark_dirty()
        messagebox.showinfo(i18n.MSG_TITLE_INFO,
                            i18n.MSG_PROFILE_LOADED.format(hit=hit, total=len(names)), parent=self)

    def open_game_folder(self) -> None:
        self._open_dir(self.cfg.GamePath, i18n.MSG_GAME_FOLDER_BAD)

    def open_game_mods_folder(self) -> None:
        self._open_dir(str(self.cfg.mod_folder), i18n.MSG_GAME_FOLDER_BAD)

    def open_steam_mods_folder(self) -> None:
        self._open_dir(self.cfg.SteamModsPath, i18n.MSG_STEAM_FOLDER_BAD)

    def _open_dir(self, path: str, err: str) -> None:
        if path and os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showerror(i18n.MSG_TITLE_ERROR, err, parent=self)

    def open_settings(self) -> None:
        SettingsWindow(self, self.cfg, on_saved=self._on_settings_saved)

    def _on_settings_saved(self) -> None:
        self.apply_language()
        self.reload_mods()

    def open_folder_tool(self) -> None:
        FolderToolWindow(self, self.cfg, on_changed=self.reload_mods)

    def open_about(self) -> None:
        AboutWindow(self)

    def launch_game(self) -> None:
        if self.cfg.uses_steam:
            os.startfile(f"steam://rungameid/{constants.KENSHI_APP_ID}")
            return
        exe = Path(self.cfg.GamePath) / "kenshi_x64.exe"
        if not exe.is_file():
            messagebox.showerror(i18n.MSG_TITLE_ERROR, i18n.MSG_GAME_NOT_FOUND, parent=self)
            return
        subprocess.Popen([str(exe)], cwd=self.cfg.GamePath)

    def start_fcs(self) -> None:
        exe = Path(self.cfg.GamePath) / "forgotten construction set.exe"
        if not exe.is_file():
            messagebox.showerror(i18n.MSG_TITLE_ERROR, i18n.MSG_FCS_NOT_FOUND, parent=self)
            return
        subprocess.Popen([str(exe)], cwd=self.cfg.GamePath)

    def _on_close(self) -> None:
        if self.dirty and not messagebox.askyesno(i18n.MSG_TITLE_CONFIRM, i18n.MSG_UNSAVED_EXIT, parent=self):
            return
        self.destroy()
