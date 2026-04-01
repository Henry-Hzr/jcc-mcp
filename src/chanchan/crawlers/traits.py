from __future__ import annotations

import logging
import time

from ..repository import GameDataRepository
from .common import first_non_empty_text, open_page, unique_texts


LOGGER = logging.getLogger(__name__)


def _extract_seasons(page) -> list[str]:
    elements = page.locator(".tab-bar a").all()
    return unique_texts([(element.text_content() or "") for element in elements])


def _extract_trait_types(page) -> list[str]:
    try:
        page.locator(".component-select").first.click(timeout=3000)
        time.sleep(1)
        options = page.locator(".select-options li").all()
        values = unique_texts([(option.text_content() or "") for option in options])
        page.mouse.click(100, 100)
        return values or ["特质", "职业"]
    except Exception:
        return ["特质", "职业"]


def _select_season(page, season: str) -> bool:
    for selector in [
        f".tab-bar a span:has-text('{season}')",
        f".tab-bar a:has-text('{season}')",
    ]:
        try:
            page.locator(selector).first.click(timeout=5000)
            return True
        except Exception:
            continue
    return False


def _select_trait_type(page, trait_type: str) -> bool:
    try:
        page.locator(".component-select").first.click(timeout=3000)
        time.sleep(1)
        page.locator(f".select-options li:has-text('{trait_type}')").first.click(timeout=5000)
        time.sleep(1)
        return True
    except Exception:
        return False


def crawl(repository: GameDataRepository, settings) -> None:
    saved = 0
    skipped = 0
    failures = 0
    with open_page(settings) as page:
        page.goto(f"{settings.base_url}/#/synergy", timeout=30000)
        time.sleep(4)
        page.wait_for_selector(".tab-bar", timeout=10000)
        seasons = _extract_seasons(page)
        trait_types = _extract_trait_types(page)
        LOGGER.info("trait seasons=%s types=%s", seasons, trait_types)
        for season in seasons:
            if not _select_season(page, season):
                continue
            time.sleep(1)
            for trait_type in trait_types:
                if not _select_trait_type(page, trait_type):
                    LOGGER.warning("failed to switch trait type: %s / %s", season, trait_type)
                    continue
                crawled_ids = repository.read_crawled_ids(repository.trait_crawled_key(season, trait_type))
                new_ids: set[str] = set()
                item_count = page.locator(".swiper-slide").count()
                for index in range(item_count):
                    item = page.locator(".swiper-slide").nth(index)
                    trait_name = first_non_empty_text(item, [".synergy-name"])
                    if not trait_name:
                        try:
                            trait_name = (item.locator("img").first.get_attribute("alt") or "").strip()
                        except Exception:
                            trait_name = ""
                    if not trait_name:
                        continue
                    trait_id = f"{season}:{trait_type}:{trait_name}"
                    if trait_id in crawled_ids or trait_id in new_ids:
                        skipped += 1
                        continue
                    try:
                        item.click(timeout=3000)
                        time.sleep(1)
                    except Exception:
                        failures += 1
                        continue
                    introduce = first_non_empty_text(page, [".synergy-txt .introduce"])
                    level_info = first_non_empty_text(page, [".synergy-txt .level-list"])
                    content = (
                        f"赛季：{season}\n"
                        f"羁绊类型：{trait_type}\n"
                        f"羁绊名称：{trait_name}\n\n"
                        f"羁绊介绍：\n{introduce or '无描述'}\n\n"
                        f"羁绊层级：\n{level_info or '无层级信息'}\n"
                    )
                    repository.save_trait(season, trait_type, trait_name, content)
                    new_ids.add(trait_id)
                    saved += 1
                if new_ids:
                    repository.write_crawled_ids(repository.trait_crawled_key(season, trait_type), crawled_ids | new_ids)
    LOGGER.info("trait crawl finished: saved=%s skipped=%s failures=%s", saved, skipped, failures)
