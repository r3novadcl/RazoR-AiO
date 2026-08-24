import json
import os

import config

_semantic_map: dict[str, str] = {}
_uploaded_map: dict[str, dict] = {}


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load() -> None:
    global _semantic_map, _uploaded_map
    raw = _load_json(config.EMOJIS_JSON_PATH)
    _semantic_map = {k: v for k, v in raw.items() if not k.startswith("_")}
    _uploaded_map = _load_json(config.UPLOADED_EMOJIS_JSON_PATH)


def get(key: str, fallback: str = "") -> str:
    """Returns the live `<:name:id>` (or `<a:name:id>`) tag for a semantic
    key, e.g. get('success'). Falls back to `fallback` (a plain unicode
    emoji if the caller wants one) if the asset hasn't been uploaded yet —
    never a hardcoded default Discord emoji."""
    emoji_name = _semantic_map.get(key)
    if not emoji_name:
        return fallback
    entry = _uploaded_map.get(emoji_name)
    if not entry:
        return fallback
    prefix = "a" if entry.get("animated") else ""
    return f"<{prefix}:{entry['name']}:{entry['id']}>"


def all_keys() -> list[str]:
    return list(_semantic_map.keys())
