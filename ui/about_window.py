"""「關於」視窗：顯示改寫作者、原作者致謝與 MIT License 完整授權條款。"""
from __future__ import annotations

import webbrowser

import customtkinter as ctk

from kmm import constants

from . import i18n, theme


class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG)
        self.title(i18n.ABOUT_TITLE)
        self.geometry("660x560")
        self.minsize(560, 460)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 頂部資訊卡片
        header = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=f"{i18n.ABOUT_HEADING}  v{constants.APP_VERSION}",
            font=theme.font(16, "bold"),
            text_color="#ffffff",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            header,
            text=i18n.ABOUT_REWRITE_AUTHOR,
            font=theme.font(13, "bold"),
            text_color=theme.ACCENT,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=2)

        ctk.CTkLabel(
            header,
            text=i18n.ABOUT_ORIGINAL_AUTHOR,
            font=theme.font(12),
            text_color=theme.OK,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 12))

        # 中央完整說明與 MIT 授權條款
        box = ctk.CTkTextbox(
            self,
            fg_color=theme.PANEL,
            text_color=theme.FG,
            font=theme.font(12),
            wrap="word",
            corner_radius=8,
            activate_scrollbars=True,
        )
        box.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)
        box.insert("1.0", i18n.ABOUT_DESCRIPTION_TEXT)
        box.configure(state="disabled")

        # 下方連結與關閉按鈕
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 14))
        for col, (text, cmd, accent) in enumerate((
            (i18n.ABOUT_OPEN_ORIG_REPO, lambda: webbrowser.open(i18n.ABOUT_ORIGINAL_REPO_URL), False),
            (i18n.ABOUT_OPEN_SORT_GUIDE, lambda: webbrowser.open(i18n.ABOUT_SORT_GUIDE_URL), False),
            (i18n.ABOUT_CLOSE, self.destroy, True),
        )):
            btn_bar.grid_columnconfigure(col, weight=1)
            ctk.CTkButton(
                btn_bar,
                text=text,
                height=34,
                font=theme.font(12, "bold" if accent else "normal"),
                fg_color=theme.ACCENT if accent else theme.PANEL,
                hover_color=theme.ACCENT_HOVER if accent else "#2f333a",
                command=cmd,
            ).grid(row=0, column=col, sticky="ew", padx=4)
