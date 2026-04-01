from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class NoticeSummary:
    title: str
    published_at: date | None
    notice_id: str
    key: str


@dataclass(frozen=True)
class BalanceChange:
    category: str
    season: str
    content: str


@dataclass(frozen=True)
class BalanceUpdate:
    title: str
    published_at: date
    changes: list[BalanceChange]
    key: str


def extract_notice_title(content: str) -> str:
    match = re.search(r"标题：(.*?)\n", content)
    if match:
        return match.group(1).strip()
    return "未知标题"


def extract_notice_id(content: str, key: str) -> str:
    match = re.search(r"ID：(.*?)\n", content)
    if match:
        return match.group(1).strip()
    file_name = key.replace("\\", "/").split("/")[-1]
    return file_name.rsplit(".", 1)[0]


def extract_notice_date(content: str, key: str) -> date | None:
    match = re.search(r"日期：(\d{4}-\d{2}-\d{2})", content)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    file_name = key.replace("\\", "/").split("/")[-1]
    fallback = DATE_RE.search(file_name)
    if not fallback:
        return None
    return datetime.strptime(fallback.group(1), "%Y-%m-%d").date()


def summarize_notice(content: str, key: str) -> NoticeSummary:
    return NoticeSummary(
        title=extract_notice_title(content),
        published_at=extract_notice_date(content, key),
        notice_id=extract_notice_id(content, key),
        key=key,
    )


def _normalize_season(raw_season: str, known_seasons: list[str]) -> str:
    cleaned = raw_season.strip()
    for season in known_seasons:
        if season in cleaned:
            return season
    return cleaned or "未指定"


def _collect_tagged_changes(
    content: str,
    label: str,
    category: str,
    known_seasons: list[str],
) -> list[BalanceChange]:
    pattern = rf"【([^】]+)】[：\s]*(?:平衡性调整)?[：\s]*——{label}\s*([\s\S]*?)(?=——|\n【|$)"
    changes = []
    for raw_season, raw_content in re.findall(pattern, content, re.DOTALL):
        text = raw_content.strip()
        if not text or "活动" in text:
            continue
        changes.append(
            BalanceChange(
                category=category,
                season=_normalize_season(raw_season, known_seasons),
                content=text,
            )
        )
    return changes


def _collect_untagged_changes(
    content: str,
    label: str,
    category: str,
    known_seasons: list[str],
) -> list[BalanceChange]:
    pattern = rf"——{label}\s*([\s\S]*?)(?=——|\n【|$)"
    matches = re.findall(pattern, content, re.DOTALL)
    changes = []
    for text in matches:
        cleaned = text.strip()
        if not cleaned or "活动" in cleaned:
            continue
        position = content.find(cleaned)
        start = max(0, position - 200)
        context = content[start:position]
        season_tags = re.findall(r"【([^】]+)】", context)
        raw_season = season_tags[-1] if season_tags else "未指定"
        changes.append(
            BalanceChange(
                category=category,
                season=_normalize_season(raw_season, known_seasons),
                content=cleaned,
            )
        )
    return changes


def extract_balance_changes(content: str, known_seasons: list[str]) -> list[BalanceChange]:
    definitions = [
        ("英雄调整", "英雄调整"),
        ("羁绊调整", "羁绊调整"),
        ("强化符文调整", "强化符文调整"),
        ("装备调整", "装备调整"),
    ]
    changes: list[BalanceChange] = []
    for label, category in definitions:
        tagged = _collect_tagged_changes(content, label, category, known_seasons)
        if tagged:
            changes.extend(tagged)
            continue
        changes.extend(_collect_untagged_changes(content, label, category, known_seasons))
    return changes

