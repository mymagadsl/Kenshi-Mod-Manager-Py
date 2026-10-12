"""Kenshi 當機與 Log 診斷分析器。

解析遊戲目錄下的：
- crashDump*.zip 內的 .dmp（Windows Minidump 異常碼、故障位址、已載入模組）
- RE_Kenshi_log.txt（RE_Kenshi 插件載入、當機前最後 30 秒活躍插件、錯誤訊息）
- RE_Kenshi/DesoCrash.log（VEH 崩潰現場、呼叫堆疊）
- MyGUI.log（UI 貼圖與版面錯誤，並自動反查實際引用該貼圖的模組 .dll/.mod）
- kenshi_info.log / kenshi.log / Havok.log（模型缺失、翻譯缺件、最後載入資源、導航網格）
並與模組管理器中實際安裝的模組清單交叉比對，給出零幻覺的可疑模組排行與修復建議。
"""
from __future__ import annotations

import os
import re
import stat
import struct
import time
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import Mod

EXCEPTION_NAMES: dict[int, str] = {
    0xC0000005: "Access Violation（記憶體存取違規 / 空指標讀取）",
    0xC00000FD: "Stack Overflow（堆疊溢位）",
    0xC0000409: "Stack Buffer Overrun（堆疊緩衝區溢位 / Fail-Fast）",
    0xC000001D: "Illegal Instruction（非法指令）",
    0xC0000094: "Integer Divide by Zero（除以零錯誤）",
    0x80000003: "Breakpoint（中斷點觸發）",
    0xE06D7363: "Microsoft C++ Exception（未捕捉的 C++ 例外）",
}


@dataclass
class DumpAnalysis:
    zip_path: str = ""
    dmp_name: str = ""
    crash_time: str = ""
    exception_code: int = 0
    exception_name: str = ""
    exception_address: int = 0
    faulting_module: str = ""
    faulting_offset: int = 0
    plugin_dlls: list[str] = field(default_factory=list)


@dataclass
class DesoCrashEntry:
    header: str = ""
    exception_line: str = ""
    last_hook: str = ""
    access_line: str = ""
    stack_line: str = ""
    source_file: str = ""


@dataclass
class SuspectMod:
    mod: Mod | None
    name: str
    dll_name: str = ""
    score: int = 0
    level: str = "LOW"  # HIGH / MEDIUM / LOW
    reasons: list[str] = field(default_factory=list)


@dataclass
class CrashAnalysisReport:
    analyzed_at: str = ""
    elapsed_sec: float = 0.0
    game_path: str = ""
    crash_detected: bool = False
    crash_time_str: str = ""
    crash_summary: str = ""
    dump: DumpAnalysis | None = None
    deso_entry: DesoCrashEntry | None = None
    re_kenshi_crash_line: str = ""
    gui_exceptions: list[str] = field(default_factory=list)
    re_kenshi_loaded_plugins: list[tuple[str, str]] = field(default_factory=list)  # (mod_name, dll_name)
    re_kenshi_recent_activity: list[tuple[str, int, str]] = field(default_factory=list)  # (plugin, count, last_msg)
    re_kenshi_warnings: list[str] = field(default_factory=list)
    mygui_errors: list[str] = field(default_factory=list)
    mygui_warnings_count: int = 0
    missing_textures_owners: dict[str, list[str]] = field(default_factory=dict)  # texture -> [mod/dll names]
    kenshi_info_warnings: list[str] = field(default_factory=list)
    missing_meshes: list[str] = field(default_factory=list)
    missing_meshes_total: int = 0
    last_loaded_resources: list[str] = field(default_factory=list)
    havok_errors_count: int = 0
    havok_samples: list[str] = field(default_factory=list)
    suspects: list[SuspectMod] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def _fmt_mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return ""


def _parse_minidump_bytes(data: bytes) -> tuple[int, int, str, int, list[str]]:
    """解析 Windows Minidump (.dmp) 二進位內容。
    回傳 (exception_code, exception_addr, faulting_module, faulting_offset, non_system_dlls)。
    """
    if len(data) < 32 or data[:4] != b"MDMP":
        return 0, 0, "", 0, []

    num_streams, dir_rva = struct.unpack_from("<II", data, 8)
    exc_code = 0
    exc_addr = 0
    modules: list[tuple[int, int, str]] = []

    for i in range(min(num_streams, 64)):
        off = dir_rva + i * 12
        if off + 12 > len(data):
            break
        stype, ssize, srva = struct.unpack_from("<III", data, off)
        if srva + ssize > len(data):
            continue
        if stype == 6 and ssize >= 32:  # ExceptionStream
            exc_code = struct.unpack_from("<I", data, srva + 8)[0]
            exc_addr = struct.unpack_from("<Q", data, srva + 24)[0]
        elif stype == 4 and ssize >= 4:  # ModuleListStream
            mod_count = struct.unpack_from("<I", data, srva)[0]
            for m in range(min(mod_count, 512)):
                mo = srva + 4 + m * 108
                if mo + 108 > len(data):
                    break
                base_addr = struct.unpack_from("<Q", data, mo)[0]
                mod_size = struct.unpack_from("<I", data, mo + 8)[0]
                name_rva = struct.unpack_from("<I", data, mo + 20)[0]
                if name_rva + 4 <= len(data):
                    name_len = struct.unpack_from("<I", data, name_rva)[0]
                    if name_rva + 4 + name_len <= len(data):
                        mod_name = data[name_rva + 4 : name_rva + 4 + name_len].decode("utf-16-le", errors="replace")
                        modules.append((base_addr, base_addr + mod_size, mod_name))

    fault_mod = ""
    fault_off = 0
    plugin_dlls: list[str] = []
    for start, end, name in modules:
        if exc_addr and start <= exc_addr < end:
            fault_mod = name
            fault_off = exc_addr - start
        norm = name.lower()
        if norm.endswith(".dll") and not norm.startswith("c:\\windows\\") and "steam" not in Path(name).name.lower():
            if "233860" in norm or "\\mods\\" in norm or "re_kenshi" in norm or "kenshilib" in norm:
                plugin_dlls.append(name)

    return exc_code, exc_addr, fault_mod, fault_off, plugin_dlls


