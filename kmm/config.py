"""程式設定（對應 C# Core/KenshiToolConfig.cs），JSON 欄位名稱與原版相同。"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import constants, logging_util


@dataclass
class KenshiToolConfig:
    GamePath: str = ""
    SteamModsPath: str = ""
    SteamPageUrl: str = constants.DEFAULT_STEAM_PAGE_URL
    SteamSearchUrl: str = constants.DEFAULT_STEAM_SEARCH_URL
    NexusPageUrl: str = constants.DEFAULT_STEAM_SEARCH_URL
    MasterlistVersion: str | None = None
    MasterlistSource: str = "millerscout/kmm-masterlist"
    MaxLogFiles: int = 5
    CheckForUpdatesAutomatically: bool = True
    Language: str = "zh_TW"

    @property
    def mod_folder(self) -> Path:
        return Path(self.GamePath) / "Mods"

    @property
    def uses_steam(self) -> bool:
        return self.SteamModsPath != "NONE"

    @classmethod
    def load(cls, path: Path = constants.CONFIG_FILE) -> "KenshiToolConfig":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            logging_util.write(constants.ERROR_FILE, "無法讀取 config.json，改用預設值。")
            logging_util.write_exception(constants.ERROR_FILE, exc)
            return cls()
        known = {f.name for f in fields(cls)}
        cfg = cls(**{k: v for k, v in data.items() if k in known})
        if cfg.SteamModsPath is None:
            cfg.SteamModsPath = ""
        if cfg.GamePath is None:
            cfg.GamePath = ""
        if cfg.Language not in ("zh_TW", "zh_CN", "en_US"):
            cfg.Language = "zh_TW"
        return cfg

    def save(self, path: Path = constants.CONFIG_FILE) -> None:
        try:
            if path.exists():
                try:
                    os.chmod(path, stat.S_IWRITE)
                except OSError:
                    pass
            path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logging_util.write(constants.ERROR_FILE, f"無法儲存設定檔：{path}")
            logging_util.write_exception(constants.ERROR_FILE, exc)
