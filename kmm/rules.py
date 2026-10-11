"""Masterlist 下載與自動排序（對應 C# Core/RuleService.cs）。"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from . import conflicts, constants, logging_util
from .config import KenshiToolConfig
from .models import Mod, Rule

_UA = {"User-Agent": "kmm-tool-py"}


def _get(url: str, timeout: float = 10) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_latest_version(cfg: KenshiToolConfig) -> str:
    try:
        data = json.loads(_get(f"https://api.github.com/repos/{cfg.MasterlistSource}/releases/latest"))
        return data.get("tag_name") or ""
    except Exception as exc:  # 網路錯誤不影響主程式
        logging_util.write(constants.ERROR_FILE, "無法檢查 masterlist 最新版本。")
        logging_util.write_exception(constants.ERROR_FILE, exc)
        return ""


def update_master_file(cfg: KenshiToolConfig) -> str:
    try:
        url = (f"https://raw.githubusercontent.com/{cfg.MasterlistSource}/"
               f"{cfg.MasterlistVersion}/masterlist.json")
        content = _get(url).decode("utf-8-sig")
        json.loads(content)  # 確認格式正確才寫入
        constants.MASTERLIST_FILE.write_text(content, encoding="utf-8")
        return content
    except Exception as exc:
        logging_util.write(constants.ERROR_FILE, "無法更新 masterlist。")
        logging_util.write_exception(constants.ERROR_FILE, exc)
        return ""


def check_masterlist_update(cfg: KenshiToolConfig) -> bool:
    """有新版時下載並回傳 True。"""
    version = get_latest_version(cfg)
    if version and version != cfg.MasterlistVersion:
        cfg.MasterlistVersion = version
        return bool(update_master_file(cfg))
    return False


def _parse_rules(raw: list[dict]) -> list[Rule]:
    rules = [Rule(order=int(r.get("Order", 0)), name=r.get("Name", ""), mods=list(r.get("Mod") or []))
             for r in raw]
    rules.sort(key=lambda r: r.order)
    if not any(r.order == constants.DEFAULT_RULE_ORDER for r in rules):
        rules.append(Rule(order=constants.DEFAULT_RULE_ORDER, name="Priority (Custom)", mods=[]))
    return rules


def get_rules(path: Path = constants.MASTERLIST_FILE) -> list[Rule]:
    for source in (path, constants.BASE_RULES_FILE):
        try:
            if source.is_file():
                return _parse_rules(json.loads(source.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError) as exc:
            logging_util.write(constants.ERROR_FILE, f"規則檔格式錯誤：{source}")
            logging_util.write_exception(constants.ERROR_FILE, exc)
    return _parse_rules([])


# 依據 Steam 工作坊標籤對應至 base_rules.json 的 Order 區段（參考 PR #1605 並依標籤權重決定優先度）
_CATEGORY_PRIORITY: list[tuple[tuple[str, ...], int]] = [
    (("total overhaul",), 7),
    (("animations", "animation"), 1),
    (("buildings",), 5),
    (("clothing/armour", "items/weapons", "armor", "weapons", "armour"), 6),
    (("factions",), 4),
    (("races",), 2),
    (("characters",), 3),
    (("gui", "ui", "graphical", "environment/map"), 0),
    (("economy",), 9),
    (("patches", "patch"), 8),
    (("gameplay", "research", "re_kenshi", "cheats"), 7),
]


def classify_by_category(mod: Mod) -> int | None:
    """根據模組的 Steam 工作坊分類標籤，回傳建議的 Rule Order（0~9）；無對應時回傳 None。"""
    if not mod.categories:
        return None
    cats = {c.strip().lower() for c in mod.categories if c.strip()}
    for keywords, target_order in _CATEGORY_PRIORITY:
        if any(k in cats for k in keywords):
            return target_order
    return None


def _ensure_rule_order(rules: list[Rule], order: int) -> Rule:
    for r in rules:
        if r.order == order:
            return r
    new_rule = Rule(order=order, name=f"Category-{order}", mods=[])
    rules.append(new_rule)
    rules.sort(key=lambda r: r.order)
    return new_rule


def _renumber(ordered: list[Mod]) -> None:
    for i, m in enumerate(ordered):
        m.order = i


def order_mods(mods: list[Mod], rules: list[Rule] | None = None) -> list[Mod]:
    """依規則分組、工作坊分類標籤、相依關係，以及補丁／漢化自動跟隨進行智慧排序。

    每次都使用全新的規則清單，避免原版靜態 ruleList 重複執行時殘留資料。
    回傳的清單已依新順序排列，並寫回每個模組的 order。
    停用的模組也會一起排序（與原版相同），但只有啟用的會寫入 mods.cfg。
    """
    rules = list(rules) if rules is not None else get_rules()
    if not any(r.order == constants.DEFAULT_RULE_ORDER for r in rules):
        rules.append(Rule(order=constants.DEFAULT_RULE_ORDER, name="Priority (Custom)", mods=[]))
    rules.sort(key=lambda r: r.order)
    for r in rules:
        r.mods_ordered = []
    for m in mods:
        m.ordered_automatically = False

    trans_map = conflicts.detect_translation_map(mods)
    patch_map = conflicts.detect_patch_map(mods, trans_map)
    masterlist_matched: set[str] = set()

    # 1. 依 masterlist 規則分組：同一模組命中多條規則時，以較後面（order 較大）的規則為準
    for rule in rules:
        for pattern in rule.mods:
            mod = next((m for m in mods if pattern in m.file_name), None)
            if mod is None:
                continue
            mod.ordered_automatically = True
            masterlist_matched.add(mod.file_name)
            for earlier in rules:
                if earlier.order < rule.order and mod in earlier.mods_ordered:
                    earlier.mods_ordered.remove(mod)
            if mod not in rule.mods_ordered:
                rule.mods_ordered.append(mod)

    # 1b. 未命中 masterlist 的一般模組，依 Steam 分類標籤智慧歸類（漢化與已配對補丁留待後續自動跟隨）
    for mod in mods:
        if mod.ordered_automatically:
            continue
        if mod.file_name in trans_map or mod.file_name in patch_map:
            continue
        cat_order = classify_by_category(mod)
        if cat_order is not None:
            target_rule = _ensure_rule_order(rules, cat_order)
            mod.ordered_automatically = True
            target_rule.mods_ordered.append(mod)

    default_rule = _ensure_rule_order(rules, constants.DEFAULT_RULE_ORDER)
    default_rule.mods_ordered.extend(m for m in mods if not m.ordered_automatically)

    # 2. 依規則區段給初始順序
    ordered: list[Mod] = []
    for rule in rules:
        for i, mod in enumerate(rule.mods_ordered):
            mod.order = rule.initial_range + i
        ordered.extend(rule.mods_ordered)
    ordered.sort(key=lambda m: m.order)
    _renumber(ordered)

    # 3. 相依調整：被相依的模組要排在前面
    for item in [m for m in ordered if m.all_dependencies]:
        deps = [c for c in ordered
                if c is not item and any(c.file_name.lower() in d.lower() for d in item.all_dependencies)]
        if not deps:
            continue
        last_dep = max(deps, key=lambda c: c.order)
        if item.order > last_dep.order:
            continue
        ordered.remove(item)
        ordered.insert(ordered.index(last_dep) + 1, item)
        _renumber(ordered)

    # 4a. 補丁／修正／擴充模組自動跟隨：排在所有配對主模組（及相依模組）緊接之後
    for item in [m for m in ordered if m.file_name in patch_map]:
        target_names = {t.lower() for t in patch_map.get(item.file_name, [])}
        dep_names = [d.lower() for d in item.all_dependencies]
        targets = [
            c for c in ordered
            if c is not item and (
                c.file_name.lower() in target_names
                or any(c.file_name.lower() in d for d in dep_names)
            )
        ]
        if not targets:
            continue
        last_target = max(targets, key=lambda c: c.order)
        # 若已被 masterlist 明確指定順序且已在主模組之後，保留其位置；否則緊接在最後一個主模組（及其已排好的補丁）之後
        if item.file_name in masterlist_matched and item.order > last_target.order:
            continue
        ordered.remove(item)
        insert_pos = ordered.index(last_target) + 1
        while (
            insert_pos < len(ordered)
            and ordered[insert_pos].file_name in patch_map
            and any(t.lower() in target_names for t in patch_map[ordered[insert_pos].file_name])
        ):
            insert_pos += 1
        ordered.insert(insert_pos, item)
        _renumber(ordered)

    # 4b. 專屬漢化模組自動跟隨：排在所配對之原版主模組及該主模組的補丁緊接之後
    for item in [m for m in ordered if m.file_name in trans_map and trans_map[m.file_name]]:
        base_names = {t.lower() for t in trans_map[item.file_name]}
        dep_names = [d.lower() for d in item.all_dependencies]
        related = [
            c for c in ordered
            if c is not item and (
                c.file_name.lower() in base_names
                or any(c.file_name.lower() in d for d in dep_names)
                or (
                    c.file_name in patch_map
                    and any(pt.lower() in base_names for pt in patch_map[c.file_name])
                )
            )
        ]
        if not related:
            continue
        last_rel = max(related, key=lambda c: c.order)
        ordered.remove(item)
        insert_pos = ordered.index(last_rel) + 1
        ordered.insert(insert_pos, item)
        _renumber(ordered)

    # 4c. 全域／獨立漢化模組（如 TraditionalChinese.mod、zh_TW.mod）排在清單最後面，確保中文字串不被覆蓋
    global_trans = [m for m in ordered if m.file_name in trans_map and not trans_map[m.file_name]]
    if global_trans:
        for gt in global_trans:
            ordered.remove(gt)
            ordered.append(gt)
        _renumber(ordered)

    for r in rules:
        r.mods_ordered = []
    return ordered
