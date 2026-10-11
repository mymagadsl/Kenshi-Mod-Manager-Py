"""Kenshi .mod 二進位完整物件解析器（對應 C# Core/Kenshi_Data/GameData.cs）。

支援 fileVersion 7 ~ 17+（包含 FCS v17 的檔頭長度欄位）。
使用 struct.unpack_from 直接在 bytes 緩衝區上位移讀取，避免大量小塊 I/O 呼叫。
"""
from __future__ import annotations

import enum
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

INT_MAX = 0x7FFFFFFF


class ItemType(enum.IntEnum):
    BUILDING = 0
    CHARACTER = 1
    WEAPON = 2
    ARMOUR = 3
    ITEM = 4
    ANIMAL_ANIMATION = 5
    ATTACHMENT = 6
    RACE = 7
    LOCATION = 8
    WAR_SAVESTATE = 9
    FACTION = 10
    NULL_ITEM = 11
    ZONE_MAP = 12
    TOWN = 13
    WORLDMAP_CHARACTER = 14
    CHARACTER_APPEARANCE_OLD = 15
    LOCATIONAL_DAMAGE = 16
    COMBAT_TECHNIQUE = 17
    DIALOGUE = 18
    DIALOGUE_LINE = 19
    TECHTREE = 20
    RESEARCH = 21
    AI_TASK = 22
    AI_STATE = 23
    ANIMATION = 24
    STATS = 25
    PERSONALITY = 26
    CONSTANTS = 27
    BIOMES = 28
    BUILDING_PART = 29
    INSTANCE_COLLECTION = 30
    DIALOG_ACTION = 31
    TEMPORARY_INFO = 32
    MOD_FILENAME = 33
    PLATOON = 34
    GAMESTATE_BUILDING = 35
    GAMESTATE_CHARACTER = 36
    GAMESTATE_FACTION = 37
    GAMESTATE_TOWN_INSTANCE_LIST = 38
    STATE = 39
    SAVED_STATE = 40
    INVENTORY_STATE = 41
    INVENTORY_ITEM_STATE = 42
    REPEATABLE_BUILDING_PART_SLOT = 43
    MATERIAL_SPEC = 44
    MATERIAL_SPECS_COLLECTION = 45
    CONTAINER = 46
    MATERIAL_SPECS_CLOTHING = 47
    GAMESTATE_BUILDING_INTERIOR = 48
    VENDOR_LIST = 49
    MATERIAL_SPECS_WEAPON = 50
    WEAPON_MANUFACTURER = 51
    SQUAD_TEMPLATE = 52
    ROAD = 53
    LOCATION_NODE = 54
    COLOR_DATA = 55
    CAMERA = 56
    MEDICAL_STATE = 57
    MEDICAL_PART_STATE = 58
    FOLIAGE_LAYER = 59
    FOLIAGE_MESH = 60
    GRASS = 61
    BUILDING_FUNCTIONALITY = 62
    DAY_SCHEDULE = 63
    NEW_GAME_STARTOFF = 64
    GAMESTATE_CRAFTING = 65
    CHARACTER_APPEARANCE = 66
    GAMESTATE_AI = 67
    WILDLIFE_BIRDS = 68
    MAP_FEATURES = 69
    DIPLOMATIC_ASSAULTS = 70
    SINGLE_DIPLOMATIC_ASSAULT = 71
    AI_PACKAGE = 72
    DIALOGUE_PACKAGE = 73
    GUN_DATA = 74
    HUMAN_CHARACTER = 75
    ANIMAL_CHARACTER = 76
    UNIQUE_SQUAD_TEMPLATE = 77
    FACTION_TEMPLATE = 78
    AI_SCHEDULE = 79
    WEATHER = 80
    SEASON = 81
    EFFECT = 82
    ITEM_PLACEMENT_GROUP = 83
    WORD_SWAPS = 84
    NEST = 85
    NEST_ITEM = 86
    CHARACTER_PHYSICS_ATTACHMENT = 87
    LIGHT = 88
    HEAD = 89
    BLUEPRINT = 90
    SHOP_TRADER_CLASS = 91
    FOLIAGE_BUILDING = 92
    FACTION_CAMPAIGN = 93
    GAMESTATE_TOWN = 94
    BIOME_GROUP = 95
    EFFECT_FOG_VOLUME = 96
    FARM_DATA = 97
    FARM_PART = 98
    ENVIRONMENT_RESOURCES = 99
    RACE_GROUP = 100
    ARTIFACTS = 101
    MAP_ITEM = 102
    BUILDINGS_SWAP = 103
    ITEMS_CULTURE = 104
    ANIMATION_EVENT = 105
    TUTORIAL = 106
    CROSSBOW = 107
    TERRAIN_DECALS = 108
    AMBIENT_SOUND = 109
    WORLD_EVENT_STATE = 110
    LIMB_REPLACEMENT = 111
    ANIMATION_FILE = 112
    BOAT = 113
    GAMESTATE_BOAT = 114
    BUILD_GRID = 115
    OBJECT_TYPE_MAX = 116


