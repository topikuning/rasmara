"""Helper kecil untuk baca env var dengan cast tipe."""
import os
from typing import Any


def env(key: str, default: Any = None) -> str:
    val = os.environ.get(key)
    if val is None or val == "":
        if default is None:
            raise RuntimeError(f"Environment variable {key} is required")
        return str(default)
    return val


def env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None or val == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on", "y")


def env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None or val == "":
        return default
    return int(val)


def env_list(key: str, default: list[str] | None = None, sep: str = ",") -> list[str]:
    val = os.environ.get(key)
    if val is None or val == "":
        return list(default or [])
    return [item.strip() for item in val.split(sep) if item.strip()]
