from __future__ import annotations

import re


INVALID_SEGMENT_CHARS = re.compile(r'[\\/*?:"<>|]')


def sanitize_segment(value: str) -> str:
    cleaned = INVALID_SEGMENT_CHARS.sub("", (value or "").strip())
    return cleaned


def season_prefix(season_name: str) -> str:
    return f"season_{sanitize_segment(season_name)}"


def rune_level_dir(level_name: str) -> str:
    cleaned = sanitize_segment(level_name)
    if not cleaned:
        return ""
    return cleaned.replace("强化符文", "").strip() + "强化符文"


def txt_filename(name: str) -> str:
    return f"{sanitize_segment(name)}.txt"


def build_key(*parts: str) -> str:
    normalized = []
    for part in parts:
        if not part:
            continue
        piece = part.replace("\\", "/").strip("/")
        if piece:
            normalized.append(piece)
    return "/".join(normalized)