ITEM_TYPE_LABELS: dict[int, str] = {
    ItemType.BUILDING: "建築 (BUILDING)",
    ItemType.CHARACTER: "角色 (CHARACTER)",
    ItemType.WEAPON: "武器 (WEAPON)",
    ItemType.ARMOUR: "護甲 (ARMOUR)",
    ItemType.ITEM: "物品 (ITEM)",
    ItemType.RACE: "種族 (RACE)",
    ItemType.FACTION: "陣營 (FACTION)",
    ItemType.TOWN: "城鎮 (TOWN)",
    ItemType.DIALOGUE: "對話 (DIALOGUE)",
    ItemType.DIALOGUE_LINE: "對話台詞 (DIALOGUE_LINE)",
    ItemType.RESEARCH: "研究 (RESEARCH)",
    ItemType.AI_TASK: "AI 任務 (AI_TASK)",
    ItemType.ANIMATION: "動畫 (ANIMATION)",
    ItemType.CONSTANTS: "全域常數 (CONSTANTS)",
    ItemType.BIOMES: "生態區 (BIOMES)",
    ItemType.BUILDING_PART: "建築部件 (BUILDING_PART)",
    ItemType.VENDOR_LIST: "商店清單 (VENDOR_LIST)",
    ItemType.WEAPON_MANUFACTURER: "武器製造商 (WEAPON_MANUFACTURER)",
    ItemType.SQUAD_TEMPLATE: "小隊模板 (SQUAD_TEMPLATE)",
    ItemType.NEW_GAME_STARTOFF: "開局設定 (NEW_GAME_STARTOFF)",
    ItemType.DIALOGUE_PACKAGE: "對話包 (DIALOGUE_PACKAGE)",
    ItemType.WEATHER: "天氣 (WEATHER)",
    ItemType.WORLD_EVENT_STATE: "世界狀態 (WORLD_EVENT_STATE)",
    ItemType.LIMB_REPLACEMENT: "義肢 (LIMB_REPLACEMENT)",
    ItemType.CROSSBOW: "十字弓 (CROSSBOW)",
}


def item_type_label(type_id: int) -> str:
    if type_id in ITEM_TYPE_LABELS:
        return ITEM_TYPE_LABELS[type_id]
    try:
        return ItemType(type_id).name
    except ValueError:
        return f"TYPE_{type_id}"


@dataclass
class ModItem:
    string_id: str
    name: str
    item_type: int
    state: str  # "OWNED" | "MODIFIED" | "REMOVED"
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def type_label(self) -> str:
        return item_type_label(self.item_type)


class _Buf:
    """輕量二進位游標，直接在 bytes 上 unpack。"""
    __slots__ = ("buf", "pos", "end")

    def __init__(self, buf: bytes):
        self.buf = buf
        self.pos = 0
        self.end = len(buf)

    def i32(self) -> int:
        p = self.pos
        if p + 4 > self.end:
            raise EOFError
        self.pos = p + 4
        return struct.unpack_from("<i", self.buf, p)[0]

    def i64(self) -> int:
        p = self.pos
        if p + 8 > self.end:
            raise EOFError
        self.pos = p + 8
        return struct.unpack_from("<q", self.buf, p)[0]

    def f32(self) -> float:
        p = self.pos
        if p + 4 > self.end:
            raise EOFError
        self.pos = p + 4
        return round(struct.unpack_from("<f", self.buf, p)[0], 5)

    def bool(self) -> bool:
        p = self.pos
        if p >= self.end:
            raise EOFError
        self.pos = p + 1
        return self.buf[p] != 0

    def vec3(self) -> str:
        p = self.pos
        if p + 12 > self.end:
            raise EOFError
        self.pos = p + 12
        x, y, z = struct.unpack_from("<3f", self.buf, p)
        return f"{x:.4g}, {y:.4g}, {z:.4g}"

    def quat4(self) -> str:
        p = self.pos
        if p + 16 > self.end:
            raise EOFError
        self.pos = p + 16
        x, y, z, w = struct.unpack_from("<4f", self.buf, p)
        return f"{x:.4g}, {y:.4g}, {z:.4g}, {w:.4g}"

    def str(self) -> str:
        n = self.i32()
        if n <= 0:
            return ""
        p = self.pos
        if p + n > self.end:
            raise EOFError
        self.pos = p + n
        return self.buf[p:p + n].decode("utf-8", errors="replace")


def _tagged(tags: dict[str, bool] | None, key: str) -> bool:
    return True if tags is None else bool(tags.get(key))


