from __future__ import annotations

import logging
import time

from ..repository import GameDataRepository
from .common import first_non_empty_text, open_page, unique_texts


LOGGER = logging.getLogger(__name__)


ITEM_SELECTORS = [
    ".equipment-list .equipment-item img",
    ".equipment-item img",
    ".equipment-compose img",
    ".equipment-card img",
    ".equipment-item",
]


def _extract_seasons(page) -> list[str]:
    elements = page.locator(".tab-bar a").all()
    return unique_texts([(element.text_content() or "") for element in elements])


def _extract_equipment_types(page) -> list[str]:
    elements = page.locator(".edition-tab li").all()
    values = unique_texts([(element.text_content() or "") for element in elements])
    if values:
        return values
    return ["基础装备", "成型装备", "光明装备", "辅助装备", "神器装备", "纹章", "特殊装备"]


def _select_season(page, season: str) -> bool:
    for selector in [
        f".tab-bar a span:has-text('{season}')",
        f".tab-bar a:has-text('{season}')",
        f".tab-bar span:has-text('{season}')",
    ]:
        try:
            page.locator(selector).first.click(timeout=5000)
            return True
        except Exception:
            continue
    return False


def _select_equipment_type(page, equipment_type: str) -> bool:
    try:
        page.locator(f".edition-tab li:has-text('{equipment_type}')").first.click(timeout=5000)
        time.sleep(1)
        return True
    except Exception:
        return False


def _find_item_selector(page) -> tuple[str, int]:
    for selector in ITEM_SELECTORS:
        count = page.locator(selector).count()
        if count:
            return selector, count
    return "", 0


def _equipment_src(item) -> str:
    try:
        return (item.get_attribute("src") or "").strip()
    except Exception:
        try:
            return (item.locator("img").first.get_attribute("src") or "").strip()
        except Exception:
            return ""


def crawl(repository: GameDataRepository, settings) -> None:
    saved = 0
    skipped = 0
    failures = 0
    with open_page(settings) as page:
        page.goto(f"{settings.base_url}/#/quipment", timeout=30000)
        time.sleep(4)
        page.wait_for_selector(".tab-bar", timeout=10000)
        seasons = _extract_seasons(page)
        equipment_types = _extract_equipment_types(page)
        LOGGER.info("equipment seasons=%s types=%s", seasons, equipment_types)
        for season in seasons:
            if not _select_season(page, season):
                continue
            time.sleep(1)
            for equipment_type in equipment_types:
                if not _select_equipment_type(page, equipment_type):
                    failures += 1
                    continue
                crawled_ids = repository.read_crawled_ids(repository.equipment_crawled_key(season, equipment_type))
                new_ids: set[str] = set()
                selector, item_count = _find_item_selector(page)
                if not selector:
                    continue
                for index in range(item_count):
                    item = page.locator(selector).nth(index)
                    src = _equipment_src(item)
                    if not src:
                        continue
                    equip_id = src.split("/")[-1].replace(".png", "")
                    record_id = f"{season}:{equipment_type}:{equip_id}"
                    if record_id in crawled_ids or record_id in new_ids:
                        skipped += 1
                        continue
                    try:
                        item.click(timeout=3000)
                        time.sleep(1)
                    except Exception:
                        failures += 1
                        continue
                    name = first_non_empty_text(page, [".equipment-compose .name", ".equipment-name"]) or equip_id
                    desc = first_non_empty_text(page, [".equipment-compose .desc", ".equipment-compose p.desc"]) or "无描述"
                    content = (
                        f"赛季：{season}\n"
                        f"装备类型：{equipment_type}\n"
                        f"装备ID：{equip_id}\n"
                        f"装备名称：{name}\n\n"
                        f"装备描述：\n{desc}\n"
                    )
                    repository.save_equipment(season, equipment_type, name, content)
                    new_ids.add(record_id)
                    saved += 1
                if new_ids:
                    repository.write_crawled_ids(repository.equipment_crawled_key(season, equipment_type), crawled_ids | new_ids)
    LOGGER.info("equipment crawl finished: saved=%s skipped=%s failures=%s", saved, skipped, failures)
