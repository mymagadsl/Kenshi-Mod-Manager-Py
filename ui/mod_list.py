"""模組列表元件：ttk.Treeview + 勾選、拖曳排序、雙擊編輯順序、標題排序。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import customtkinter as ctk

from kmm.models import Mod

from . import i18n, theme

COLUMNS = ("active", "order", "name", "categories", "source")


def _headers() -> dict[str, str]:
    return {
        "active": i18n.COL_ACTIVE,
        "order": i18n.COL_ORDER,
        "name": i18n.COL_NAME,
        "categories": i18n.COL_CATEGORIES,
        "source": i18n.COL_SOURCE,
    }


CHECKED, UNCHECKED = "☑", "☐"


def _sort_key(col: str) -> Callable[[Mod], object]:
    return {
        "active": lambda m: (not m.active, m.order if m.active else 0, m.display_name.lower()),
        "order": lambda m: (not m.active, m.order if m.active else 0, m.display_name.lower()),
        "name": lambda m: m.display_name.lower(),
        "categories": lambda m: (m.display_categories.lower(), m.display_name.lower()),
        "source": lambda m: (m.source.value, m.display_name.lower()),
    }[col]


class ModListView(ctk.CTkFrame):
    def __init__(self, master, *,
                 on_select: Callable[[list[Mod]], None],
                 on_toggle: Callable[[list[Mod]], None],
                 on_reorder: Callable[[Mod, Mod], None],
                 on_order_edit: Callable[[Mod, str], None],
                 on_context: Callable[[tk.Event], None],
                 on_drag_blocked: Callable[[], None]):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=8)
        self.on_select, self.on_toggle = on_select, on_toggle
        self.on_reorder, self.on_order_edit = on_reorder, on_order_edit
        self.on_drag_blocked = on_drag_blocked

        self._mods: dict[str, Mod] = {}
        self.sort_col, self.sort_reverse = "order", False
        self._drag_src: str | None = None
        self._drag_started = False
        self._press_y = 0
        self._editor: tk.Entry | None = None

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings",
                                 selectmode="extended", style="KMM.Treeview")
        widths = {"active": 56, "order": 64, "name": 420, "categories": 200, "source": 100}
        headers = _headers()
        for col in COLUMNS:
            self.tree.heading(col, text=headers[col], command=lambda c=col: self.sort_by(c))
            anchor = "center" if col in ("active", "order", "source") else "w"
            self.tree.column(col, width=widths[col], anchor=anchor,
                             stretch=col in ("name", "categories"), minwidth=40)

        self.tree.tag_configure("odd", background=theme.ROW_ALT)
        self.tree.tag_configure("inactive", foreground=theme.FG_DIM)
        self.tree.tag_configure("error", foreground=theme.FG_ERROR)
        self.tree.tag_configure("conflict", background=theme.ROW_CONFLICT)
        self.tree.tag_configure("missing", background=theme.ROW_MISSING)
        self.tree.tag_configure("search", background=theme.ROW_SEARCH)
        self.tree.tag_configure("drop", background=theme.ACCENT)

        sb = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        sb.grid(row=0, column=1, sticky="ns", padx=(2, 4), pady=6)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_select(self.selected()))
        self.tree.bind("<ButtonPress-1>", self._on_press)
        self.tree.bind("<B1-Motion>", self._on_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_release)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Button-3>", on_context)
        self.tree.bind("<space>", lambda e: (self.on_toggle(self.selected()), "break")[1])

        self._update_headings()

    # ------------------------------------------------------------ 資料
    def set_items(
        self,
        mods: list[Mod],
        *,
        search: set[str],
        missing: set[str],
        show_zh: bool = True,
    ) -> None:
        sel = set(self.tree.selection())
        yview = self.tree.yview()
        self.tree.delete(*self.tree.get_children())
        self._mods = {m.uid: m for m in mods}
        ordered = sorted(mods, key=_sort_key(self.sort_col), reverse=self.sort_reverse)
        for i, m in enumerate(ordered):
            tags = ["odd"] if i % 2 else []
            if not m.active:
                tags.append("inactive")
            if not m.has_extension:
                tags.append("error")
            if m.conflicts:
                tags.append("conflict")
            if m.uid in missing:
                tags.append("missing")
            if m.uid in search:
                tags.append("search")
            base_name = m.ui_name(show_zh)
            name_label = f"{base_name}  [⚠ {len(m.conflicts)}]" if m.conflicts else base_name
            self.tree.insert("", "end", iid=m.uid, tags=tags, values=(
                CHECKED if m.active else UNCHECKED,
                m.order if m.active else "",
                name_label, m.display_categories, i18n.source_label(m.source)))
        keep = [i for i in sel if i in self._mods]
        if keep:
            self.tree.selection_set(keep)
        self.tree.yview_moveto(yview[0])

    def selected(self) -> list[Mod]:
        return [self._mods[i] for i in self.tree.selection() if i in self._mods]

    def visible_order(self) -> list[Mod]:
        return [self._mods[i] for i in self.tree.get_children()]

    def see(self, mod: Mod, select: bool = False) -> None:
        if self.tree.exists(mod.uid):
            self.tree.see(mod.uid)
            if select:
                self.tree.selection_set(mod.uid)
                self.tree.focus(mod.uid)

    # ------------------------------------------------------------ 排序
    def sort_by(self, col: str) -> None:
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col, self.sort_reverse = col, False
        self._update_headings()
        self.event_generate("<<ResortRequested>>")

    def _update_headings(self) -> None:
        headers = _headers()
        for col in COLUMNS:
            arrow = ""
            if col == self.sort_col:
                arrow = " ▼" if self.sort_reverse else " ▲"
            self.tree.heading(col, text=headers[col] + arrow)

    @property
    def drag_enabled(self) -> bool:
        return self.sort_col in ("order", "active") and not self.sort_reverse

    # ------------------------------------------------------------ 滑鼠
    def _on_press(self, e: tk.Event):
        self._close_editor()
        region = self.tree.identify_region(e.x, e.y)
        row = self.tree.identify_row(e.y)
        self._drag_src, self._drag_started, self._press_y = None, False, e.y
        if region != "cell" or not row:
            return None
        if self.tree.identify_column(e.x) == "#1":
            # 點擊「啟用」欄：若點的是已選取的多列之一則全部切換，否則只切換該列
            targets = self.selected() if row in self.tree.selection() else [self._mods[row]]
            self.on_toggle(targets)
            return "break"
        self._drag_src = row
        return None

    def _on_motion(self, e: tk.Event):
        if not self._drag_src:
            return
        if not self._drag_started and abs(e.y - self._press_y) < 6:
            return
        if not self._drag_started:
            if not self.drag_enabled:
                self._drag_src = None
                self.on_drag_blocked()
                return
            self._drag_started = True
            self.tree.configure(cursor="sb_v_double_arrow")
        for iid in self.tree.tag_has("drop"):
            self.tree.item(iid, tags=[t for t in self.tree.item(iid, "tags") if t != "drop"])
        target = self.tree.identify_row(e.y)
        if target and target != self._drag_src:
            self.tree.item(target, tags=(*self.tree.item(target, "tags"), "drop"))
        # 拖到邊緣自動捲動
        h = self.tree.winfo_height()
        if e.y < 20:
            self.tree.yview_scroll(-1, "units")
        elif e.y > h - 20:
            self.tree.yview_scroll(1, "units")

    def _on_release(self, e: tk.Event):
        src, started = self._drag_src, self._drag_started
        self._drag_src, self._drag_started = None, False
        self.tree.configure(cursor="")
        if not started or not src:
            return
        for iid in self.tree.tag_has("drop"):
            self.tree.item(iid, tags=[t for t in self.tree.item(iid, "tags") if t != "drop"])
        target = self.tree.identify_row(e.y)
        if target and target != src:
            self.on_reorder(self._mods[src], self._mods[target])

    def _on_double(self, e: tk.Event):
        row = self.tree.identify_row(e.y)
        if not row or self.tree.identify_column(e.x) != "#2":
            return
        bbox = self.tree.bbox(row, "#2")
        if not bbox:
            return
        x, y, w, h = bbox
        mod = self._mods[row]
        ent = tk.Entry(self.tree, justify="center", bg=theme.BG, fg=theme.FG,
                       insertbackground=theme.FG, relief="flat", font=(theme.FONT_FAMILY, 11))
        ent.insert(0, str(mod.order if mod.active else ""))
        ent.select_range(0, "end")
        ent.place(x=x, y=y, width=w, height=h)
        ent.focus_set()
        self._editor = ent

        def commit(_e=None):
            value = ent.get().strip()
            self._close_editor()
            if value:
                self.on_order_edit(mod, value)

        ent.bind("<Return>", commit)
        ent.bind("<KP_Enter>", commit)
        ent.bind("<Escape>", lambda _e: self._close_editor())
        ent.bind("<FocusOut>", lambda _e: self._close_editor())

    def _close_editor(self) -> None:
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None
