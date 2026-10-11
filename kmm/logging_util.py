"""寫入 info.log / error.log（對應 C# Core/Logging.cs）。"""
from __future__ import annotations

import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable

_lock = threading.Lock()


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write(path: Path, *lines: str | Iterable[str]) -> None:
    flat: list[str] = []
    for item in lines:
        if isinstance(item, str):
            flat.append(item)
        else:
            flat.extend(item)
    if not flat:
        return
    with _lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                for line in flat:
                    f.write(f"{_stamp()} - {line}\n")
        except OSError:
            pass


def write_exception(path: Path, exc: BaseException) -> None:
    write(path, "".join(traceback.format_exception(exc)).rstrip())


def reset(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
        if path.parent.name == "logs":
            (path.parent.parent / path.name).unlink(missing_ok=True)
    except OSError:
        pass