def parse_mod_file(path: str | Path) -> list[ModItem]:
    """解析單一 .mod 檔案內的所有物件與其修改的屬性/參照。"""
    p = Path(path)
    if not p.is_file():
        return []
    try:
        raw = p.read_bytes()
    except OSError:
        return []

    b = _Buf(raw)
    file_name = p.name
    items: dict[str, ModItem] = {}

    try:
        file_version = b.i32()
        if file_version > 15:
            header_end = 0
            if file_version >= 17:
                header_len = b.i32()  # v17+ 檔頭長度
                header_end = b.pos + header_len
            b.i32()      # header.Version
            b.str()      # Author
            b.str()      # Description
            b.str()      # Dependencies
            b.str()      # Referenced
            if header_end > b.pos and header_end <= b.end:
                b.pos = header_end

        b.i32()  # lastID
        item_count = b.i32()

        for _ in range(item_count):
            b.i32()  # instance count / unused int
            item_type = b.i32()
            num_id = b.i32()
            name = b.str()
            sid = b.str() if file_version >= 7 else f"{num_id}-{file_name}"

            tags: dict[str, bool] | None = None
            is_modified_flag = False
            is_renamed_flag = False

            if file_version >= 15:
                flags = b.i32() & INT_MAX
                is_modified_flag = bool(flags & 1)
                is_renamed_flag = bool(flags & 2)
            elif file_version >= 11:
                tag_count = b.i32()
                if tag_count > 0 and file_name != "gamedata.base":
                    tags = {}
                    for _ in range(tag_count):
                        k = b.str()
                        tags[k] = b.bool()

            existing = items.get(sid)
            if existing is None:
                state = "MODIFIED" if is_modified_flag else "OWNED"
                item = ModItem(string_id=sid, name=name, item_type=item_type, state=state)
                items[sid] = item
            else:
                item = existing
                if is_renamed_flag or not item.name:
                    item.name = name

            vals = item.values
            if is_renamed_flag:
                vals["[名稱 (Name)]"] = name

            # 1. bool
            for _ in range(b.i32()):
                k = b.str()
                v = b.bool()
                if _tagged(tags, k):
                    vals[k] = v

            # 2. float
            for _ in range(b.i32()):
                k = b.str()
                v = b.f32()
                if _tagged(tags, k):
                    vals[k] = v

            # 3. int
            for _ in range(b.i32()):
                k = b.str()
                v = b.i32()
                if _tagged(tags, k):
                    vals[k] = v

            # 4. vec3 & quat4
            if file_version > 8:
                for _ in range(b.i32()):
                    k = b.str()
                    v = b.vec3()
                    if _tagged(tags, k):
                        vals[k] = v
                for _ in range(b.i32()):
                    k = b.str()
                    v = b.quat4()
                    if _tagged(tags, k):
                        vals[k] = v

            # 5. string
            for _ in range(b.i32()):
                k = b.str()
                v = b.str()
                if _tagged(tags, k):
                    vals[k] = v

            # 6. File
            for _ in range(b.i32()):
                k = b.str()
                v = b.str()
                if _tagged(tags, k):
                    vals[k] = v

            # 7. References
            for _ in range(b.i32()):
                section = b.str()
                ref_count = b.i32()
                for _ in range(ref_count):
                    if file_version < 8:
                        b.i64()
                        continue
                    ref_id = b.str()
                    v0 = b.i32()
                    v1 = b.i32() if file_version >= 10 else 0
                    v2 = b.i32() if file_version >= 10 else 0
                    if tags is not None and f"-ref-{ref_id}" not in tags:
                        continue
                    removed = (tags is not None and not tags[f"-ref-{ref_id}"]) or (v2 == INT_MAX)
                    if item_type == ItemType.DIALOGUE_PACKAGE and v1 == 100:
                        v1 = 0
                    prop_key = f"[參照:{section}] {ref_id}"
                    vals[prop_key] = "REMOVED" if removed else f"({v0}, {v1}, {v2})"

            # 8. Instances
            for _ in range(b.i32()):
                inst_id = b.str() if file_version >= 15 else f"{b.i32()}-{file_name}"
                ref_str = "" if file_version < 8 else b.str()
                # x, y, z, qw, qx, qy, qz (7 floats = 28 bytes)
                if b.pos + 28 > b.end:
                    raise EOFError
                x, y, z, qw, qx, qy, qz = struct.unpack_from("<7f", b.buf, b.pos)
                b.pos += 28
                states: list[str] = []
                if file_version > 6:
                    sc = b.i32()
                    if file_version < 15:
                        for _ in range(sc):
                            states.append(f"{b.i32()}-{file_name}-INGAME")
                    else:
                        for _ in range(sc):
                            states.append(b.str())
                vals[f"[實例:{inst_id}]"] = f"ref={ref_str} pos=({x:.2f},{y:.2f},{z:.2f})"

            # REMOVED flag
            if vals.get("REMOVED") is True:
                item.state = "REMOVED"
                vals.pop("REMOVED", None)
    except EOFError:
        pass

    return list(items.values())
