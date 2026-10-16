"""資料模型（對應 C# Core/Models/Mod.cs、Rules.cs）。"""
from __future__ import annotations

import enum
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import PurePath

from . import constants


class Source(enum.Enum):
    GAME_FOLDER = "GameFolder"
    STEAM = "Steam"

    @property
    def label(self) -> str:
        return "Steam" if self is Source.STEAM else "遊戲資料夾"


@dataclass(eq=False)
class Mod:
    file_path: str
    source: Source = Source.GAME_FOLDER
    id: str | None = None
    title: str = ""
    zh_name: str = ""
    description: str = ""
    author: str = ""
    version: str = ""
    order: int = -1
    active: bool = False
    categories: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    ordered_automatically: bool = False
    subscribed_by: list[str] = field(default_factory=list)
    updated_at: float | None = None
    uid: str = field(default_factory=lambda: uuid.uuid4().hex)

    def is_subscribed_by(self, user_id: str | None) -> bool:
        """判斷此模組是否由指定的 Steam 帳號 (32-bit ID) 訂閱。若未提供 user_id，則只要有任何訂閱者即為 True。"""
        if self.source is not Source.STEAM:
            return False
        if not self.subscribed_by:
            return False
        if not user_id:
            return bool(self.subscribed_by)
        return str(user_id) in self.subscribed_by

    @property
    def file_name(self) -> str:
        return PurePath(self.file_path).name

    @property
    def has_extension(self) -> bool:
        return bool(PurePath(self.file_path).suffix)

    @property
    def display_name(self) -> str:
        stem = PurePath(self.file_path).stem if self.has_extension else PurePath(self.file_path).name
        return stem if self.has_extension else f"[錯誤]：{stem}"

    def ui_name(self, show_zh: bool = True) -> str:
        base = self.display_name
        if not show_zh or not self.zh_name or not self.has_extension:
            return base
        zh = self.zh_name.strip()
        if not zh or zh.lower() == base.lower():
            return base
        return f"【{zh}】 {base}"

    @property
    def folder(self) -> str:
        p = PurePath(self.file_path)
        return str(p.parent) if self.has_extension else str(p)

    @property
    def display_categories(self) -> str:
        return ", ".join(self.categories)

    @property
    def all_dependencies(self) -> list[str]:
        return [d for d in (*self.dependencies, *self.references)
                if d and d.lower() not in constants.SKIPPABLE_MODS]

    def url(self, steam_page_url: str = "", nexus_page_url: str = "") -> str:
        """回傳模組在 Steam 工作坊的專屬網址；若無 ID 則回傳 Steam 工作坊搜尋網址。"""
        if self.id:
            base = steam_page_url or constants.DEFAULT_STEAM_PAGE_URL
            return base + self.id
        # 無 ID 時，直接前往 Steam Kenshi 工作坊搜尋該模組名稱
        search_base = (
            nexus_page_url
            if (nexus_page_url and "steamcommunity.com" in nexus_page_url)
            else constants.DEFAULT_STEAM_SEARCH_URL
        )
        query = urllib.parse.quote_plus(self.display_name)
        return search_base + query

    @property
    def updated_display(self) -> str:
        """格式化為 'YYYY-MM-DD HH:MM'，無更新時間則為 '—'。"""
        if not self.updated_at:
            return "—"
        try:
            from datetime import datetime
            return datetime.fromtimestamp(self.updated_at).strftime("%Y-%m-%d %H:%M")
        except (OSError, OverflowError, ValueError):
            return "—"

    @property
    def updated_date_only(self) -> str:
        """用於列表精簡顯示 'YYYY-MM-DD'。"""
        if not self.updated_at:
            return "—"
        try:
            from datetime import datetime
            return datetime.fromtimestamp(self.updated_at).strftime("%Y-%m-%d")
        except (OSError, OverflowError, ValueError):
            return "—"

    def update_status(self, now: float | None = None) -> str:
        """回傳 'today' (24小時內或今日)、'week' (7天內)、或 'older'。"""
        if not self.updated_at:
            return "older"
        import time
        from datetime import datetime
        current = now if now is not None else time.time()
        diff = current - self.updated_at
        if diff < 0:
            return "today"
        # 若在 86400 秒 (24 小時) 內，或同一日曆天
        if diff <= 86400:
            return "today"
        try:
            if datetime.fromtimestamp(self.updated_at).date() == datetime.fromtimestamp(current).date():
                return "today"
        except (OSError, OverflowError, ValueError):
            pass
        if diff <= 7 * 86400:
            return "week"
        return "older"


@dataclass
class Rule:
    order: int
    name: str
    mods: list[str]
    mods_ordered: list[Mod] = field(default_factory=list)

    @property
    def initial_range(self) -> int:
        return constants.RULE_MAX_RANGE * self.order