def _analyze_crash_dump(game_dir: Path) -> DumpAnalysis | None:
    zips = sorted(game_dir.glob("crashDump*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        return None
    zpath = zips[0]
    res = DumpAnalysis(zip_path=str(zpath), crash_time=_fmt_mtime(zpath))
    try:
        with zipfile.ZipFile(zpath, "r") as zf:
            dmps = [n for n in zf.namelist() if n.lower().endswith(".dmp")]
            if not dmps:
                return res
            res.dmp_name = dmps[0]
            raw = zf.read(dmps[0])
            code, addr, fmod, foff, dlls = _parse_minidump_bytes(raw)
            res.exception_code = code
            res.exception_name = EXCEPTION_NAMES.get(code, f"未知異常 (0x{code:08X})" if code else "")
            res.exception_address = addr
            res.faulting_module = fmod
            res.faulting_offset = foff
            res.plugin_dlls = dlls
    except (OSError, zipfile.BadZipFile):
        pass
    return res


def _analyze_deso_crash(game_dir: Path) -> DesoCrashEntry | None:
    re_dir = game_dir / "RE_Kenshi"
    for fname in ("DesoCrash.log", "DesoCrash.log.1"):
        fpath = re_dir / fname
        if not fpath.is_file():
            continue
        try:
            # 只讀最後 512KB 加速處理
            size = fpath.stat().st_size
            with open(fpath, "rb") as f:
                if size > 524288:
                    f.seek(size - 524288)
                text = f.read().decode("utf-8", errors="replace")
        except OSError:
            continue
        blocks = list(re.finditer(r"=====\s*\[崩溃现场[^\r\n]*=====", text))
        if not blocks:
            continue
        last_pos = blocks[-1].start()
        snippet = text[last_pos : last_pos + 4000].splitlines()
        entry = DesoCrashEntry(header=snippet[0].strip(), source_file=fname)
        for line in snippet[1:15]:
            s = line.strip()
            if s.startswith("异常码="):
                entry.exception_line = s
            elif s.startswith("最后进入的钩子="):
                entry.last_hook = s.split("=", 1)[1].strip()
            elif s.startswith("访问类型="):
                entry.access_line = s
            elif s.startswith("栈扫描:"):
                entry.stack_line = s
        return entry
    return None


@dataclass
class _DllProfile:
    dll_path: Path
    mod: Mod | None
    hooks_inventory_icon: bool = False
    hooks_inventory_gui: bool = False
    hooks_inventory_lifecycle: bool = False
    hooks_inventory_transfer: bool = False
    hooks_inventory_data: bool = False
    hooks_mygui: bool = False
    ascii_blob: bytes = b""


def _build_mod_lookup(mods: Iterable[Mod], game_dir: Path) -> tuple[dict[str, Mod], dict[str, _DllProfile]]:
    """建立 (名稱->Mod 索引, DLL檔名小寫->_DllProfile 索引)。"""
    by_key: dict[str, Mod] = {}
    dll_profiles: dict[str, _DllProfile] = {}

    for m in mods:
        for k in (
            m.file_name.lower(),
            (m.title or "").lower(),
            m.display_name.lower(),
            (m.zh_name or "").lower(),
            (m.id or "").lower(),
        ):
            if k:
                by_key[k] = m
        folder = Path(m.folder)
        if folder.is_dir():
            for dll in folder.glob("*.dll"):
                try:
                    blob = dll.read_bytes()
                except OSError:
                    blob = b""
                prof = _DllProfile(
                    dll_path=dll,
                    mod=m,
                    hooks_inventory_icon=b"InventoryIcon" in blob,
                    hooks_inventory_gui=(b"InventoryGUI" in blob or b"InventoryLayout" in blob or b"InventorySectionGUI" in blob),
                    hooks_inventory_lifecycle=(
                        b"_DESTRUCTOR@InventoryGUI" in blob
                        and b"createInventoryLayout" in blob
                        and b"removeItem@InventorySection" in blob
                    ),
                    hooks_inventory_transfer=(
                        b"tryAddItem@Inventory" in blob
                        or b"_sectionAddItemCallback@Inventory" in blob
                    ),
                    hooks_inventory_data=(b"Inventory@@" in blob or b"InventorySection@@" in blob or b"InventoryItemBase@@" in blob),
                    hooks_mygui=(b"MyGUI@@" in blob),
                    ascii_blob=blob,
                )
                dll_profiles[dll.name.lower()] = prof

    return by_key, dll_profiles


def analyze_logs(game_path: str | Path, mods: Iterable[Mod]) -> CrashAnalysisReport:
    t0 = time.perf_counter()
    game_dir = Path(game_path) if game_path else Path()
    mod_list = list(mods)
    report = CrashAnalysisReport(
        analyzed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        game_path=str(game_dir),
    )
    if not game_dir.is_dir():
        report.crash_summary = "找不到遊戲目錄，請先在「設定」中確認 Kenshi 遊戲路徑。"
        report.elapsed_sec = time.perf_counter() - t0
        return report

    by_key, dll_profiles = _build_mod_lookup(mod_list, game_dir)
    suspect_map: dict[str, SuspectMod] = {}

    def add_suspect(
        mod: Mod | None,
        fallback_name: str,
        dll_name: str,
        points: int,
        reason: str,
    ) -> None:
        # 若該模組目前在管理器中已被使用者取消勾選（未啟用），則不列入可疑排行
        if mod is not None and not mod.active:
            return
        key = mod.uid if mod else (dll_name.lower() or fallback_name.lower())
        if key not in suspect_map:
            disp = mod.ui_name(True) if mod else fallback_name
            suspect_map[key] = SuspectMod(mod=mod, name=disp, dll_name=dll_name)
        item = suspect_map[key]
        if dll_name and not item.dll_name:
            item.dll_name = dll_name
        item.score += points
        if reason not in item.reasons:
            item.reasons.append(reason)

    def resolve_mod(name_or_dll: str) -> Mod | None:
        clean = name_or_dll.strip().lower()
        if clean in dll_profiles and dll_profiles[clean].mod:
            return dll_profiles[clean].mod
        if f"{clean}.dll" in dll_profiles and dll_profiles[f"{clean}.dll"].mod:
            return dll_profiles[f"{clean}.dll"].mod
        if clean in by_key:
            return by_key[clean]
        # 去除空白或符號比對
        compact = re.sub(r"[\s_\-!]+", "", clean)
        for k, m in by_key.items():
            if compact and compact == re.sub(r"[\s_\-!]+", "", k):
                return m
        return None

    # 檢查最新一局遊戲 Log 時間，判斷 crashDump 是否為上一局留下的舊檔案
    re_log_path = game_dir / "RE_Kenshi_log.txt"
    klog_path = game_dir / "kenshi.log"
    latest_session_mtime = 0.0
    for lp in (re_log_path, klog_path):
        if lp.is_file():
            try:
                latest_session_mtime = max(latest_session_mtime, lp.stat().st_mtime)
            except OSError:
                pass

    # 1. 解析 crashDump*.zip
    dump = _analyze_crash_dump(game_dir)
    report.dump = dump
    dump_is_stale = False
    if dump and dump.exception_code:
        try:
            dump_mtime = Path(dump.zip_path).stat().st_mtime
            if latest_session_mtime > 0 and (latest_session_mtime - dump_mtime) > 60:
                dump_is_stale = True
        except OSError:
            pass

        report.crash_detected = True
        report.crash_time_str = dump.crash_time
        fmod_short = Path(dump.faulting_module).name if dump.faulting_module else "未知模組"
        stale_tag = " [前次舊紀錄，最新一局未閃退]" if dump_is_stale else ""
        report.crash_summary = (
            f"偵測到崩潰傾印檔（{dump.crash_time}{stale_tag}）：{dump.exception_name}，"
            f"故障位址：{fmod_short} + 0x{dump.faulting_offset:X}"
        )
        # 若崩潰位址直接落在某個第三方 .dll 插件內
        if fmod_short.lower() in dll_profiles:
            prof = dll_profiles[fmod_short.lower()]
            add_suspect(
                prof.mod,
                fmod_short,
                fmod_short,
                90,
                f"🔥 崩潰指令位址（RIP）直接位於此插件內部：{fmod_short} + 0x{dump.faulting_offset:X}",
            )

    # 2. 解析 RE_Kenshi_log.txt
    if re_log_path.is_file():
        try:
            re_lines = re_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            re_lines = []

        load_re = re.compile(r"^\s*[\d.]+\s+RE_Kenshi:\s+(.+?)\s+->\s+([^\s]+\.dll)\s*$")
        ts_re = re.compile(r"^(?:Error\s+)?([\d.]+)\s+([^:]+):\s*(.*)$")

        parsed_rows: list[tuple[float, str, str, str]] = []
        gui_exc_timestamps: list[float] = []
        for raw in re_lines:
            m_load = load_re.match(raw)
            if m_load:
                mod_name, dll_name = m_load.group(1).strip(), m_load.group(2).strip()
                report.re_kenshi_loaded_plugins.append((mod_name, dll_name))
                continue
            m_ts = ts_re.match(raw)
            if m_ts:
                ts_val = float(m_ts.group(1))
                actor = m_ts.group(2).strip()
                msg = m_ts.group(3).strip()
                parsed_rows.append((ts_val, actor, msg, raw))
                if any(w in msg for w in ("CRITICAL", "WARN:", "Failed to hook", "hook failed", "Could not add")):
                    if len(report.re_kenshi_warnings) < 15:
                        report.re_kenshi_warnings.append(raw.strip())
                if "engine GUI update raised exception" in msg or "getGUIData engine call raised exception" in msg:
                    report.crash_detected = True
                    report.gui_exceptions.append(raw.strip())
                    gui_exc_timestamps.append(ts_val)
                elif "[崩溃盾] 60s 汇总:" in msg and (
                    "通用致命异常=0 次" not in msg or "读档崩精确拦截=0" not in msg or "资源悬垂拦截=0" not in msg
                ):
                    report.crash_detected = True
                    report.gui_exceptions.append(raw.strip())
                    gui_exc_timestamps.append(ts_val)
                if "Crash detected" in msg or "probably crashing" in msg:
                    report.crash_detected = True
                    report.re_kenshi_crash_line = raw.strip()
                    if not report.crash_time_str:
                        report.crash_time_str = _fmt_mtime(re_log_path)

        if report.gui_exceptions:
            re_mtime = _fmt_mtime(re_log_path)
            if report.crash_summary:
                report.crash_summary = (
                    f"偵測到 GUI 介面異常攔截／僵屍視窗（{re_mtime}，共 {len(report.gui_exceptions)} 次）"
                    f" ｜ 另含前次崩潰傾印：{report.crash_summary}"
                )
            else:
                report.crash_summary = (
                    f"偵測到 GUI 介面更新異常被攔截（{re_mtime}）：引發「關不掉的 INVENTORY 僵屍視窗」或面板異常"
                )

        if parsed_rows:
            re_log_had_crash = bool(
                report.re_kenshi_crash_line
                or gui_exc_timestamps
                or (dump and dump.exception_code and not dump_is_stale)
            )
            # 若本局有明確 Crash 則看最後 30 秒；若為 GUI 異常攔截則看異常發生瞬間前 15 秒至後 5 秒
            if report.re_kenshi_crash_line:
                ref_ts = parsed_rows[-1][0]
                window_start = max(0.0, ref_ts - 30.0)
                window_end = ref_ts
            elif gui_exc_timestamps:
                ref_ts = gui_exc_timestamps[-1]
                window_start = max(0.0, ref_ts - 15.0)
                window_end = ref_ts + 5.0
            else:
                ref_ts = parsed_rows[-1][0]
                window_start = max(0.0, ref_ts - 30.0)
                window_end = ref_ts

            counts: Counter[str] = Counter()
            last_msg_map: dict[str, str] = {}
            very_last_actors: set[str] = set()
            for ts_val, actor, msg, _raw in parsed_rows:
                if actor == "RE_Kenshi":
                    continue
                if window_start <= ts_val <= window_end:
                    counts[actor] += 1
                    last_msg_map[actor] = f"[{ts_val:.1f}s] {msg[:110]}"
                if (ref_ts - 5.0) <= ts_val <= window_end:
                    very_last_actors.add(actor)

            for actor, cnt in counts.most_common(8):
                report.re_kenshi_recent_activity.append((actor, cnt, last_msg_map.get(actor, "")))
                if not re_log_had_crash:
                    continue
                mod_obj = resolve_mod(actor)
                dll_str = f"{actor}.dll" if f"{actor.lower()}.dll" in dll_profiles else ""
                if actor in very_last_actors:
                    add_suspect(
                        mod_obj,
                        actor,
                        dll_str,
                        45,
                        f"⏱ 在異常／當機瞬間前後 5 秒內密集運作（區間內共輸出 {cnt} 筆紀錄，最後紀錄：{last_msg_map.get(actor, '')}）",
                    )
                elif cnt >= 5:
                    add_suspect(
                        mod_obj,
                        actor,
                        dll_str,
                        25,
                        f"⏱ 在異常／當機前頻繁運作（共輸出 {cnt} 筆紀錄，最後紀錄：{last_msg_map.get(actor, '')}）",
                    )

    # 彙整當局實際載入記憶體的 DLL 清單（取自 RE_Kenshi_log.txt 與 CrashDump）
    loaded_dll_names: set[str] = {dll.lower() for _, dll in report.re_kenshi_loaded_plugins}
    if dump and dump.plugin_dlls:
        for p_dll in dump.plugin_dlls:
            loaded_dll_names.add(Path(p_dll).name.lower())

    def is_dll_active_and_loaded(dll_key: str, prof: _DllProfile) -> bool:
        """確認該插件所屬模組目前處於『已勾選啟用』狀態，且實際有在當局被載入記憶體。"""
        if prof.mod is not None and not prof.mod.active:
            return False
        if loaded_dll_names and dll_key.lower() not in loaded_dll_names:
            return False
        return True

    # 3. 解析 DesoCrash.log
    deso = _analyze_deso_crash(game_dir)
    report.deso_entry = deso

    # 判斷是否為 UI / 背包（MyGUI / 0x8A94A7）相關崩潰或 GUI 異常攔截
    is_ui_or_inventory_crash = bool(report.gui_exceptions)
    if dump and dump.faulting_offset in (0x8A94A7, 0x8AA668):
        is_ui_or_inventory_crash = True
    if dump and "mygui" in dump.faulting_module.lower():
        is_ui_or_inventory_crash = True
    if deso and ("MyGUIEngine" in deso.exception_line or "MyGUIEngine" in deso.stack_line or "8A94A7" in deso.exception_line):
        is_ui_or_inventory_crash = True

    # 若偵測到 DivineGraceUI 攔截到 engine GUI update raised exception（導致關不掉的 INVENTORY 僵屍視窗）
    if report.gui_exceptions:
        for dll_name, prof in dll_profiles.items():
            if not is_dll_active_and_loaded(dll_name, prof):
                continue
            if prof.hooks_inventory_lifecycle:
                add_suspect(
                    prof.mod,
                    prof.dll_path.stem,
                    prof.dll_path.name,
                    65,
                    f"🧟 僵屍視窗頭號元兇：此插件（{prof.dll_path.name}）同時攔截了背包視窗建立（createInventoryLayout）、物品拿取（InventorySection::removeItem）與視窗關閉解構子（~InventoryGUI）。搜刮物品後關閉視窗時極易引發 GUI 例外，導致視窗銷毀中斷而卡死在螢幕上關不掉！",
                )
            elif prof.hooks_inventory_transfer:
                add_suspect(
                    prof.mod,
                    prof.dll_path.stem,
                    prof.dll_path.name,
                    40,
                    f"🔄 物品轉移攔截：此插件（{prof.dll_path.name}）攔截了撿拾與新增物品事件（tryAddItem / _sectionAddItemCallback），在撿拾物品並瞬間關閉視窗時可能因合併或搬移物品引發 UI 指標異常",
                )
            elif dll_name == "divinegraceui.dll":
                add_suspect(
                    prof.mod,
                    prof.dll_path.stem,
                    prof.dll_path.name,
                    30,
                    "🛡 異常攔截者（非直接肇因）：DivineGraceUI.dll 攔截了 ForgottenGUI::update 並吞掉了上述背包插件引發的崩潰（紀錄：engine GUI update raised exception），雖保住遊戲未閃退，但導致關閉到一半的 INVENTORY 視窗變成無法關閉的孤兒視窗",
                )
        # 若當局 RE_Kenshi_log.txt 曾載入 SkeletonRebirth.dll，但玩家事後已刪除該模組資料夾
        for mod_label, loaded_dll in report.re_kenshi_loaded_plugins:
            if loaded_dll.lower() == "skeletonrebirth.dll" and "skeletonrebirth.dll" not in dll_profiles:
                add_suspect(
                    resolve_mod(mod_label),
                    f"{mod_label}（目前已從硬碟移除）",
                    loaded_dll,
                    65,
                    f"🧟 僵屍視窗頭號元兇：當局 Log 載入了『{loaded_dll}』，該插件攔截了背包視窗建立、搜刮拿取物品（removeItem）與視窗關閉解構子（~InventoryGUI），導致搜刮關閉視窗時拋出異常並留下關不掉的 INVENTORY 僵屍視窗（註：您目前已將此模組移除）",
                )

    # 4. 解析 MyGUI.log 並反查缺失貼圖所屬模組
    mygui_path = game_dir / "MyGUI.log"
    if mygui_path.is_file():
        try:
            mg_lines = mygui_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            mg_lines = []
        missing_tex: set[str] = set()
        for line in mg_lines:
            if re.search(r"\|\s*Error\s*\|", line):
                short_err = line.split("  |  C:\\")[0].strip()
                report.mygui_errors.append(short_err)
                m_tex = re.search(r"Texture '([^']+)' not found", line)
                if m_tex:
                    missing_tex.add(m_tex.group(1))
            elif re.search(r"\|\s*Warning\s*\|", line):
                report.mygui_warnings_count += 1

        # 只保留最後 10 筆 MyGUI Error
        report.mygui_errors = report.mygui_errors[-10:]

        # 反查是哪個 .dll 插件引用了該缺失貼圖（僅檢查已啟用且有載入的插件）
        for tex in sorted(missing_tex):
            tex_bytes = tex.encode("ascii", errors="ignore")
            owners: list[str] = []
            for dll_name, prof in dll_profiles.items():
                if not is_dll_active_and_loaded(dll_name, prof):
                    continue
                if tex_bytes and tex_bytes in prof.ascii_blob:
                    disp = prof.mod.ui_name(True) if prof.mod else dll_name
                    owners.append(f"{disp} ({prof.dll_path.name})")
                    add_suspect(
                        prof.mod,
                        disp,
                        prof.dll_path.name,
                        40,
                        f"🖼 MyGUI.log 報錯找不到貼圖 '{tex}'，經二進位反查確認由『{prof.dll_path.name}』所呼叫（非外部 AI 誤稱的 ItemMarkers）",
                    )
            if owners:
                report.missing_textures_owners[tex] = owners

    # 若為 UI / 背包空指標崩潰，將所有「已勾選啟用且當局實際載入」並攔截 InventoryIcon / InventoryGUI / Inventory 的插件列入嫌疑
    if is_ui_or_inventory_crash or report.mygui_errors:
        for dll_name, prof in dll_profiles.items():
            if not is_dll_active_and_loaded(dll_name, prof):
                continue
            if prof.hooks_inventory_icon:
                add_suspect(
                    prof.mod,
                    prof.dll_path.stem,
                    prof.dll_path.name,
                    55,
                    f"🎒 此插件（{prof.dll_path.name}）直接攔截了背包物品格圖示建構子（InventoryIcon::_CONSTRUCTOR），在按 I 開啟背包繪製物品標記時極易因指標異常引發 UI 閃退",
                )
            elif prof.hooks_inventory_gui:
                add_suspect(
                    prof.mod,
                    prof.dll_path.stem,
                    prof.dll_path.name,
                    40,
                    f"🎒 此插件（{prof.dll_path.name}）直接攔截了背包視窗介面（InventoryGUI / InventoryLayout），開啟或更新背包視窗時會介入渲染",
                )
            elif prof.hooks_inventory_data and dll_name in ("medkitmerge.dll", "kenshiqol.dll", "kenshiaffixes.dll"):
                add_suspect(
                    prof.mod,
                    prof.dll_path.stem,
                    prof.dll_path.name,
                    35,
                    f"🎒 此插件（{prof.dll_path.name}）攔截了背包物品欄資料與事件（Inventory / Item），若在開啟背包瞬間合併或修改物品可能導致 UI 讀取到空指標",
                )

    # 5. 解析 kenshi_info.log 與 kenshi.log
    info_path = game_dir / "kenshi_info.log"
    if info_path.is_file():
        try:
            info_lines = info_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            info_lines = []
        mesh_counter: Counter[str] = Counter()
        for line in info_lines:
            if "Loaded mesh doesn't exist:" in line:
                report.missing_meshes_total += 1
                m_name = line.split("Loaded mesh doesn't exist:", 1)[1].strip()
                mesh_counter[m_name] += 1
            elif "[warning]:" in line or "[error]:" in line:
                if " multiple uv sets" not in line:
                    msg = re.sub(r"^\{[^}]+\}\s*[\d\-:\s]+", "", line).strip()
                    if msg not in report.kenshi_info_warnings and len(report.kenshi_info_warnings) < 12:
                        report.kenshi_info_warnings.append(msg)
                        # 檢查是否提及特定 .mod 檔案
                        m_mod = re.search(r"([A-Za-z0-9_\-\s]+\.mod)", msg)
                        if m_mod:
                            mod_ref = m_mod.group(1).strip()
                            target_mod = resolve_mod(mod_ref)
                            if target_mod and target_mod.active:
                                add_suspect(
                                    target_mod,
                                    mod_ref,
                                    "",
                                    15,
                                    f"⚠ kenshi_info.log 紀錄警告：{msg}",
                                )
        report.missing_meshes = [f"{k}（{v} 次）" for k, v in mesh_counter.most_common(8)]

    if klog_path.is_file():
        try:
            size = klog_path.stat().st_size
            with open(klog_path, "rb") as f:
                if size > 65536:
                    f.seek(size - 65536)
                klines = f.read().decode("utf-8", errors="replace").splitlines()
        except OSError:
            klines = []
        res_lines = [
            l.strip() for l in klines
            if any(k in l for k in ("Mesh: Loading ", "Texture: ", "Skeleton: Loading ", "Created Morph ", "Error", "Exception"))
        ]
        report.last_loaded_resources = res_lines[-8:]

    # 6. 解析 Havok.log
    havok_path = game_dir / "Havok.log"
    if havok_path.is_file():
        try:
            hlines = havok_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            hlines = []
        for l in hlines:
            if "Error" in l or "error" in l or "Invalid connection" in l or "missing connections" in l:
                report.havok_errors_count += 1
                if len(report.havok_samples) < 5:
                    report.havok_samples.append(l.strip())

    # 整理並排序可疑模組
    suspects = sorted(suspect_map.values(), key=lambda s: s.score, reverse=True)
    for s in suspects:
        if s.score >= 60:
            s.level = "HIGH"
        elif s.score >= 35:
            s.level = "MEDIUM"
        else:
            s.level = "LOW"
    report.suspects = suspects[:10]

    if not report.crash_summary:
        if report.crash_detected:
            report.crash_summary = f"在 RE_Kenshi_log.txt 偵測到遊戲當機紀錄（{report.crash_time_str}）。"
        else:
            report.crash_summary = "近期 Log 中未偵測到明確的當機傾印，以下為最新執行的診斷記錄。"

    top_names = "、".join(f"『{s.name}』" for s in report.suspects[:3]) if report.suspects else "上方可疑插件"

    # 產生具體排查建議
    if dump_is_stale:
        report.recommendations.append(
            f"【舊 CrashDump 提醒】目前偵測到的『{Path(dump.zip_path).name}』（{dump.crash_time}）是前次遊戲留下的舊崩潰傾印檔，"
            "而您最新一局遊戲並未發生閃退。建議點擊右上角「🗑 清理遊戲 Log」將舊傾印檔清除，避免舊紀錄干擾後續診斷。"
        )
    if report.gui_exceptions:
        report.recommendations.append(
            "【關不掉的 INVENTORY 僵屍視窗／搜刮視窗異常排查】Log 記錄到『engine GUI update raised exception』！"
            f"這是因為在撿拾物品並關閉視窗時，背包相關插件（目前啟用名單中以 {top_names} 嫌疑最高）在更新或解構視窗時引發記憶體異常，"
            "並被『絕境系統（DivineGraceUI.dll）』的防崩潰機制攔截，導致該視窗殘留在畫面上。"
            "👉 解決方式：(1) 當下請先存檔並「完全退出遊戲重開」以清除殘留視窗；(2) 可優先測試暫時停用上方排行前幾名的背包相關插件。"
        )
    if is_ui_or_inventory_crash:
        report.recommendations.append(
            "【背包／UI 閃退排查】偵測到介面渲染或開啟背包瞬間發生空指標異常（0xC0000005）。"
            f"在您目前有勾選啟用且載入記憶體的模組中，建議優先點擊上方排行中的 {top_names}，"
            "在主清單中暫時取消勾選並按「💾 儲存模組順序」，再進遊戲按 I 鍵或搜刮物品測試是否恢復正常。"
        )
    if report.missing_textures_owners:
        for tex, owners in report.missing_textures_owners.items():
            report.recommendations.append(
                f"【缺失貼圖真相】MyGUI.log 報錯的 Texture '{tex}' not found，實際上是由 {', '.join(owners)} 呼叫的預設退回貼圖（並非不存在的 ItemMarkers 模組）。"
            )
    if report.havok_errors_count > 0:
        report.recommendations.append(
            f"【導航網格修復】Havok.log 中有 {report.havok_errors_count} 筆分區網格連接錯誤，若在移動或開背包卡頓時容易閃退，"
            "建議在遊戲內按 Ctrl + Shift + F11 重建導航網格並手動存檔，或在主選單使用「匯入遊戲（Import Game）」。"
        )
    if not report.recommendations:
        report.recommendations.append(
            "【二分法排查建議】建議優先從上方「🎯 可疑模組排行榜」得分最高的 RE_Kenshi 插件（.dll）開始暫時停用測試，"
            "並確保漢化模組與 UI 模組（如 Dark UI）維持在適當順序。"
        )

    report.elapsed_sec = time.perf_counter() - t0
    return report


def format_report_text(report: CrashAnalysisReport) -> str:
    """將分析報告格式化為結構化純文字（供顯示與一鍵複製）。"""
    lines: list[str] = []
    lines.append("══════════════════════════════════════════════════════════════")
    lines.append("                🩺 Kenshi 當機與 Log 深度診斷報告")
    lines.append("══════════════════════════════════════════════════════════════")
    lines.append(f"分析時間：{report.analyzed_at}（耗時 {report.elapsed_sec:.2f} 秒）")
    lines.append(f"遊戲路徑：{report.game_path}")
    lines.append(f"診斷結論：{report.crash_summary}")
    lines.append("")

    # 1. 可疑模組排行榜
    lines.append("──────────────────────────────────────────────────────────────")
    lines.append("🎯 一、可疑模組排行榜（依據真實檔案反查與當機瞬間紀錄評分）")
    lines.append("──────────────────────────────────────────────────────────────")
    if not report.suspects:
        lines.append("  （未偵測到明顯異常的可疑模組）")
    else:
        badge_map = {"HIGH": "🔴 [高度懷疑]", "MEDIUM": "🟠 [中度懷疑]", "LOW": "🟡 [低度關聯]"}
        for idx, s in enumerate(report.suspects, 1):
            badge = badge_map.get(s.level, "🟡")
            steam_info = f" [Steam ID: {s.mod.id}]" if (s.mod and s.mod.id) else ""
            dll_info = f" ({s.dll_name})" if s.dll_name else ""
            lines.append(f"{idx}. {badge} {s.name}{dll_info}{steam_info}  （風險指數：{s.score}）")
            for r in s.reasons:
                lines.append(f"   └─ {r}")
    lines.append("")

    # 2. 具體修復與排查建議
    lines.append("──────────────────────────────────────────────────────────────")
    lines.append("🛠 二、具體排查與修復建議")
    lines.append("──────────────────────────────────────────────────────────────")
    for idx, rec in enumerate(report.recommendations, 1):
        lines.append(f"{idx}. {rec}")
    lines.append("")

    # 3. 硬體崩潰傾印與 DesoCrash 現場
    lines.append("──────────────────────────────────────────────────────────────")
    lines.append("💥 三、Crash Dump 記憶體傾印與崩潰現場紀錄")
    lines.append("──────────────────────────────────────────────────────────────")
    if report.dump and report.dump.exception_code:
        d = report.dump
        lines.append(f"• 傾印檔案：{Path(d.zip_path).name} -> {d.dmp_name}（時間：{d.crash_time}）")
        lines.append(f"• 異常代碼：0x{d.exception_code:08X} — {d.exception_name}")
        lines.append(f"• 故障位址：0x{d.exception_address:016X}（{Path(d.faulting_module).name} + 0x{d.faulting_offset:X}）")
        if d.plugin_dlls:
            dll_names = ", ".join(Path(p).name for p in d.plugin_dlls)
            lines.append(f"• 當下掛載於記憶體的插件 DLL（{len(d.plugin_dlls)} 個）：{dll_names}")
    else:
        lines.append("• 未發現 crashDump*.zip 或無異常碼紀錄。")

    if report.deso_entry:
        de = report.deso_entry
        lines.append(f"• DesoCrash 最新崩潰現場（{de.source_file}）：{de.header}")
        if de.exception_line:
            lines.append(f"  - {de.exception_line}")
        if de.last_hook:
            lines.append(f"  - 最後進入的鉤子：{de.last_hook}")
        if de.access_line:
            lines.append(f"  - {de.access_line}")
        if de.stack_line:
            lines.append(f"  - {de.stack_line[:160]}...")
    lines.append("")

    # 4. RE_Kenshi_log.txt 當機前活動
    lines.append("──────────────────────────────────────────────────────────────")
    lines.append("🔌 四、RE_Kenshi 插件異常攔截與當機前活動統計")
    lines.append("──────────────────────────────────────────────────────────────")
    if report.re_kenshi_crash_line:
        lines.append(f"• 崩潰偵測紀錄：{report.re_kenshi_crash_line}")
    if report.gui_exceptions:
        lines.append(f"• 🔴 偵測到 GUI 介面更新異常被攔截（共 {len(report.gui_exceptions)} 筆，易導致視窗卡死關不掉）：")
        for gexc in report.gui_exceptions[-5:]:
            lines.append(f"  👉 {gexc}")
    if report.re_kenshi_recent_activity:
        for actor, cnt, last_msg in report.re_kenshi_recent_activity:
            lines.append(f"• {actor}：異常／當機區間輸出 {cnt} 筆紀錄 ｜ 最後訊息：{last_msg}")
    else:
        lines.append("• 無 RE_Kenshi 當機前插件活動紀錄。")
    if report.re_kenshi_warnings:
        lines.append("• 插件啟動警告／異常摘錄：")
        for w in report.re_kenshi_warnings[:6]:
            lines.append(f"  - {w}")
    lines.append("")

    # 5. MyGUI.log / kenshi_info.log / kenshi.log
    lines.append("──────────────────────────────────────────────────────────────")
    lines.append("📋 五、MyGUI 介面、模型資源與引擎 Log 關鍵證據")
    lines.append("──────────────────────────────────────────────────────────────")
    if report.mygui_errors:
        lines.append(f"• MyGUI.log 最新錯誤（共擷取 {len(report.mygui_errors)} 筆，另有版面 Warning {report.mygui_warnings_count} 筆）：")
        for err in report.mygui_errors[-5:]:
            lines.append(f"  - {err}")
        for tex, owners in report.missing_textures_owners.items():
            lines.append(f"  👉 貼圖 '{tex}' 真實呼叫來源：{', '.join(owners)}")
    else:
        lines.append(f"• MyGUI.log：無 Error 紀錄（版面 Warning 共 {report.mygui_warnings_count} 筆）。")

    if report.kenshi_info_warnings:
        lines.append("• kenshi_info.log 模組與地圖警告：")
        for w in report.kenshi_info_warnings[:8]:
            lines.append(f"  - {w}")

    if report.missing_meshes_total:
        lines.append(f"• 缺失遠景／網格模型（Loaded mesh doesn't exist）：共 {report.missing_meshes_total} 次（如 {', '.join(report.missing_meshes[:5])}）")

    if report.last_loaded_resources:
        lines.append("• kenshi.log 當機前最後載入的 3D 模型與貼圖：")
        for r in report.last_loaded_resources[-5:]:
            lines.append(f"  - {r}")

    if report.havok_errors_count:
        lines.append(f"• Havok.log 導航網格異常：共 {report.havok_errors_count} 筆")
        for h in report.havok_samples[:3]:
            lines.append(f"  - {h}")

    return "\n".join(lines)


def format_bytes(num_bytes: int) -> str:
    """將位元組數格式化為易讀字串（KB / MB / GB）。"""
    if num_bytes >= 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 ** 3):.2f} GB"
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 ** 2):.2f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes} B"


