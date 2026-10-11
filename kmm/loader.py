"""模組掃描、mods.cfg 讀寫、資料夾連結（對應 C# Core/LoadService.cs）。"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

from . import constants, logging_util
from .config import KenshiToolConfig
from .mod_reader import load_metadata
from .models import Mod, Source


# ---------------------------------------------------------------- mods.cfg

def mods_cfg_path(cfg: KenshiToolConfig) -> Path:
    return Path(cfg.GamePath) / "data" / "mods.cfg"


def get_current_active_mods(cfg: KenshiToolConfig) -> list[str]:
    try:
        text = mods_cfg_path(cfg).read_text(encoding="utf-8-sig")
    except OSError as exc:
        logging_util.write(constants.ERROR_FILE, "無法讀取 mods.cfg，請檢查遊戲路徑設定。")
        logging_util.write_exception(constants.ERROR_FILE, exc)
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def _ensure_writable(path: Path) -> None:
    """若檔案已存在且被設為唯讀，自動解除唯讀屬性以避免寫入失敗。"""
    if path.exists():
        try:
            mode = path.stat().st_mode
            if not (mode & stat.S_IWRITE):
                os.chmod(path, mode | stat.S_IWRITE)
        except OSError:
            pass


def active_file_names(mods: Iterable[Mod]) -> list[str]:
    """依載入順序回傳啟用模組檔名清單，並自動去除重複檔名（保留第一個）。"""
    seen: set[str] = set()
    result: list[str] = []
    for m in sorted((m for m in mods if m.active), key=lambda m: m.order):
        key = m.file_name.lower()
        if key not in seen:
            seen.add(key)
            result.append(m.file_name)
    return result


def save_mods_cfg(cfg: KenshiToolConfig, mods: Iterable[Mod]) -> None:
    """寫入 mods.cfg，先備份成 mods.cfg.backup。找不到 data 資料夾時丟出 FileNotFoundError。"""
    data_dir = Path(cfg.GamePath) / "data"
    if not cfg.GamePath or not data_dir.is_dir():
        raise FileNotFoundError(str(data_dir))
    target = data_dir / "mods.cfg"
    if target.exists():
        backup = target.with_name("mods.cfg.backup")
        _ensure_writable(backup)
        backup.write_bytes(target.read_bytes())
    write_profile(target, mods)


def write_profile(path: Path, mods: Iterable[Mod]) -> None:
    # 與原版 File.WriteAllLines 相同：每行結尾 CRLF
    _ensure_writable(path)
    lines = active_file_names(mods)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("".join(f"{n}\n" for n in lines))


def read_profile(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def apply_profile(mods: list[Mod], names: list[str]) -> int:
    """套用設定檔，回傳成功對應的模組數量。"""
    for m in mods:
        m.order, m.active = -1, False
    by_name = {m.file_name: m for m in mods}
    hit = 0
    for i, name in enumerate(names):
        m = by_name.get(name)
        if m:
            m.active, m.order = True, i
            hit += 1
    return hit


# ---------------------------------------------------------------- 連結判斷

def is_link(path: Path) -> bool:
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return False


def is_broken_link(path: Path) -> bool:
    return is_link(path) and not path.exists()


def delete_folder(path: Path) -> None:
    """只刪除連結本身或空資料夾，不會遞迴刪除內容。"""
    if is_link(path):
        os.rmdir(path) if path.is_junction() or path.is_dir() else path.unlink()
    elif path.is_dir():
        path.rmdir()


def create_junction(target_link: Path, source_dir: Path) -> None:
    """建立目錄連接點 target_link -> source_dir（不需要系統管理員權限）。"""
    try:
        import _winapi
        _winapi.CreateJunction(str(source_dir), str(target_link))
    except (ImportError, AttributeError):
        subprocess.run(["cmd", "/c", "mklink", "/J", str(target_link), str(source_dir)],
                       check=True, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def create_links(pairs: Iterable[tuple[Path, Path]]) -> list[str]:
    """pairs = (連結位置, 來源資料夾)。回傳錯誤訊息清單。"""
    errors: list[str] = []
    info: list[str] = []
    for link, src in pairs:
        if link.exists() or is_link(link):
            info.append(f"資料夾已存在，略過：{link}")
            continue
        try:
            create_junction(link, src)
            info.append(f"已建立連結：{src} -> {link}")
        except (OSError, subprocess.CalledProcessError) as exc:
            msg = f"建立連結失敗：{src} -> {link}（{exc}）"
            errors.append(msg)
    logging_util.write(constants.LOG_FILE, info)
    logging_util.write(constants.ERROR_FILE, errors)
    return errors


def folder_cleanup(path: Path) -> list[Path]:
    """遞迴刪除空資料夾，回傳被刪除的路徑。不會進入連結內部。"""
    removed: list[Path] = []
    if not path or not path.is_dir():
        return removed
    for child in path.iterdir():
        if not child.is_dir() or is_link(child):
            continue
        removed.extend(folder_cleanup(child))
        try:
            if not any(child.iterdir()):
                child.rmdir()
                removed.append(child)
        except OSError:
            pass
    if removed:
        logging_util.write(constants.LOG_FILE, [f"已刪除空資料夾：{p}" for p in removed])
    return removed


# ---------------------------------------------------------------- 掃描模組

def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def read_info_file(info_path: Path, mod: Mod) -> None:
    """讀取 Steam 工作坊的 _模組名.info（XML），取得 ID、標題與分類。"""
    target = info_path
    folder = info_path.parent
    if not target.is_file() and folder.is_dir():
        infos = sorted(folder.glob("*.info"))
        if infos:
            target = infos[0]
    if not target.is_file():
        return
    root = ET.parse(target).getroot()
    tags: list[str] = []
    for tag_node in root.iter("tags"):
        tags.extend((s.text or "").strip() for s in tag_node.iter("string"))
    mod.categories = [t for t in tags if t]
    id_node = next(root.iter("id"), None)
    if id_node is not None and id_node.text:
        mod.id = id_node.text.strip()
    title_node = next(root.iter("title"), None)
    if title_node is not None and title_node.text:
        mod.title = title_node.text.strip()

    # 若主 .info 的標題不含中文，但同資料夾內有其他含中文標題的 .info，取其補充
    if not _has_cjk(mod.title) and folder.is_dir():
        for extra in sorted(folder.glob("*.info")):
            if extra == target:
                continue
            try:
                t_node = next(ET.parse(extra).getroot().iter("title"), None)
                if t_node is not None and t_node.text and _has_cjk(t_node.text):
                    mod.title = t_node.text.strip()
                    break
            except (ET.ParseError, OSError):
                continue


def _is_inside(child: str, parent: str) -> bool:
    if not parent:
        return False
    try:
        return os.path.normcase(os.path.abspath(child)).startswith(os.path.normcase(os.path.abspath(parent)))
    except ValueError:
        return False


def load_mods_from(cfg: KenshiToolConfig, current: list[str], path: Path) -> list[Mod]:
    result: list[Mod] = []
    if not path.is_dir():
        logging_util.write(constants.ERROR_FILE, f"無法讀取資料夾：{path}")
        return result

    for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir() and not is_link(item):
            continue
        if is_link(item):
            # 連結是由 Steam 模組建立的，略過避免重複；失效的連結直接清除
            if is_broken_link(item):
                try:
                    delete_folder(item)
                    logging_util.write(constants.LOG_FILE, f"已移除失效連結：{item}")
                except OSError:
                    pass
            continue

        mod_files = sorted(item.glob("*.mod"))
        mod = Mod(file_path=str(mod_files[0]) if mod_files else str(item))

        try:
            read_info_file(item / f"_{Path(mod.file_path).stem}.info", mod)
        except (ET.ParseError, OSError) as exc:
            logging_util.write(constants.ERROR_FILE, f"無法讀取模組資訊檔，可能已損毀：{mod.file_path}")
            logging_util.write_exception(constants.ERROR_FILE, exc)

        mod.source = Source.GAME_FOLDER if _is_inside(mod.file_path, cfg.GamePath) else Source.STEAM

        md = load_metadata(mod.file_path) if mod_files else None
        if md is None:
            mod.description = f"無法讀取此模組，可能已損毀或是空資料夾。請檢查 error.log 與模組資料夾：{item}"
            logging_util.write(constants.ERROR_FILE, f"無法讀取模組檔頭：{item}")
        else:
            mod.dependencies = md.dependencies
            mod.references = md.referenced
            mod.description = md.description
            mod.version = str(md.version)
            mod.author = md.author

        if mod.file_name in current:
            mod.active = True
            mod.order = current.index(mod.file_name)

        result.append(mod)
    return result


def get_list_of_mods(cfg: KenshiToolConfig) -> list[Mod]:
    current = get_current_active_mods(cfg)
    mods: list[Mod] = []
    if cfg.uses_steam and cfg.SteamModsPath:
        mods.extend(load_mods_from(cfg, current, Path(cfg.SteamModsPath)))
    if cfg.GamePath:
        mods.extend(load_mods_from(cfg, current, cfg.mod_folder))

    # 若工作坊與本機 Mods 資料夾同時存在相同 .mod 檔名，僅保留第一個為啟用狀態，避免重複寫入 mods.cfg
    seen_active: set[str] = set()
    dup_logs: list[str] = []
    for m in mods:
        if not m.active:
            continue
        key = m.file_name.lower()
        if key in seen_active:
            m.active = False
            m.order = -1
            dup_logs.append(f"偵測到重複模組檔名，已自動停用重複項：{m.file_path}")
        else:
            seen_active.add(key)
    if dup_logs:
        normalize_orders(mods)

    counts = Counter(m.source.value for m in mods)
    log = [f"已載入 {len(mods)} 個模組",
           ", ".join(f"{k} - {v}" for k, v in counts.items())]
    if dup_logs:
        log.extend(dup_logs)
    log.append("詳細清單：")
    log.extend(f"{m.source.value} - {m.file_path}" for m in mods)
    logging_util.write(constants.LOG_FILE, log)
    return mods


def backup_subscribed_list(
    cfg: KenshiToolConfig,
    mods: list[Mod],
    *,
    logs_dir: Path | None = None,
    base_dir: Path | None = None,
) -> None:
    """每次啟動時將 Steam 訂閱 ID 清單備份至 logs/ 子資料夾，只保留最近 MaxLogFiles 份，並自動遷移舊版根目錄備份檔。"""
    if not mods:
        return
    target_dir = logs_dir or constants.LOGS_DIR
    root_dir = base_dir or constants.BASE_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    # 自動將舊版殘留在主目錄的 bkpsubscribedList*.info 移入 logs/ 子資料夾
    if root_dir.is_dir() and root_dir != target_dir:
        for legacy in sorted(root_dir.glob(f"{constants.BACKUP_SUBSCRIBE_LIST}*")):
            if not legacy.is_file():
                continue
            dest = target_dir / legacy.name
            try:
                if dest.exists():
                    legacy.unlink()
                else:
                    shutil.move(str(legacy), str(dest))
            except OSError:
                pass

    files = sorted(target_dir.glob(f"{constants.BACKUP_SUBSCRIBE_LIST}*"))
    while len(files) >= max(cfg.MaxLogFiles, 1):
        try:
            files.pop(0).unlink()
        except OSError:
            break
    name = f"{constants.BACKUP_SUBSCRIBE_LIST}{datetime.now():%Y%m%d%H%M%S}.info"
    ids = [m.id for m in mods if m.source is Source.STEAM and m.id]
    try:
        (target_dir / name).write_text("\r\n".join(ids), encoding="utf-8")
    except OSError:
        pass


def clear_logs_and_backups(
    base_dir: Path | None = None,
    logs_dir: Path | None = None,
) -> int:
    """清除 logs/ 與根目錄下所有 bkpsubscribedList*.info、info.log、error.log，回傳刪除檔案數。"""
    root_dir = base_dir or constants.BASE_DIR
    target_dir = logs_dir or constants.LOGS_DIR
    removed = 0
    for folder in {root_dir, target_dir}:
        if not folder or not folder.is_dir():
            continue
        candidates = list(folder.glob(f"{constants.BACKUP_SUBSCRIBE_LIST}*"))
        for log_name in ("info.log", "error.log"):
            p = folder / log_name
            if p.is_file():
                candidates.append(p)
        for f in candidates:
            if not f.is_file():
                continue
            try:
                _ensure_writable(f)
                f.unlink()
                removed += 1
            except OSError:
                pass
    return removed


# ---------------------------------------------------------------- 排序 / 相依

def set_new_order(mods: list[Mod], current: Mod, new: int) -> None:
    """把 current 移到 new 的位置，其他有順序的模組依序遞補（對應 C# SetNewOrder）。"""
    new = max(new, 0)
    others = sorted((m for m in mods if m.order != -1 and m is not current), key=lambda m: m.order)
    i = 0
    for m in others:
        if i == new:
            i += 1
        m.order = i
        i += 1
    current.order = new

    active_others = [m for m in mods if m.active and m is not current]
    max_order = max((m.order for m in active_others), default=0)
    if new > max_order:
        current.order = max_order + 1


