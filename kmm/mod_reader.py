"""讀取 .mod 檔頭（對應 C# Core/ModMetadataReader.cs）。

格式（little-endian）：
    int32 檔案版本；若 > 15 才有以下檔頭
    int32 模組版本
    str   作者
    str   描述
    str   相依（逗號分隔）
    str   參考（逗號分隔）
其中 str = int32 長度 + UTF-8 位元組。
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO

from . import constants


@dataclass
class Metadata:
    version: int = 0
    author: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    referenced: list[str] = field(default_factory=list)


def _read_int(f: BinaryIO) -> int:
    data = f.read(4)
    if len(data) < 4:
        raise EOFError
    return struct.unpack("<i", data)[0]


_MAX_HEADER_STR = 65536


def _read_str(f: BinaryIO) -> str:
    count = _read_int(f)
    if count <= 0:
        return ""
    if count > _MAX_HEADER_STR:
        raise EOFError
    data = f.read(count)
    if len(data) < count:
        raise EOFError
    return data.decode("utf-8", errors="replace")


def _split_list(value: str) -> list[str]:
    return [m for m in value.split(",") if m and m.lower() not in constants.SKIPPABLE_MODS]


def load_metadata(filename: str) -> Metadata | None:
    """回傳檔頭資訊；檔案不存在或舊版格式（無檔頭）時回傳 None。"""
    try:
        f = open(filename, "rb")
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return None
    with f:
        try:
            file_version = _read_int(f)
            if file_version <= 15:
                return None
            if file_version >= 17:
                _read_int(f)  # v17+ 檔頭總長度（bytes）
            return Metadata(
                version=_read_int(f),
                author=_read_str(f),
                description=_read_str(f),
                dependencies=_split_list(_read_str(f)),
                referenced=_split_list(_read_str(f)),
            )
        except EOFError:
            return None


def write_metadata_for_test(path, md: Metadata, file_version: int = 16) -> None:
    """測試用：產生只含檔頭的 .mod 檔。"""
    def s(v: str) -> bytes:
        b = v.encode("utf-8")
        return struct.pack("<i", len(b)) + b

    body = (struct.pack("<i", md.version)
            + s(md.author) + s(md.description)
            + s(",".join(md.dependencies)) + s(",".join(md.referenced)))
    with open(path, "wb") as f:
        f.write(struct.pack("<i", file_version))
        if file_version >= 17:
            f.write(struct.pack("<i", len(body)))
        f.write(body)
