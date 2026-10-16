"""詳細資訊面板（對應 C# ListView_SelectionChanged 的 RichTextBox）。"""
from __future__ import annotations

import os
import webbrowser
from typing import Callable

import customtkinter as ctk

from kmm.conflicts import ConflictDetail
from kmm.models import Mod, Source

from . import i18n, theme

_MAX_SHOWN_CONFLICTS = 150


class DetailPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        dep_ok: Callable[[Mod, str], bool],
        url_of: Callable[[Mod], str],
        conflict_of: Callable[[str], ConflictDetail | None] | None = None,
        translation_of: Callable[[Mod], list[str] | None] | None = None,
        patch_of: Callable[[Mod], list[str] | None] | None = None,
        account_label_of: Callable[[str], str] | None = None,
        on_mod_click: Callable[[str], None] | None = None,
    ):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=8)
        self.dep_ok, self.url_of = dep_ok, url_of
        self.conflict_of = conflict_of or (lambda _k: None)
        self.translation_of = translation_of or (lambda _m: None)
        self.patch_of = patch_of or (lambda _m: None)
        self.account_label_of = account_label_of
        self.on_mod_click = on_mod_click
        self.box = ctk.CTkTextbox(self, fg_color=theme.PANEL, text_color=theme.FG,
                                  font=theme.font(12), wrap="word", activate_scrollbars=True)
        self.box.pack(fill="both", expand=True, padx=6, pady=6)
        t = self.box._textbox  # CTkTextbox 不允許 tag 設定字型，直接使用底層 tk.Text
        t.tag_configure("title", font=(theme.FONT_FAMILY, 11, "bold"), foreground=theme.ACCENT)
        t.tag_configure("name", font=(theme.FONT_FAMILY, 14, "bold"), foreground="#ffffff")
        t.tag_configure("ok", foreground=theme.OK)
        t.tag_configure("bad", foreground=theme.BAD)
        t.tag_configure("warn", font=(theme.FONT_FAMILY, 11, "bold"), foreground=theme.WARN)
        t.tag_configure("today", font=(theme.FONT_FAMILY, 11, "bold"), foreground=theme.FG_UPDATED_TODAY)
        t.tag_configure("week", font=(theme.FONT_FAMILY, 11, "bold"), foreground=theme.FG_UPDATED_WEEK)
        t.tag_configure("dim", foreground=theme.FG_DIM)
        t.tag_configure("link", foreground=theme.LINK, underline=True)
        t.tag_configure("mod_link_ok", foreground=theme.OK, underline=True)
        t.tag_configure("mod_link_dim", foreground=theme.LINK, underline=True)
        for hover_tag in ("link", "mod_link_ok", "mod_link_dim"):
            t.tag_bind(hover_tag, "<Enter>", lambda e: t.configure(cursor="hand2"))
            t.tag_bind(hover_tag, "<Leave>", lambda e: t.configure(cursor=""))
        self._link_n = 0
        self.show(None)

    def _write(self, text: str, *tags: str) -> None:
        self.box._textbox.insert("end", text, tags)

    def _link(self, text: str, target: str) -> None:
        self._link_n += 1
        tag = f"link{self._link_n}"
        t = self.box._textbox
        t.insert("end", text, ("link", tag))
        t.tag_bind(tag, "<Button-1>", lambda e, u=target: _open(u))

    def _mod_link(self, mod_name: str, is_win: bool) -> None:
        if self.on_mod_click is None:
            self._write(mod_name, "ok" if is_win else "dim")
            return
        self._link_n += 1
        tag = f"mlink{self._link_n}"
        style_tag = "mod_link_ok" if is_win else "mod_link_dim"
        t = self.box._textbox
        t.insert("end", mod_name, (style_tag, tag))
        t.tag_bind(tag, "<Button-1>", lambda e, m=mod_name: self.on_mod_click(m))

    def _field(self, title: str, value: str) -> None:
        self._write(title, "title")
        self._write(f" {value}\n")

    def show(self, mod: Mod | None) -> None:
        self.box.configure(state="normal")
        self.box._textbox.delete("1.0", "end")
        self._link_n = 0
        if mod is None:
            self._write(i18n.D_EMPTY, "dim")
            self.box.configure(state="disabled")
            return

        self._write(mod.ui_name(True) + "\n", "name")
        if mod.zh_name:
            self._field(i18n.D_ZH_NAME, mod.zh_name)
        if mod.title and mod.title.lower() != mod.display_name.lower():
            self._field(i18n.D_WORKSHOP_TITLE, mod.title)
        trans_targets = self.translation_of(mod)
        if trans_targets is not None:
            self._write(i18n.D_TRANSLATION, "title")
            self._write(" ")
            label = (
                i18n.D_TRANSLATION_TARGET.format(targets="、".join(trans_targets))
                if trans_targets
                else i18n.D_TRANSLATION_GLOBAL
            )
            self._write(label + "\n", "ok")
        patch_targets = self.patch_of(mod)
        if patch_targets:
            self._write(i18n.D_PATCH, "title")
            self._write(" ")
            self._write(i18n.D_PATCH_TARGET.format(targets="、".join(patch_targets)) + "\n", "ok")
        for title, items in ((i18n.D_DEPENDENCIES, mod.dependencies), (i18n.D_REFERENCES, mod.references)):
            if not items:
                continue
            self._write(title, "title")
            self._write(" ")
            for i, dep in enumerate(items):
                tag = ("ok" if self.dep_ok(mod, dep) else "bad") if mod.active else ""
                self._write(dep, tag)
                if i < len(items) - 1:
                    self._write("，")
            self._write("\n")
        if mod.active and (mod.dependencies or mod.references):
            self._write(i18n.D_LEGEND + "\n", "dim")

        if mod.updated_at:
            status = mod.update_status()
            self._write(i18n.D_UPDATED, "title")
            self._write(f" {mod.updated_display}")
            if status == "today":
                self._write(f"  {i18n.UPDATE_TODAY}", "today")
            elif status == "week":
                self._write(f"  {i18n.UPDATE_WEEK}", "week")
            self._write("\n")
        else:
            self._field(i18n.D_UPDATED, "—")

        self._field(i18n.D_AUTHOR, mod.author or "—")
        self._field(i18n.D_VERSION, mod.version or "—")
        if mod.id:
            self._field(i18n.D_STEAM_ID, mod.id)

        self._write(i18n.D_SUBSCRIBED_BY, "title")
        self._write(" ")
        if mod.source is Source.STEAM:
            if mod.subscribed_by:
                for idx, uid in enumerate(mod.subscribed_by):
                    badge, tag = (
                        self.account_label_of(uid)
                        if self.account_label_of
                        else (uid, "ok")
                    )
                    self._write(badge, tag)
                    if idx < len(mod.subscribed_by) - 1:
                        self._write("、")
                self._write("\n")
            else:
                self._write(i18n.D_SUBSCRIBED_LOCAL + "\n", "dim")
        else:
            self._write(i18n.D_SUBSCRIBED_LOCAL + "\n", "dim")

        self._write(i18n.D_PATH, "title")
        self._write(" ")
        self._link(mod.file_path, mod.folder)
        self._write("\n")
        url = self.url_of(mod)
        self._write(i18n.D_URL, "title")
        self._write(" ")
        self._link(url, url)
        self._write("\n")
        self._write(i18n.D_DESCRIPTION, "title")
        self._write("\n" + (mod.description or "—") + "\n")

        if mod.conflicts:
            self._render_conflicts(mod)

        self.box.configure(state="disabled")

    def _render_conflicts(self, mod: Mod) -> None:
        total = len(mod.conflicts)
        self._write("\n" + i18n.D_CONFLICTS_HEADER.format(n=total) + "\n", "warn")
        self._write(i18n.D_CONFLICTS_HINT + "\n", "dim")

        shown = mod.conflicts[:_MAX_SHOWN_CONFLICTS]
        for key in shown:
            d = self.conflict_of(key)
            if d is None:
                continue
            self._write(f"\n▸ [{d.item_type}] {d.item_name}  —  ", "title")
            self._write(f"{d.property_key}\n", "warn")
            win_idx = d.winning_index
            for idx, ch in enumerate(d.changes):
                is_win = idx == win_idx and ch.state != "REMOVED"
                val_text = "" if ch.state == "REMOVED" else f" = {ch.value}"
                prefix = f"    [{ch.state}]{val_text}   —  "
                self._write(prefix, "ok" if is_win else "dim")
                self._mod_link(ch.mod_name, is_win)
                if is_win:
                    self._write(i18n.D_CONFLICTS_WINNER, "ok")
                self._write("\n")

        if total > _MAX_SHOWN_CONFLICTS:
            self._write(
                "\n" + i18n.D_CONFLICTS_MORE.format(
                    more=total - _MAX_SHOWN_CONFLICTS, shown=_MAX_SHOWN_CONFLICTS
                ) + "\n",
                "warn",
            )


def _open(target: str) -> None:
    if os.path.isdir(target):
        os.startfile(target)
    else:
        webbrowser.open(target)