def normalize_orders(mods: list[Mod]) -> None:
    """讓啟用的模組順序連續（0,1,2...），停用的設為 -1。"""
    i = 0
    for m in sorted(mods, key=lambda m: (m.order == -1, m.order)):
        if m.active:
            m.order = i
            i += 1
        else:
            m.order = -1


def missing_dependencies(mods: list[Mod], mod: Mod) -> list[str]:
    """回傳尚未在此模組之前啟用的相依項目。"""
    loaded_before = [m.file_name.lower() for m in mods if m.active and m.order < mod.order]
    return [d for d in mod.all_dependencies
            if not any(d.lower() in name for name in loaded_before)]


def dependency_ok(mods: list[Mod], mod: Mod, dep: str) -> bool:
    d = dep.lower()
    return any(m.active and m.order < mod.order and d in m.file_name.lower() for m in mods)


def set_active(mods: list[Mod], targets: Iterable[Mod], active: bool | None) -> None:
    """批次啟用 / 停用 / 切換（active=None）。新啟用的模組接在目前清單最後面。"""
    for m in targets:
        new_state = (not m.active) if active is None else active
        if new_state == m.active:
            continue
        m.active = new_state
        if new_state:
            m.order = max((x.order for x in mods if x.active and x is not m), default=-1) + 1
        else:
            m.order = -1
    normalize_orders(mods)


