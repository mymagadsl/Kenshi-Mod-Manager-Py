"""Kenshi 模組管理器 — 專用視窗化編譯工具（Python + CustomTkinter 繁體中文版）。

用途：
  將 KenshiModManager-Py 專案一鍵封裝為 Windows 獨立執行檔（.exe），
  自動打包 CustomTkinter 主題資源、base_rules.json 與 base_mod_names_zh.json。
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from kmm import constants
from ui import theme

PROJECT_DIR = Path(__file__).resolve().parent
ENTRY_SCRIPT = PROJECT_DIR / "main.py"
DEFAULT_EXE_NAME = "KenshiModManager"
DEFAULT_DIST_DIR = PROJECT_DIR / "dist"
DEFAULT_BUILD_DIR = PROJECT_DIR / "build"


def has_pyinstaller() -> bool:
    """檢查目前 Python 環境是否已安裝 PyInstaller。"""
    return importlib.util.find_spec("PyInstaller") is not None


def get_pyinstaller_version() -> str:
    """取得已安裝的 PyInstaller 版本字串；未安裝則回傳空字串。"""
    if not has_pyinstaller():
        return ""
    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "PyInstaller", "--version"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.strip()
    except Exception:
        return "已安裝"


def build_pyinstaller_args(
    *,
    exe_name: str = DEFAULT_EXE_NAME,
    dist_dir: Path = DEFAULT_DIST_DIR,
    work_dir: Path = DEFAULT_BUILD_DIR,
    onefile: bool = True,
    noconsole: bool = True,
    clean: bool = True,
    icon_path: str = "",
    python_exe: str | None = None,
) -> list[str]:
    """組裝 PyInstaller 命令列參數清單（方便單元測試與執行期呼叫）。"""
    py = python_exe or sys.executable
    sep = ";" if os.name == "nt" else ":"

    cmd = [
        py,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        exe_name.strip() or DEFAULT_EXE_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(PROJECT_DIR),
    ]
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    if noconsole:
        cmd.append("--noconsole")

    if clean:
        cmd.append("--clean")

    if icon_path and Path(icon_path).is_file():
        cmd.extend(["--icon", str(Path(icon_path).resolve())])

    # 自動收集 CustomTkinter 資源與專案內建 JSON / QR Code 資料檔
    cmd.extend(["--collect-all", "customtkinter"])
    for res_name in ("base_rules.json", "base_mod_names_zh.json", "donate_qr.png"):
        res_file = PROJECT_DIR / "kmm" / res_name
        if res_file.is_file():
            cmd.extend(["--add-data", f"{res_file}{sep}kmm"])

    cmd.append(str(ENTRY_SCRIPT))
    return cmd


class CompilerApp(ctk.CTk):
    """Kenshi 模組管理器 — 繁體中文視窗化編譯工具。"""

    def __init__(self) -> None:
        theme.setup()
        super().__init__(fg_color=theme.BG)

        self.title(f"Kenshi 模組管理器 — 獨立執行檔編譯工具 (v{constants.APP_VERSION})")
        self.geometry("780x680")
        self.minsize(700, 600)
        self._busy = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_options()
        self._build_progress_and_log()
        self._build_bottom_buttons()
        self._refresh_env_status()

    # ------------------------------------------------------------ 介面區塊
    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text=f"🛠 Kenshi 模組管理器 — 獨立執行檔編譯工具  [v{constants.APP_VERSION}]",
            font=theme.font(16, "bold"),
            text_color="#ffffff",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))

        self.lbl_env = ctk.CTkLabel(
            hdr,
            text="正在檢查 Python 與 PyInstaller 環境…",
            font=theme.font(12),
            text_color=theme.FG_DIM,
            anchor="w",
        )
        self.lbl_env.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.btn_install_pyi = ctk.CTkButton(
            hdr,
            text="📦 安裝 / 更新 PyInstaller",
            width=180,
            height=32,
            font=theme.font(12),
            fg_color="#2f333a",
            hover_color="#3c414a",
            command=self.install_pyinstaller,
        )
        self.btn_install_pyi.grid(row=0, column=1, rowspan=2, padx=14, pady=10)

    def _build_options(self) -> None:
        opt = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        opt.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        opt.grid_columnconfigure(1, weight=1)

        # Row 0: 輸出檔名
        ctk.CTkLabel(opt, text="輸出執行檔名稱：", font=theme.font(12)).grid(
            row=0, column=0, sticky="w", padx=(14, 8), pady=(12, 6)
        )
        self.ent_name = ctk.CTkEntry(opt, font=theme.font(12), height=30)
        self.ent_name.insert(0, DEFAULT_EXE_NAME)
        self.ent_name.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=(12, 6))

        # Row 1: 輸出目錄
        ctk.CTkLabel(opt, text="輸出資料夾路徑：", font=theme.font(12)).grid(
            row=1, column=0, sticky="w", padx=(14, 8), pady=6
        )
        self.ent_dist = ctk.CTkEntry(opt, font=theme.font(12), height=30)
        self.ent_dist.insert(0, str(DEFAULT_DIST_DIR))
        self.ent_dist.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=6)
        ctk.CTkButton(
            opt, text="瀏覽…", width=80, height=30, font=theme.font(12),
            command=self._browse_dist,
        ).grid(row=1, column=2, padx=(0, 14), pady=6)

        # Row 2: 圖示檔案 (.ico)
        ctk.CTkLabel(opt, text="自訂圖示 (.ico)：", font=theme.font(12)).grid(
            row=2, column=0, sticky="w", padx=(14, 8), pady=6
        )
        self.ent_icon = ctk.CTkEntry(
            opt, placeholder_text="選填：留空則使用預設圖示", font=theme.font(12), height=30
        )
        self.ent_icon.grid(row=2, column=1, sticky="ew", padx=(0, 6), pady=6)
        ctk.CTkButton(
            opt, text="選擇…", width=80, height=30, font=theme.font(12),
            command=self._browse_icon,
        ).grid(row=2, column=2, padx=(0, 14), pady=6)

        # Row 3: 封裝模式
        ctk.CTkLabel(opt, text="封裝模式：", font=theme.font(12)).grid(
            row=3, column=0, sticky="w", padx=(14, 8), pady=6
        )
        mode_frame = ctk.CTkFrame(opt, fg_color="transparent")
        mode_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=6)
        self.var_mode = ctk.StringVar(value="onefile")
        ctk.CTkRadioButton(
            mode_frame,
            text="單一獨立執行檔 (--onefile，推薦：所有檔案封裝成單一 .exe)",
            variable=self.var_mode,
            value="onefile",
            font=theme.font(12),
        ).pack(side="left", padx=(0, 18))
        ctk.CTkRadioButton(
            mode_frame,
            text="資料夾模式 (--onedir，啟動較快)",
            variable=self.var_mode,
            value="onedir",
            font=theme.font(12),
        ).pack(side="left")

        # Row 4: 附加選項
        chk_frame = ctk.CTkFrame(opt, fg_color="transparent")
        chk_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=14, pady=(4, 12))
        self.var_noconsole = ctk.BooleanVar(value=True)
        self.var_clean = ctk.BooleanVar(value=True)
        self.var_autoclean_temp = ctk.BooleanVar(value=True)
        for text, var in (
            ("隱藏背景命令列視窗 (--noconsole)", self.var_noconsole),
            ("編譯前清理快取 (--clean)", self.var_clean),
            ("完成後自動刪除 build/ 與 .spec 暫存檔", self.var_autoclean_temp),
        ):
            ctk.CTkCheckBox(
                chk_frame, text=text, variable=var, font=theme.font(12),
                checkbox_width=18, checkbox_height=18,
            ).pack(side="left", padx=(0, 18))

    def _build_progress_and_log(self) -> None:
        pframe = ctk.CTkFrame(self, fg_color="transparent")
        pframe.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 2))
        pframe.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            pframe, text="狀態：待命中（點擊下方「🚀 開始編譯獨立執行檔」即可打包）",
            font=theme.font(12, "bold"), text_color=theme.ACCENT, anchor="w",
        )
        self.lbl_status.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.progress = ctk.CTkProgressBar(pframe, height=10, progress_color=theme.ACCENT)
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)

        log_frame = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=8)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=14, pady=6)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(
            log_frame,
            fg_color="#121417",
            text_color=theme.FG,
            font=("Consolas", 11),
            wrap="word",
            corner_radius=6,
        )
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._append_log(
            f"=== Kenshi 模組管理器 編譯工具就緒 ===\n"
            f"• 專案路徑：{PROJECT_DIR}\n"
            f"• 進入點腳本：{ENTRY_SCRIPT}\n"
            f"• 自動隨附資源：customtkinter、kmm/base_rules.json、kmm/base_mod_names_zh.json\n"
        )

    def _build_bottom_buttons(self) -> None:
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.grid(row=4, column=0, sticky="ew", padx=14, pady=(4, 14))
        for col in range(3):
            bot.grid_columnconfigure(col, weight=1)

        self.btn_build = ctk.CTkButton(
            bot,
            text="🚀 開始編譯獨立執行檔 (.exe)",
            height=40,
            font=theme.font(14, "bold"),
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            command=self.start_build,
        )
        self.btn_build.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            bot,
            text="📂 開啟輸出資料夾 (dist)",
            height=40,
            font=theme.font(13),
            fg_color=theme.PANEL,
            command=self.open_dist_folder,
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ctk.CTkButton(
            bot,
            text="🧹 清理 build / .spec 暫存檔",
            height=40,
            font=theme.font(13),
            fg_color=theme.PANEL,
            command=self.clean_temp_files,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    # ------------------------------------------------------------ 輔助動作
    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + ("\n" if not text.endswith("\n") else ""))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _refresh_env_status(self) -> None:
        py_ver = sys.version.split()[0]
        pyi_ver = get_pyinstaller_version()
        if pyi_ver:
            self.lbl_env.configure(
                text=f"✔ Python {py_ver}  ｜  ✔ PyInstaller {pyi_ver}（已就緒，可直接編譯）",
                text_color=theme.OK,
            )
        else:
            self.lbl_env.configure(
                text=f"✔ Python {py_ver}  ｜  ⚠ 尚未安裝 PyInstaller（請點擊右側按鈕一鍵安裝）",
                text_color=theme.WARN,
            )

    def _browse_dist(self) -> None:
        folder = filedialog.askdirectory(parent=self, initialdir=self.ent_dist.get() or str(PROJECT_DIR))
        if folder:
            self.ent_dist.delete(0, "end")
            self.ent_dist.insert(0, folder)

    def _browse_icon(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="選擇執行檔圖示 (.ico)",
            filetypes=[("圖示檔案 (*.ico)", "*.ico"), ("所有檔案", "*.*")],
        )
        if path:
            self.ent_icon.delete(0, "end")
            self.ent_icon.insert(0, path)

    def open_dist_folder(self) -> None:
        dist = Path(self.ent_dist.get().strip() or str(DEFAULT_DIST_DIR))
        dist.mkdir(parents=True, exist_ok=True)
        os.startfile(str(dist))

    def clean_temp_files(self, silent: bool = False) -> None:
        removed: list[str] = []
        if DEFAULT_BUILD_DIR.is_dir():
            shutil.rmtree(DEFAULT_BUILD_DIR, ignore_errors=True)
            removed.append("build/")
        for spec in PROJECT_DIR.glob("*.spec"):
            try:
                spec.unlink()
                removed.append(spec.name)
            except OSError:
                pass
        if removed:
            self._append_log(f"[清理完成] 已移除暫存項目：{', '.join(removed)}")
            if not silent:
                messagebox.showinfo("清理完成", f"已清理暫存檔：\n{', '.join(removed)}", parent=self)
        elif not silent:
            messagebox.showinfo("提示", "目前沒有需要清理的 build/ 或 .spec 暫存檔。", parent=self)

    # ------------------------------------------------------------ 安裝與編譯
    def install_pyinstaller(self) -> None:
        if self._busy:
            return
        self._set_busy(True, "正在透過 pip 安裝 / 更新 PyInstaller…")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"]
        self._append_log(f"\n> {' '.join(cmd)}")

        def worker() -> None:
            ok = self._stream_process(cmd)
            self.after(0, lambda: self._on_install_done(ok))

        threading.Thread(target=worker, daemon=True).start()

    def _on_install_done(self, ok: bool) -> None:
        self._set_busy(False, "PyInstaller 安裝完成！" if ok else "PyInstaller 安裝失敗，請檢查網路或權限。")
        self._refresh_env_status()
        if ok:
            messagebox.showinfo("安裝完成", "PyInstaller 已安裝 / 更新完成，現在可以開始編譯！", parent=self)
        else:
            messagebox.showerror("安裝失敗", "無法安裝 PyInstaller，請查看下方日誌輸出。", parent=self)

    def start_build(self) -> None:
        if self._busy:
            return
        if not has_pyinstaller():
            if messagebox.askyesno(
                "尚未安裝 PyInstaller",
                "編譯獨立執行檔需要 PyInstaller 套件。\n\n是否現在自動為您安裝 PyInstaller 並開始編譯？",
                parent=self,
            ):
                self._install_then_build()
            return

        exe_name = self.ent_name.get().strip() or DEFAULT_EXE_NAME
        dist_dir = Path(self.ent_dist.get().strip() or str(DEFAULT_DIST_DIR))
        onefile = self.var_mode.get() == "onefile"
        cmd = build_pyinstaller_args(
            exe_name=exe_name,
            dist_dir=dist_dir,
            work_dir=DEFAULT_BUILD_DIR,
            onefile=onefile,
            noconsole=self.var_noconsole.get(),
            clean=self.var_clean.get(),
            icon_path=self.ent_icon.get().strip(),
        )

        self._set_busy(True, f"正在編譯 {exe_name}.exe（請稍候約 20～60 秒）…")
        self._append_log("\n" + "=" * 68)
        self._append_log(f"開始編譯時間：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        self._append_log(f"執行命令：{' '.join(cmd)}\n")

        def worker() -> None:
            t0 = time.perf_counter()
            ok = self._stream_process(cmd)
            elapsed = time.perf_counter() - t0
            self.after(0, lambda: self._on_build_done(ok, exe_name, dist_dir, onefile, elapsed))

        threading.Thread(target=worker, daemon=True).start()

    def _install_then_build(self) -> None:
        self._set_busy(True, "正在安裝 PyInstaller…")
        install_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"]
        self._append_log(f"\n> {' '.join(install_cmd)}")

        def worker() -> None:
            ok = self._stream_process(install_cmd)
            self.after(0, self._refresh_env_status)
            if not ok:
                self.after(0, lambda: self._set_busy(False, "PyInstaller 安裝失敗。"))
                return
            self.after(0, lambda: (self._set_busy(False, "準備開始編譯…"), self.start_build()))

        threading.Thread(target=worker, daemon=True).start()

    def _stream_process(self, cmd: list[str]) -> bool:
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self.after(0, lambda ln=line: self._append_log(ln.rstrip("\r\n")))
            proc.wait()
            return proc.returncode == 0
        except Exception as exc:
            self.after(0, lambda e=exc: self._append_log(f"[錯誤] {e}"))
            return False

    def _on_build_done(
        self, ok: bool, exe_name: str, dist_dir: Path, onefile: bool, elapsed: float
    ) -> None:
        if self.var_autoclean_temp.get() and ok:
            self.clean_temp_files(silent=True)

        target_exe = (dist_dir / f"{exe_name}.exe") if onefile else (dist_dir / exe_name / f"{exe_name}.exe")
        if ok and target_exe.is_file():
            size_mb = target_exe.stat().st_size / (1024 * 1024)
            msg = (
                f"✔ 編譯成功！（耗時 {elapsed:.1f} 秒）\n\n"
                f"輸出檔案：{target_exe}\n"
                f"檔案大小：{size_mb:.2f} MB\n\n"
                f"是否立即開啟輸出資料夾？"
            )
            self._append_log(f"\n✔ 編譯完成：{target_exe} ({size_mb:.2f} MB，耗時 {elapsed:.1f} 秒)")
            self._set_busy(False, f"✔ 編譯成功：{target_exe.name} ({size_mb:.2f} MB)")
            if messagebox.askyesno("編譯成功", msg, parent=self):
                self.open_dist_folder()
        else:
            self._append_log("\n✖ 編譯失敗，請檢查上方日誌訊息。")
            self._set_busy(False, "✖ 編譯失敗，請檢查日誌訊息。")
            messagebox.showerror("編譯失敗", "編譯過程中發生錯誤，請檢查日誌視窗中的詳細訊息。", parent=self)

    def _set_busy(self, busy: bool, status_text: str) -> None:
        self._busy = busy
        self.lbl_status.configure(text=f"狀態：{status_text}")
        state = "disabled" if busy else "normal"
        self.btn_build.configure(state=state)
        self.btn_install_pyi.configure(state=state)
        if busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(1.0 if "成功" in status_text or "完成" in status_text else 0.0)


def main() -> None:
    app = CompilerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
