"""當機與 Log 診斷分析視窗。"""
from __future__ import annotations

import os
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from kmm import log_analyzer
from kmm.config import KenshiToolConfig
from kmm.models import Mod

from . import i18n, theme


class LogAnalyzerWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        cfg: KenshiToolConfig,
        mods: list[Mod],
        on_select_mod: Callable[[Mod], None] | None = None,
    ):
        super().__init__(master, fg_color=theme.BG)
        self.cfg = cfg
        self.mods = mods
        self.on_select_mod = on_select_mod
        self.report: log_analyzer.CrashAnalysisReport | None = None
        self.report_text: str = ""

        self.title(i18n.LA_TITLE)
        self.geometry("960x740")
        self.minsize(760, 560)
        self.transient(master)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Row 0: 頂部工具與狀態列
        top = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.grid_columnconfigure(0, weight=1)

        self.lbl_summary = ctk.CTkLabel(
            top,
            text=i18n.LA_ANALYZING,
            font=theme.font(13, "bold"),
            text_color=theme.FG,
            anchor="w",
            justify="left",
        )
        self.lbl_summary.grid(row=0, column=0, sticky="ew", padx=12, pady=10)

        btn_box = ctk.CTkFrame(top, fg_color="transparent")
        btn_box.grid(row=0, column=1, padx=8, pady=6)

        ctk.CTkButton(
            btn_box,
            text=i18n.LA_BTN_REANALYZE,
            width=105,
            height=32,
            font=theme.font(12),
            fg_color="#2f333a",
            hover_color="#3b4048",
            command=self.run_analysis,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text=i18n.LA_BTN_COPY,
            width=120,
            height=32,
            font=theme.font(12, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            command=self._copy_report,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text=i18n.LA_BTN_OPEN_DIR,
            width=115,
            height=32,
            font=theme.font(12),
            fg_color="#2f333a",
            hover_color="#3b4048",
            command=self._open_game_dir,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text=i18n.LA_BTN_CLEAN_LOGS,
            width=125,
            height=32,
            font=theme.font(12, "bold"),
            fg_color="#5a1e23",
            hover_color="#78282f",
            command=self._clean_logs,
        ).pack(side="left", padx=4)

        # Row 1: 可疑模組快速定位區
        suspect_frame = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        suspect_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        suspect_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            suspect_frame,
            text=i18n.LA_SUSPECTS_HINT,
            font=theme.font(12, "bold"),
            text_color=theme.ACCENT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

        self.suspect_scroll = ctk.CTkScrollableFrame(
            suspect_frame,
            height=135,
            fg_color=theme.BG,
            corner_radius=6,
        )
        self.suspect_scroll.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.suspect_scroll.grid_columnconfigure(0, weight=1)

        # Row 2: 完整診斷報告文字區
        body = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        body.grid(row=2, column=0, sticky="nsew", padx=12, pady=(6, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(
            body,
            font=theme.font(12),
            fg_color="#141619",
            text_color=theme.FG,
            wrap="word",
            corner_radius=6,
        )
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        tb = self.textbox._textbox
        tb.tag_configure("header", foreground="#58a6ff", font=theme.font(13, "bold"))
        tb.tag_configure("high", foreground="#ff7b72", font=theme.font(12, "bold"))
        tb.tag_configure("medium", foreground="#ffa657", font=theme.font(12, "bold"))
        tb.tag_configure("accent", foreground="#79c0ff")
        tb.tag_configure("dim", foreground=theme.FG_DIM)

        self.after(60, self.run_analysis)

    def run_analysis(self) -> None:
        self.lbl_summary.configure(text=i18n.LA_ANALYZING, text_color=theme.FG)
        self.update_idletasks()

        self.report = log_analyzer.analyze_logs(self.cfg.GamePath, self.mods)
        self.report_text = log_analyzer.format_report_text(self.report)

        if self.report.crash_detected:
            self.lbl_summary.configure(text=f"🔴 {self.report.crash_summary}", text_color="#ff7b72")
        else:
            self.lbl_summary.configure(text=f"🟢 {self.report.crash_summary}", text_color="#7ee787")

        self._populate_suspects()
        self._populate_report_text()

    def _populate_suspects(self) -> None:
        for child in self.suspect_scroll.winfo_children():
            child.destroy()

        if not self.report or not self.report.suspects:
            ctk.CTkLabel(
                self.suspect_scroll,
                text=i18n.LA_NO_SUSPECTS,
                font=theme.font(12),
                text_color=theme.FG_DIM,
            ).grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        color_map = {
            "HIGH": ("#5a1e23", "#78282f", "🔴"),
            "MEDIUM": ("#4d3319", "#664422", "🟠"),
            "LOW": ("#282c34", "#353b45", "🟡"),
        }

        for idx, s in enumerate(self.report.suspects):
            fg, hover, icon = color_map.get(s.level, color_map["LOW"])
            dll_part = f" ({s.dll_name})" if s.dll_name else ""
            first_reason = s.reasons[0] if s.reasons else ""
            if len(first_reason) > 72:
                first_reason = first_reason[:72] + "…"
            label = f"{idx + 1}. {icon} [{s.score}分] {s.name}{dll_part}  —  {first_reason}"

            btn = ctk.CTkButton(
                self.suspect_scroll,
                text=label,
                anchor="w",
                height=30,
                font=theme.font(12),
                fg_color=fg,
                hover_color=hover,
                command=lambda m=s.mod, n=s.name: self._on_click_suspect(m, n),
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=4, pady=2)

    def _on_click_suspect(self, mod: Mod | None, name: str) -> None:
        if mod and self.on_select_mod:
            self.on_select_mod(mod)
            self.lbl_summary.configure(
                text=i18n.LA_JUMPED_TO_MOD.format(name=mod.display_name),
                text_color=theme.ACCENT,
            )
        else:
            self.lbl_summary.configure(
                text=i18n.LA_MOD_NOT_IN_LIST.format(name=name),
                text_color=theme.FG_DIM,
            )

    def _populate_report_text(self) -> None:
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        tb = self.textbox._textbox

        for line in self.report_text.splitlines():
            tag = None
            if line.startswith(("═", "─", "🎯", "🛠", "💥", "🔌", "📋")) or "診斷報告" in line:
                tag = "header"
            elif "🔴" in line or "異常代碼：0x" in line or "故障位址：" in line or "Crash detected" in line:
                tag = "high"
            elif "🟠" in line or "👉" in line or "【" in line:
                tag = "medium"
            elif line.startswith(("分析時間：", "遊戲路徑：")):
                tag = "dim"

            if tag:
                tb.insert("end", line + "\n", tag)
            else:
                tb.insert("end", line + "\n")

        self.textbox.configure(state="disabled")

    def _copy_report(self) -> None:
        if not self.report_text:
            return
        self.clipboard_clear()
        self.clipboard_append(self.report_text)
        self.lbl_summary.configure(text=i18n.LA_COPIED, text_color="#7ee787")

    def _open_game_dir(self) -> None:
        if self.cfg.GamePath and os.path.isdir(self.cfg.GamePath):
            os.startfile(self.cfg.GamePath)

    def _clean_logs(self) -> None:
        paths = log_analyzer.scan_game_logs(self.cfg.GamePath)
        if not paths:
            messagebox.showinfo(i18n.MSG_TITLE_INFO, i18n.LA_CLEAN_NONE, parent=self)
            return

        from pathlib import Path
        root = Path(self.cfg.GamePath)
        sized_items: list[tuple[Path, int]] = []
        for p in paths:
            try:
                sz = p.stat().st_size
            except OSError:
                sz = 0
            sized_items.append((p, sz))
        sized_items.sort(key=lambda x: x[1], reverse=True)

        total_bytes = sum(sz for _, sz in sized_items)
        size_str = log_analyzer.format_bytes(total_bytes)

        preview_lines = []
        for p, sz in sized_items[:10]:
            try:
                rel = p.relative_to(root)
            except ValueError:
                rel = p.name
            preview_lines.append(f"  • {rel}  ({log_analyzer.format_bytes(sz)})")
        if len(sized_items) > 10:
            preview_lines.append(f"  …以及其他 {len(sized_items) - 10} 個檔案")

        msg = i18n.LA_CLEAN_CONFIRM.format(
            n=len(sized_items),
            size=size_str,
            preview="\n".join(preview_lines),
        )
        if not messagebox.askyesno(i18n.MSG_TITLE_CONFIRM, msg, parent=self):
            return

        removed, freed_bytes, errors = log_analyzer.clean_game_logs(self.cfg.GamePath)
        freed_str = log_analyzer.format_bytes(freed_bytes)

        if errors:
            messagebox.showwarning(
                i18n.MSG_TITLE_INFO,
                i18n.LA_CLEAN_ERRORS.format(
                    n=removed,
                    size=freed_str,
                    e="\n".join(errors[:8]),
                ),
                parent=self,
            )
        else:
            messagebox.showinfo(
                i18n.MSG_TITLE_INFO,
                i18n.LA_CLEAN_DONE.format(n=removed, size=freed_str),
                parent=self,
            )

        self.run_analysis()
        self.lbl_summary.configure(
            text=i18n.LA_CLEAN_DONE.format(n=removed, size=freed_str),
            text_color="#7ee787",
        )