def is_mod_valid(mod: Mod) -> bool:
    """檢查模組的資料夾與 .mod 檔案是否都存在。"""
    if not mod.has_extension:
        return False
    p = Path(mod.file_path)
    return p.is_file() and Path(mod.folder).is_dir()


def find_invalid_mods(mods: Iterable[Mod]) -> list[Mod]:
    """回傳所有資料夾不存在或缺少 .mod 檔案的無效模組。"""
    return [m for m in mods if not is_mod_valid(m)]


def _force_remove_readonly(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_mods_and_folders(
    cfg: KenshiToolConfig,
    mods: list[Mod],
    targets: Iterable[Mod],
) -> tuple[int, list[str]]:
    """將指定模組從清單移除，並一併刪除其磁碟資料夾（與連結）。回傳 (移除數量, 錯誤清單)。"""
    target_list = list(targets)
    removed_count = 0
    errors: list[str] = []
    logs: list[str] = []

    for mod in target_list:
        folder = Path(mod.folder)
        # 若為 Steam 模組且在遊戲 Mods 目錄建有連結，先移除連結
        if cfg.GamePath and mod.has_extension:
            link_in_game = cfg.mod_folder / Path(mod.file_path).stem
            if link_in_game != folder and is_link(link_in_game):
                try:
                    delete_folder(link_in_game)
                    logs.append(f"已移除遊戲目錄連結：{link_in_game}")
                except OSError as exc:
                    errors.append(f"{link_in_game}：{exc}")

        # 刪除模組資料夾本身
        try:
            if is_link(folder):
                delete_folder(folder)
                logs.append(f"已移除模組連結：{folder}")
            elif folder.is_dir():
                shutil.rmtree(folder, onexc=_force_remove_readonly)
                logs.append(f"已刪除模組資料夾：{folder}")
            else:
                logs.append(f"已移除不存在的模組項目：{folder}")
            if mod in mods:
                mods.remove(mod)
            removed_count += 1
        except OSError as exc:
            errors.append(f"{folder}：{exc}")

    normalize_orders(mods)
    logging_util.write(constants.LOG_FILE, logs)
    logging_util.write(constants.ERROR_FILE, errors)
    return removed_count, errors

