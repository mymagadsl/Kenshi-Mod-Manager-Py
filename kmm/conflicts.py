"""模組衝突檢查器（對應 C# Core/Kenshi_Data/ConflictManager.cs）。

依載入順序（order 由小到大）掃描所有已啟用模組，
當兩個以上的模組修改了同一個遊戲物件（string_id）的同一個屬性/參照時，
即記錄為一筆衝突，並依載入順序排列各模組設定的值（最後一個未移除者為最終生效值）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import difflib
import re
from typing import Any, Callable, Iterable

from .game_data import parse_mod_file
from .models import Mod

# 匹配模組名稱尾端的漢化標記（如 CN, CHN, TW, CHT, CHS, ZH_CN, 漢化, 繁中, 中文版 等）
_TRANS_SUFFIX_RE = re.compile(
    r"(?:^|[\s_\-\[\(【]+)"
    r"(?:zh[\s_\-]*(?:cn|tw|hk)|cht|chs|chn|cn|tw|tc|sc|"
    r"traditional[\s_\-]*chinese|simplified[\s_\-]*chinese|chinese|translation|"
    r"漢化|汉化|繁中|簡中|简中|中文|中文化|翻譯|翻译)"
    r"(?:[\s_\-]*patch|[\s_\-]*mod|[\s_\-]*版|[\s_\-]*補丁|[\s_\-]*补丁)?"
    r"[\]\)\s】]*$",
    re.IGNORECASE,
)

# 匹配模組名稱開頭的漢化前綴（如 [漢化] xxx、【繁中】xxx）
_TRANS_PREFIX_RE = re.compile(
    r"^[\s\[\(【]*(?:漢化|汉化|繁中|簡中|简中|中文|中文化|翻譯|翻译|cht|chs|chn|zh[\s_\-]*(?:cn|tw))"
    r"[\]\)】\s_\-:：]+",
    re.IGNORECASE,
)

# 名稱任意位置包含明確的中文漢化詞彙
_TRANS_KEYWORD_RE = re.compile(
    r"(?:漢化|汉化|繁中版?|簡中版?|简中版?|中文化|中文版|翻譯補丁|翻译补丁)",
    re.IGNORECASE,
)


def _norm_mod_name(name: str) -> str:
    """正規化模組名稱：移除空白、底線、連字號與括號並轉小寫，用於比對名稱相似度。"""
    return re.sub(r"[\s_\-\[\]\(\)【】]+", "", name).lower()


def extract_translation_base_name(display_name: str) -> str | None:
    """由模組顯示名稱判斷是否為漢化模組，若是則回傳去除漢化標記後的原版基底名稱（全域漢化回傳空字串），否則回傳 None。"""
    dn = display_name.strip()
    if not dn:
        return None

    m_suf = _TRANS_SUFFIX_RE.search(dn)
    if m_suf:
        return dn[:m_suf.start()].strip(" _-[]()【】")

    m_pre = _TRANS_PREFIX_RE.search(dn)
    if m_pre:
        return dn[m_pre.end():].strip(" _-[]()【】")

    m_kw = _TRANS_KEYWORD_RE.search(dn)
    if m_kw:
        cleaned = (dn[:m_kw.start()] + " " + dn[m_kw.end():]).strip(" _-[]()【】")
        return cleaned

    return None


def is_translation_mod(mod: Mod) -> bool:
    """自動判斷模組是否為漢化/翻譯模組（依據名稱規則或 Translation 分類標籤）。"""
    if not mod.has_extension:
        return False
    if extract_translation_base_name(mod.display_name) is not None:
        return True
    return any(c.lower() == "translation" for c in mod.categories)


def detect_translation_map(mods: Iterable[Mod], fuzzy_threshold: float = 0.85) -> dict[str, list[str]]:
    """自動辨識清單中的所有漢化模組，並配對其對應的原版模組檔名清單。

    回傳字典：{漢化模組 file_name: [對應原版模組 file_name, ...]}
    若對應清單為空，代表該模組為全域漢化或獨立漢化包（如 TraditionalChinese.mod、zh_TW.mod）。
    """
    valid_mods = [m for m in mods if m.has_extension]
    trans_flags = {m.file_name: is_translation_mod(m) for m in valid_mods}
    by_filename = {m.file_name.lower(): m.file_name for m in valid_mods}

    result: dict[str, list[str]] = {}
    for m in valid_mods:
        if not trans_flags.get(m.file_name):
            continue

        targets: list[str] = []
        # 1. 由名稱去除漢化詞綴後自動比對（支援拼字微幅差異的模糊匹配，如 ChineseAcientWeapon <-> ChineseAncientWeapon CHN）
        base_stem = extract_translation_base_name(m.display_name)
        if base_stem:
            nb = _norm_mod_name(base_stem)
            if nb:
                best_candidates: list[tuple[float, str]] = []
                for other in valid_mods:
                    if other is m or trans_flags.get(other.file_name):
                        continue
                    no = _norm_mod_name(other.display_name)
                    if not no:
                        continue
                    if no == nb:
                        best_candidates.append((1.0, other.file_name))
                    elif len(nb) >= 4:
                        ratio = difflib.SequenceMatcher(None, nb, no).ratio()
                        if ratio >= fuzzy_threshold:
                            best_candidates.append((ratio, other.file_name))
                best_candidates.sort(key=lambda x: x[0], reverse=True)
                for _, fname in best_candidates:
                    if fname not in targets:
                        targets.append(fname)

        # 2. 由模組相依性與參照自動關聯
        for dep in m.all_dependencies:
            actual = by_filename.get(dep.lower(), dep)
            if actual != m.file_name and actual not in targets:
                targets.append(actual)

        result[m.file_name] = targets

    return result


# 匹配補丁／修正／擴充關鍵字（使用單字邊界，避免將 KenshiAffixes 誤判為 fix）
_PATCH_KW_RE = re.compile(
    r"(?:^|[\s_\-\[\(【]+)"
    r"(?:bug[\s_\-]*fix(?:es)?|hot[\s_\-]*fix(?:es)?|fix(?:es)?|patch(?:es)?|"
    r"add[\s_\-]*on|sub[\s_\-]*mod|playable|compat(?:ibility)?|"
    r"補丁|补丁|修正|修復|修复|擴充|扩展|可玩|相容|兼容|附屬|附属)"
    r"(?:$|[\s_\-\]\)】]+)",
    re.IGNORECASE,
)


def detect_patch_map(
    mods: Iterable[Mod],
    trans_map: dict[str, list[str]] | None = None,
    fuzzy_threshold: float = 0.82,
) -> dict[str, list[str]]:
    """自動辨識清單中的補丁／修正／擴充模組（fix / patch / add-on / playable 等），並配對其對應的主模組。

    回傳字典：{補丁模組 file_name: [對應主模組 file_name, ...]}
    已歸類為漢化模組者不會重複列入；若無對應主模組（例如針對原版遊戲的獨立模組 Particle fix）則不列入。
    """
    all_mods = [m for m in mods if m.has_extension]
    if trans_map is None:
        trans_map = detect_translation_map(all_mods)

    valid_mods = [m for m in all_mods if m.file_name not in trans_map]
    by_filename = {m.file_name.lower(): m.file_name for m in valid_mods}

    result: dict[str, list[str]] = {}
    for m in valid_mods:
        targets: list[str] = []

        # 1. 由模組檔頭宣告的相依性／參照自動關聯主模組
        for dep in m.all_dependencies:
            actual = by_filename.get(dep.lower(), dep)
            if actual != m.file_name and actual not in trans_map and actual not in targets:
                targets.append(actual)

        # 2. 由模組名稱中的補丁／擴充關鍵字（fix / patch / add-on / playable 等）自動比對主模組名稱
        dn = m.display_name.strip()
        kw_match = _PATCH_KW_RE.search(dn)
        if kw_match:
            stem = dn[:kw_match.start()].strip(" _-[]()【】")
            parts = [p for p in re.split(r"[\s_\-]+", stem) if p]
            candidate_stems = [stem] if stem else []
            for k in range(len(parts) - 1, 0, -1):
                candidate_stems.append("".join(parts[:k]))

            best_candidates: list[tuple[float, str]] = []
            for cs in candidate_stems:
                ncs = _norm_mod_name(cs)
                if len(ncs) < 4:
                    continue
                for other in valid_mods:
                    if other is m:
                        continue
                    no = _norm_mod_name(other.display_name)
                    if not no:
                        continue
                    if no == ncs:
                        best_candidates.append((1.0, other.file_name))
                    elif len(ncs) >= 6 and no.startswith(ncs):
                        best_candidates.append((0.9, other.file_name))
                    else:
                        ratio = difflib.SequenceMatcher(None, ncs, no).ratio()
                        if ratio >= fuzzy_threshold:
                            best_candidates.append((ratio, other.file_name))

            best_candidates.sort(key=lambda x: x[0], reverse=True)
            for _, fname in best_candidates:
                if fname not in targets:
                    targets.append(fname)

        if targets:
            result[m.file_name] = targets

    return result


@dataclass
class ConflictChange:
    mod_name: str
    state: str   # "OWNED" | "MODIFIED" | "REMOVED"
    value: Any


@dataclass
class ConflictDetail:
    key: str
    string_id: str
    item_type: str
    item_name: str
    property_key: str
    changes: list[ConflictChange] = field(default_factory=list)

    @property
    def winning_index(self) -> int:
        """回傳最終生效的變更索引（最後一個非 REMOVED 的項目）。"""
        for i in range(len(self.changes) - 1, -1, -1):
            if self.changes[i].state != "REMOVED" and self.changes[i].value != "REMOVED":
                return i
        return len(self.changes) - 1


ProgressCallback = Callable[[int, int, str], None]


def analyze_conflicts(
    mods: list[Mod],
    progress_cb: ProgressCallback | None = None,
    *,
    ignore_translations: bool = True,
    ignore_patches: bool = True,
) -> dict[str, ConflictDetail]:
    """分析所有已啟用模組之間的衝突，更新每個 Mod.conflicts 並回傳衝突索引字典。

    - ignore_translations=True（預設）：自動辨識漢化模組並排除其覆寫造成的衝突。
    - ignore_patches=True（預設）：自動辨識補丁／修正／擴充模組，排除其對主模組的正常覆寫衝突。
    """
    for m in mods:
        m.conflicts.clear()

    active_mods = sorted((m for m in mods if m.active and m.has_extension), key=lambda m: m.order)
    trans_map = detect_translation_map(mods) if (ignore_translations or ignore_patches) else {}
    patch_map = detect_patch_map(mods, trans_map) if ignore_patches else {}

    if ignore_translations:
        scan_mods = [m for m in active_mods if m.file_name not in trans_map]
    else:
        scan_mods = active_mods

    total = len(scan_mods)
    if total < 2:
        return {}

    all_changes: dict[str, ConflictDetail] = {}

    for idx, mod in enumerate(scan_mods, start=1):
        if progress_cb:
            progress_cb(idx, total, mod.display_name)
        items = parse_mod_file(mod.file_path)
        mod_name = mod.file_name
        for item in items:
            # 若整個物件被標記為 REMOVED 且沒有個別屬性，也記錄一筆 "[物件狀態]"
            prop_items = list(item.values.items())
            if item.state == "REMOVED" and not prop_items:
                prop_items.append(("[物件狀態]", "REMOVED"))

            for prop_key, val in prop_items:
                ckey = f"{item.string_id}::{prop_key}"
                detail = all_changes.get(ckey)
                if detail is None:
                    detail = ConflictDetail(
                        key=ckey,
                        string_id=item.string_id,
                        item_type=item.type_label,
                        item_name=item.name or item.string_id,
                        property_key=prop_key,
                    )
                    all_changes[ckey] = detail
                elif item.name and (not detail.item_name or detail.item_name == detail.string_id):
                    detail.item_name = item.name

                state = "REMOVED" if (item.state == "REMOVED" or val == "REMOVED") else item.state
                # 同一模組對同一鍵只保留最後一筆
                if detail.changes and detail.changes[-1].mod_name == mod_name:
                    detail.changes[-1] = ConflictChange(mod_name=mod_name, state=state, value=val)
                else:
                    detail.changes.append(ConflictChange(mod_name=mod_name, state=state, value=val))

    conflicts: dict[str, ConflictDetail] = {}
    for k, d in all_changes.items():
        if len(d.changes) <= 1:
            continue
        if ignore_patches and patch_map:
            # 若某主模組在同一屬性上被其專屬補丁／擴充模組覆寫，視為正常的主從覆蓋，將被取代的主模組從衝突對立面移除
            superseded_bases: set[str] = set()
            for ch in d.changes:
                for target_base in patch_map.get(ch.mod_name, ()):
                    superseded_bases.add(target_base)
            if superseded_bases:
                effective = [ch for ch in d.changes if ch.mod_name not in superseded_bases]
                if len(effective) <= 1:
                    continue
        conflicts[k] = d

    by_filename = {m.file_name: m for m in active_mods}
    for ckey, detail in conflicts.items():
        for ch in detail.changes:
            m = by_filename.get(ch.mod_name)
            if m is not None and ckey not in m.conflicts:
                m.conflicts.append(ckey)

    return conflicts
