"""主題、字型與 ttk.Treeview 深色樣式。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

FONT_FAMILY = "Microsoft JhengHei UI"
MONO_FAMILY = "Consolas"

BG = "#1b1d21"
PANEL = "#23262b"
ROW_ALT = "#272a30"
FG = "#e6e6e6"
FG_DIM = "#8b9099"
ACCENT = "#d0873a"        # Kenshi 沙漠橘
ACCENT_HOVER = "#b5712b"
SELECT = "#3b5b7a"

ROW_SEARCH = "#6e4a1c"
ROW_MISSING = "#6a2424"
ROW_CONFLICT = "#4a2559"
ROW_UPDATED_TODAY = "#1c4a2e"
FG_UPDATED_TODAY = "#50fa7b"
ROW_UPDATED_WEEK = "#193c4d"
FG_UPDATED_WEEK = "#8be9fd"
FG_ERROR = "#7d828a"
LINK = "#6fb3ff"
OK = "#5cc26b"
BAD = "#ff6b6b"
WARN = "#f0b44c"


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def setup() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


def style_treeview(root: tk.Misc) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("KMM.Treeview",
                    background=PANEL, fieldbackground=PANEL, foreground=FG,
                    rowheight=28, borderwidth=0, font=(FONT_FAMILY, 11))
    style.map("KMM.Treeview",
              background=[("selected", SELECT)], foreground=[("selected", "#ffffff")])
    style.configure("KMM.Treeview.Heading",
                    background=BG, foreground=FG, relief="flat",
                    font=(FONT_FAMILY, 11, "bold"), padding=(6, 6))
    style.map("KMM.Treeview.Heading", background=[("active", "#2e3238")])
    style.layout("KMM.Treeview", [("KMM.Treeview.treearea", {"sticky": "nswe"})])
    style.configure("KMM.Vertical.TScrollbar", background=PANEL, troughcolor=BG,
                    bordercolor=BG, arrowcolor=FG, relief="flat")


def style_menu(menu: tk.Menu) -> None:
    menu.configure(bg=PANEL, fg=FG, activebackground=SELECT, activeforeground="#ffffff",
                   bd=0, relief="flat", font=(FONT_FAMILY, 11), tearoff=0)