_ROOT_LOG_TXT_NAMES: set[str] = {
    "re_kenshi_log.txt",
    "rangeddefence_log.txt",
    "fileiolog.txt",
}


def scan_game_logs(game_path: str | Path) -> list[Path]:
    """掃描 Kenshi 遊戲目錄中所有可安全清除的 Log 與 CrashDump 檔案（嚴格排除 changelog.txt 等說明檔）。"""
    game_dir = Path(game_path) if game_path else Path()
    if not game_dir.is_dir():
        return []

    found: dict[str, Path] = {}

    def _add(p: Path) -> None:
        try:
            if p.is_file():
                found[str(p.resolve()).lower()] = p
        except OSError:
            pass

    # 1. 遊戲根目錄：所有 *.log、*.log.*、crashDump*.zip、*.dmp，以及特定外掛 *_log.txt
    try:
        for item in game_dir.iterdir():
            if not item.is_file():
                continue
            lname = item.name.lower()
            if lname == "changelog.txt":
                continue
            if (
                lname.endswith(".log")
                or ".log." in lname
                or lname.startswith("crashdump")
                or lname.endswith(".dmp")
                or lname in _ROOT_LOG_TXT_NAMES
            ):
                _add(item)
    except OSError:
        pass

    # 2. RE_Kenshi 子目錄：DesoCrash.log*、*.log、crash_dumps/*.dmp
    re_dir = game_dir / "RE_Kenshi"
    if re_dir.is_dir():
        try:
            for item in re_dir.iterdir():
                if not item.is_file():
                    continue
                lname = item.name.lower()
                if lname.startswith("desocrash.log") or lname.endswith(".log") or ".log." in lname or lname.endswith(".dmp"):
                    _add(item)
            cd_dir = re_dir / "crash_dumps"
            if cd_dir.is_dir():
                for item in cd_dir.iterdir():
                    if item.is_file() and (item.name.lower().endswith(".dmp") or item.name.lower().endswith(".log")):
                        _add(item)
        except OSError:
            pass

    # 3. 遊戲目錄下的 logs/ 子目錄：*.log
    logs_dir = game_dir / "logs"
    if logs_dir.is_dir():
        try:
            for item in logs_dir.iterdir():
                if item.is_file() and (item.name.lower().endswith(".log") or ".log." in item.name.lower()):
                    _add(item)
        except OSError:
            pass

    return sorted(found.values(), key=lambda p: str(p).lower())


def clean_game_logs(game_path: str | Path) -> tuple[int, int, list[str]]:
    """清除遊戲目錄下所有累積的 Log 與 CrashDump 檔案。
    回傳 (成功處理檔案數, 釋放位元組數, 失敗錯誤清單)。
    """
    targets = scan_game_logs(game_path)
    removed_count = 0
    freed_bytes = 0
    errors: list[str] = []

    for p in targets:
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        try:
            os.chmod(p, stat.S_IWRITE)
        except OSError:
            pass
        try:
            p.unlink()
            removed_count += 1
            freed_bytes += size
        except OSError as exc:
            # 若檔案正被執行中的遊戲鎖定無法 unlink，嘗試將其截斷清空為 0 bytes
            try:
                with open(p, "w", encoding="utf-8"):
                    pass
                removed_count += 1
                freed_bytes += size
            except OSError:
                errors.append(f"{p.name}: {exc}")

    return removed_count, freed_bytes, errors

