"""
JSON Utilities
Safe JSON parsing with error handling for streaming candidate data.
"""

import json
from typing import Any, Optional
from src.utils.logger import get_logger

logger = get_logger("json_utils")


def safe_parse_json(line: str) -> Optional[dict]:
    """
    Safely parse a JSON string, returning None on failure.
    Used for streaming JSONL processing.
    """
    try:
        return json.loads(line)
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"JSON parse error: {e}")
        return None


def safe_get(data: dict, *keys, default: Any = None) -> Any:
    """
    Safely traverse nested dictionary keys.
    Returns default if any key is missing.
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current if current is not None else default


def safe_get_float(data: dict, key: str, default: float = 0.0) -> float:
    """Safely get a float value from a dict."""
    val = data.get(key, default)
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def safe_get_int(data: dict, key: str, default: int = 0) -> int:
    """Safely get an integer value from a dict."""
    val = data.get(key, default)
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def safe_get_bool(data: dict, key: str, default: bool = False) -> bool:
    """Safely get a boolean value from a dict."""
    val = data.get(key, default)
    if isinstance(val, bool):
        return val
    return default


def safe_get_str(data: dict, key: str, default: str = "") -> str:
    """Safely get a string value from a dict."""
    val = data.get(key, default)
    return str(val) if val is not None else default


def safe_get_list(data: dict, key: str, default: list = None) -> list:
    """Safely get a list value from a dict."""
    val = data.get(key, default or [])
    return val if isinstance(val, list) else (default or [])
