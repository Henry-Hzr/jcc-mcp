from __future__ import annotations

from datetime import date, timedelta

from .notice_parser import BalanceUpdate, extract_balance_changes, summarize_notice
from .pathing import build_key, rune_level_dir, sanitize_segment, season_prefix, txt_filename
from .storage import StorageBackend


def _read_lines(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {line.strip() for line in raw.splitlines() if line.strip()}


class GameDataRepository:
    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def read_crawled_ids(self, key: str) -> set[str]:
        return _read_lines(self.storage.read_text(key))

    def write_crawled_ids(self, key: str, ids: set[str]) -> None:
        content = "\n".join(sorted(ids))
        self.storage.write_text(key, content)

    def list_seasons(self) -> list[str]:
        seasons = []
        for directory in self.storage.list_directories():
            if directory.startswith("season_"):
                seasons.append(directory.replace("season_", "", 1))
        return sorted(seasons)

    def save_hero(self, season: str, hero_name: str, content: str) -> None:
        self.storage.write_text(self.hero_key(season, hero_name), content)

    def get_hero(self, season: str, hero_name: str) -> str | None:
        return self.storage.read_text(self.hero_key(season, hero_name))

    def list_heroes(self, season: str) -> list[str]:
        return self._list_text_names(
            build_key(season_prefix(season), "hero"),
            excluded={"crawled_hero.txt"},
        )

    def save_trait(self, season: str, trait_type: str, trait_name: str, content: str) -> None:
        self.storage.write_text(self.trait_key(season, trait_type, trait_name), content)

    def get_trait(self, season: str, trait_type: str, trait_name: str) -> str | None:
        return self.storage.read_text(self.trait_key(season, trait_type, trait_name))

    def list_traits(self, season: str, trait_type: str) -> list[str]:
        return self._list_text_names(
            build_key(season_prefix(season), "traits", sanitize_segment(trait_type)),
            excluded={"crawled_traits.txt"},
        )

    def save_rune(self, season: str, level: str, rune_name: str, content: str) -> None:
        self.storage.write_text(self.rune_key(season, level, rune_name), content)

    def get_rune(self, season: str, level: str, rune_name: str) -> str | None:
        return self.storage.read_text(self.rune_key(season, level, rune_name))

    def list_runes(self, season: str, level: str) -> list[str]:
        return self._list_text_names(
            build_key(season_prefix(season), "hex", rune_level_dir(level)),
            excluded={"crawled_hex.txt"},
        )

    def save_equipment(self, season: str, equipment_type: str, equipment_name: str, content: str) -> None:
        self.storage.write_text(self.equipment_key(season, equipment_type, equipment_name), content)

    def get_equipment(
        self,
        season: str,
        equipment_name: str,
        equipment_type: str = "",
    ) -> tuple[str, str] | None:
        if equipment_type:
            content = self.storage.read_text(self.equipment_key(season, equipment_type, equipment_name))
            if content is None:
                return None
            return sanitize_segment(equipment_type), content
        for candidate_type in self.list_equipment_types(season):
            content = self.storage.read_text(self.equipment_key(season, candidate_type, equipment_name))
            if content is not None:
                return candidate_type, content
        return None

    def list_equipment_types(self, season: str) -> list[str]:
        return self.storage.list_directories(build_key(season_prefix(season), "equipment"))

    def list_equipment(
        self,
        season: str,
        equipment_type: str = "",
    ) -> list[tuple[str, str]]:
        if equipment_type:
            names = self._list_text_names(
                build_key(season_prefix(season), "equipment", sanitize_segment(equipment_type)),
                excluded={"crawled_equipment.txt"},
            )
            return [(sanitize_segment(equipment_type), name) for name in names]
        items: list[tuple[str, str]] = []
        for candidate_type in self.list_equipment_types(season):
            items.extend(self.list_equipment(season, candidate_type))
        return items

    def save_notice(self, filename: str, content: str) -> None:
        self.storage.write_text(build_key("notice", filename), content)

    def list_notices(self, limit: int = 10) -> list:
        results = []
        for key in self.storage.list_keys("notice"):
            file_name = key.replace("\\", "/").split("/")[-1]
            if file_name == "crawled_ids.txt" or not file_name.endswith(".txt"):
                continue
            content = self.storage.read_text(key)
            if content is None:
                continue
            results.append(summarize_notice(content, key))
        results.sort(key=lambda item: (item.published_at or date.min, item.notice_id), reverse=True)
        return results[:limit]

    def search_notices(self, keyword: str, limit: int = 10) -> list:
        keyword_lower = keyword.lower()
        matches = []
        for key in self.storage.list_keys("notice"):
            file_name = key.replace("\\", "/").split("/")[-1]
            if file_name == "crawled_ids.txt" or not file_name.endswith(".txt"):
                continue
            content = self.storage.read_text(key)
            if content is None:
                continue
            if keyword_lower not in content.lower():
                continue
            matches.append(summarize_notice(content, key))
        matches.sort(key=lambda item: (item.published_at or date.min, item.notice_id), reverse=True)
        return matches[:limit]

    def latest_balance_updates(self, days: int = 60, limit: int = 10) -> list[BalanceUpdate]:
        today = date.today()
        threshold = today - timedelta(days=days)
        seasons = self.list_seasons()
        updates: list[BalanceUpdate] = []
        for key in self.storage.list_keys("notice"):
            file_name = key.replace("\\", "/").split("/")[-1]
            if file_name == "crawled_ids.txt" or not file_name.endswith(".txt"):
                continue
            content = self.storage.read_text(key)
            if content is None:
                continue
            summary = summarize_notice(content, key)
            if summary.published_at is None or summary.published_at < threshold:
                continue
            changes = extract_balance_changes(content, seasons)
            if not changes:
                continue
            updates.append(
                BalanceUpdate(
                    title=summary.title,
                    published_at=summary.published_at,
                    changes=changes,
                    key=key,
                )
            )
        updates.sort(key=lambda item: item.published_at, reverse=True)
        return updates[:limit]

    def hero_crawled_key(self, season: str) -> str:
        return build_key(season_prefix(season), "hero", "crawled_hero.txt")

    def trait_crawled_key(self, season: str, trait_type: str) -> str:
        return build_key(season_prefix(season), "traits", sanitize_segment(trait_type), "crawled_traits.txt")

    def rune_crawled_key(self, season: str, level: str) -> str:
        return build_key(season_prefix(season), "hex", rune_level_dir(level), "crawled_hex.txt")

    def equipment_crawled_key(self, season: str, equipment_type: str) -> str:
        return build_key(season_prefix(season), "equipment", sanitize_segment(equipment_type), "crawled_equipment.txt")

    def notices_crawled_key(self) -> str:
        return build_key("notice", "crawled_ids.txt")

    def hero_key(self, season: str, hero_name: str) -> str:
        return build_key(season_prefix(season), "hero", txt_filename(hero_name))

    def trait_key(self, season: str, trait_type: str, trait_name: str) -> str:
        return build_key(season_prefix(season), "traits", sanitize_segment(trait_type), txt_filename(trait_name))

    def rune_key(self, season: str, level: str, rune_name: str) -> str:
        return build_key(season_prefix(season), "hex", rune_level_dir(level), txt_filename(rune_name))

    def equipment_key(self, season: str, equipment_type: str, equipment_name: str) -> str:
        return build_key(
            season_prefix(season),
            "equipment",
            sanitize_segment(equipment_type),
            txt_filename(equipment_name),
        )

    def _list_text_names(self, prefix: str, excluded: set[str]) -> list[str]:
        names = []
        for key in self.storage.list_keys(prefix):
            file_name = key.replace("\\", "/").split("/")[-1]
            if file_name in excluded or not file_name.endswith(".txt"):
                continue
            names.append(file_name[:-4])
        return sorted(names)
