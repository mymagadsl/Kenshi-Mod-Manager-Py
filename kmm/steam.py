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


# ---------------------------------------------------------------- 多帳號與訂閱解析

_STEAM64_BASE = 76561197960265728


class SteamAccount:
    def __init__(
        self,
        account_id_32: str,
        steam_id_64: str,
        persona_name: str = "",
        account_name: str = "",
        is_current: bool = False,
    ):
        self.account_id_32 = str(account_id_32)
        self.steam_id_64 = str(steam_id_64)
        self.persona_name = persona_name
        self.account_name = account_name
        self.is_current = is_current

    @property
    def display_name(self) -> str:
        name = self.persona_name or self.account_name or self.account_id_32
        return f"{name} (目前登入)" if self.is_current else name

    def workshop_subscriptions_url(self) -> str:
        return (
            f"https://steamcommunity.com/profiles/{self.steam_id_64}"
            f"/myworkshopfiles/?appid={constants.KENSHI_APP_ID}&browsefilter=mysubscriptions"
        )

    def __repr__(self) -> str:
        return f"<SteamAccount {self.account_id_32} ({self.display_name})>"


def current_active_steam_user_id() -> str | None:
    """從 Windows 登錄檔讀取目前運行的 Steam 帳號 (32-bit ID)。"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam\ActiveProcess") as k:
            val = winreg.QueryValueEx(k, "ActiveUser")[0]
            if val and int(val) > 0:
                return str(val)
    except (ImportError, OSError, ValueError):
        pass
    return None


def get_known_steam_accounts(steam_dir: Path | None = None) -> list[SteamAccount]:
    """解析 Steam 的 config/loginusers.vdf，取得電腦上曾登入的所有 Steam 帳號。"""
    steam_dir = steam_dir or steam_install_path()
    current_uid = current_active_steam_user_id()
    accounts: list[SteamAccount] = []
    seen_ids: set[str] = set()

    if steam_dir:
        vdf_path = steam_dir / "config" / "loginusers.vdf"
        if vdf_path.is_file():
            try:
                data = parse_vdf(vdf_path.read_text(encoding="utf-8", errors="replace"))
                users = data.get("users") or data.get("Users") or {}
                for sid64_str, info in users.items():
                    if not isinstance(info, dict) or not sid64_str.isdigit():
                        continue
                    sid64 = int(sid64_str)
                    aid32 = str(sid64 - _STEAM64_BASE) if sid64 > _STEAM64_BASE else sid64_str
                    p_name = info.get("PersonaName") or info.get("personaname") or ""
                    a_name = info.get("AccountName") or info.get("accountname") or ""
                    is_cur = (aid32 == current_uid) or (info.get("MostRecent") == "1" and not current_uid)
                    acc = SteamAccount(
                        account_id_32=aid32,
                        steam_id_64=sid64_str,
                        persona_name=p_name,
                        account_name=a_name,
                        is_current=is_cur,
                    )
                    accounts.append(acc)
                    seen_ids.add(aid32)
            except Exception:
                pass

    # 若登錄檔偵測到的 current_uid 不在 loginusers 內，補齊之
    if current_uid and current_uid not in seen_ids:
        try:
            sid64 = str(int(current_uid) + _STEAM64_BASE)
        except ValueError:
            sid64 = current_uid
        accounts.insert(
            0,
            SteamAccount(
                account_id_32=current_uid,
                steam_id_64=sid64,
                persona_name=f"帳號 {current_uid}",
                is_current=True,
            ),
        )

    # 排序：目前登入的置頂，其餘依名稱排序
    accounts.sort(key=lambda a: (not a.is_current, a.display_name.lower()))
    return accounts


def get_mod_subscribers(steam_mods_path: Path) -> dict[str, list[str]]:
    """從 appworkshop_233860.acf 解析各模組的訂閱者列表：{mod_id: [steam_id_32, ...]}。"""
    result: dict[str, list[str]] = {}
    if not steam_mods_path or not steam_mods_path.is_dir():
        return result
    acf_path = steam_mods_path.parent.parent / f"appworkshop_{constants.KENSHI_APP_ID}.acf"
    if not acf_path.is_file():
        return result

    try:
        text = acf_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    # 搜尋 WorkshopItemDetails 中的 subscribedby
    sec_match = re.search(r'"WorkshopItemDetails"\s*\{(.+)\}\s*\}', text, re.DOTALL)
    if not sec_match:
        # 有時整個檔案結尾可能格式略有不同，改用更寬鬆的匹配
        sec_match = re.search(r'"WorkshopItemDetails"\s*\{(.*)', text, re.DOTALL)
    if sec_match:
        content = sec_match.group(1)
        # 匹配 "123456" { ... "subscribedby" "id1,id2" ... }
        for m in re.finditer(r'"(\d+)"\s*\{([^{}]+)\}', content):
            mid = m.group(1)
            body = m.group(2)
            sub_m = re.search(r'"subscribedby"\s+"([^"]*)"', body)
            if sub_m and sub_m.group(1).strip():
                subs = [s.strip() for s in sub_m.group(1).split(",") if s.strip()]
                result[mid] = subs
            else:
                result[mid] = []
    return result

