"""「關於」視窗：顯示改寫作者、原作者致謝、MIT License 完整授權條款與隨喜贊助收款 QR Code。"""
from __future__ import annotations

import webbrowser

import customtkinter as ctk
from PIL import Image

from kmm import constants

from . import i18n, theme


class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG)
        self.title(i18n.ABOUT_TITLE)
        self.geometry("920x620")
        self.minsize(780, 520)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # 頂部資訊卡片
        header = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(14, 8))
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

        # 左側：完整說明與 MIT 授權條款
        box = ctk.CTkTextbox(
            self,
            fg_color=theme.PANEL,
            text_color=theme.FG,
            font=theme.font(12),
            wrap="word",
            corner_radius=8,
            activate_scrollbars=True,
        )
        box.grid(row=1, column=0, sticky="nsew", padx=(14, 6), pady=6)
        box.insert("1.0", i18n.ABOUT_DESCRIPTION_TEXT)
        box.configure(state="disabled")

        # 右側：隨喜贊助支持卡片（TWQR / 街口支付 QR Code）
        self._build_donate_card()

        # 下方連結與關閉按鈕
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(6, 14))
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

    def _build_donate_card(self) -> None:
        card = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8, width=280)
        card.grid(row=1, column=1, sticky="ns", padx=(6, 14), pady=6)

        ctk.CTkLabel(
            card,
            text=i18n.ABOUT_DONATE_TITLE,
            font=theme.font(13, "bold"),
            text_color=theme.ACCENT,
        ).pack(padx=12, pady=(10, 4))

        if constants.DONATE_QR_FILE.is_file():
            try:
                pil_img = Image.open(constants.DONATE_QR_FILE)
                w, h = pil_img.size
                target_h = 260
                target_w = max(140, int(w * (target_h / h)))
                self._qr_ctk_img = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(target_w, target_h)
                )
                img_lbl = ctk.CTkLabel(card, text="", image=self._qr_ctk_img, cursor="hand2")
                img_lbl.pack(padx=12, pady=4)
                img_lbl.bind("<Button-1>", lambda _e: self._open_qr_zoom())
            except Exception:
                pass

        ctk.CTkLabel(
            card,
            text=i18n.ABOUT_DONATE_NOTE,
            font=theme.font(11),
            text_color=theme.FG_DIM,
            wraplength=256,
            justify="left",
        ).pack(padx=12, pady=(4, 6))

        if constants.DONATE_QR_FILE.is_file():
            ctk.CTkButton(
                card,
                text=i18n.ABOUT_DONATE_ZOOM,
                height=28,
                font=theme.font(11),
                fg_color="#2f333a",
                hover_color="#3c414a",
                command=self._open_qr_zoom,
            ).pack(fill="x", padx=12, pady=(2, 10))

    def _open_qr_zoom(self) -> None:
        """彈出高解析度放大版收款 QR Code 視窗，方便手機遠距離掃描。"""
        if not constants.DONATE_QR_FILE.is_file():
            return
        top = ctk.CTkToplevel(self, fg_color=theme.BG)
        top.title(i18n.ABOUT_DONATE_TITLE)
        top.geometry("500x740")
        top.transient(self)
        top.grab_set()

        pil_img = Image.open(constants.DONATE_QR_FILE)
        w, h = pil_img.size
        target_h = 580
        target_w = max(280, int(w * (target_h / h)))
        zoom_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
        top._zoom_img = zoom_img  # 防止被 GC 回收

        ctk.CTkLabel(top, text="", image=zoom_img).pack(padx=16, pady=(14, 8))
        ctk.CTkLabel(
            top,
            text=i18n.ABOUT_DONATE_NOTE,
            font=theme.font(12),
            text_color=theme.FG,
            wraplength=460,
            justify="center",
        ).pack(padx=16, pady=(0, 8))
        ctk.CTkButton(
            top,
            text=i18n.ABOUT_CLOSE,
            width=120,
            height=32,
            font=theme.font(12, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            command=top.destroy,
        ).pack(pady=(0, 12))
