"""Steam 與 Kenshi 安裝路徑偵測（對應 C# MainWindow.SteamGameDetection）。

原版必須在 Steam 執行中才能偵測；這裡改為讀取登錄檔取得 Steam 路徑，
再解析 steamapps/libraryfolders.vdf 找出安裝 Kenshi 的媒體庫。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import constants

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])')


def parse_vdf(text: str) -> dict:
    """解析 Valve KeyValues 文字格式（只支援 libraryfolders.vdf 用到的子集）。"""
    stack: list[dict] = [{}]
    key: str | None = None
    for m in _TOKEN.finditer(text):
        s, brace = m.group(1), m.group(2)
        if brace == "{":
            new: dict = {}
            stack[-1][key if key is not None else ""] = new
            stack.append(new)
            key = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            key = None
        else:
            value = s.replace("\\\\", "\\").replace('\\"', '"')
            if key is None:
                key = value
            else:
                stack[-1][key] = value
                key = None
    return stack[0]


def steam_install_path() -> Path | None:
    try:
        import winreg
    except ImportError:
        return None
    candidates = [(winreg.HKEY_LOCAL_MACHINE, p, v) for p, v in constants.STEAM_REGISTRY_PATHS]
    candidates.append((winreg.HKEY_CURRENT_USER, *constants.STEAM_USER_REGISTRY))
    for hive, sub, value in candidates:
        try:
            with winreg.OpenKey(hive, sub) as k:
                path = Path(winreg.QueryValueEx(k, value)[0])
                if path.is_dir():
                    return path
        except OSError:
            continue
    default = Path(constants.DEFAULT_STEAM_DIRECTORY)
    return default if default.is_dir() else None


def find_kenshi(steam_dir: Path | None = None) -> tuple[Path, Path] | None:
    """回傳 (遊戲資料夾, 工作坊模組資料夾)；找不到時回傳 None。"""
    steam_dir = steam_dir or steam_install_path()
    if not steam_dir:
        return None
    vdf = steam_dir / "steamapps" / "libraryfolders.vdf"
    libraries: list[Path] = [steam_dir]
    if vdf.is_file():
        data = parse_vdf(vdf.read_text(encoding="utf-8", errors="replace"))
        folders = data.get("libraryfolders") or data.get("LibraryFolders") or {}
        for entry in folders.values():
            if isinstance(entry, dict):
                apps = entry.get("apps", {})
                if constants.KENSHI_APP_ID in apps and entry.get("path"):
                    libraries.insert(0, Path(entry["path"]))
                elif entry.get("path"):
                    libraries.append(Path(entry["path"]))
            elif isinstance(entry, str):  # 舊格式："1" "D:\\SteamLibrary"
                libraries.append(Path(entry))
    for lib in libraries:
        game = lib / "steamapps" / "common" / "Kenshi"
        if game.is_dir():
            return game, lib / "steamapps" / "workshop" / "content" / constants.KENSHI_APP_ID
    return None


def guess_kenshi_folder() -> Path | None:
    steam = steam_install_path()
    if steam:
        p = steam / "steamapps" / "common" / "Kenshi"
        if p.is_dir():
            return p
    return None
