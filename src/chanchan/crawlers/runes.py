from __future__ import annotations

import logging
import time

from ..repository import GameDataRepository
from .common import first_non_empty_text, open_page, unique_texts


LOGGER = logging.getLogger(__name__)


def _extract_seasons(page) -> list[str]:
    elements = page.locator(".tab-bar a").all()
    return unique_texts([(element.text_content() or "") for element in elements])


def _extract_levels(page) -> list[str]:
    try:
        page.locator(".component-select").first.click(timeout=3000)
        time.sleep(1)
        options = page.locator(".select-options li").all()
        levels = unique_texts([(option.text_content() or "") for option in options])
        page.mouse.click(100, 100)
        return levels or ["一级强化符文", "二级强化符文", "三级强化符文"]
    except Exception:
        return ["一级强化符文", "二级强化符文", "三级强化符文"]


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


def _select_level(page, level: str) -> bool:
    try:
        page.locator(".component-select").first.click(timeout=3000)
        time.sleep(1)
        page.locator(f".select-options li:has-text('{level}')").first.click(timeout=5000)
        time.sleep(1)
        return True
    except Exception:
        return False


def _extract_rune_detail(page) -> str:
    selectors = [
        ".component-float-tips-slot .hex-text .desc",
        ".component-float-tips-hex .hex-text .desc",
        ".component-float-tips-slot",
        ".component-float-tips-hex",
        ".tooltip-content",
        ".rune-detail",
        ".hex-detail",
        ".detail-box",
    ]
    return first_non_empty_text(page, selectors) or "未能获取详情信息"


def crawl(repository: GameDataRepository, settings) -> None:
    saved = 0
    skipped = 0
    failures = 0
    with open_page(settings) as page:
        page.goto(f"{settings.base_url}/#/hex", timeout=30000)
        time.sleep(4)
        page.wait_for_selector(".tab-bar", timeout=10000)
        try:
            page.locator(".switch-filter-subtabs a:has-text('强化符文')").first.click(timeout=5000)
            time.sleep(1)
        except Exception:
            LOGGER.warning("failed to switch to rune tab")
        seasons = _extract_seasons(page)
        levels = _extract_levels(page)
        LOGGER.info("rune seasons=%s levels=%s", seasons, levels)
        for season in seasons:
            if not _select_season(page, season):
                continue
            time.sleep(1)
            for level in levels:
                if not _select_level(page, level):
                    failures += 1
                    continue
                crawled_ids = repository.read_crawled_ids(repository.rune_crawled_key(season, level))
                new_ids: set[str] = set()
                item_count = page.locator(".hex-table .item-box").count()
                for index in range(item_count):
                    item = page.locator(".hex-table .item-box").nth(index)
                    rune_name = first_non_empty_text(item, ["p"])
                    if not rune_name:
                        try:
                            rune_name = (item.locator("img").first.get_attribute("alt") or "").strip()
                        except Exception:
                            rune_name = ""
                    if not rune_name:
                        continue
                    rune_id = f"{season}:{level}:{rune_name}"
                    if rune_id in crawled_ids or rune_id in new_ids:
                        skipped += 1
                        continue
                    try:
                        item.hover(timeout=3000)
                        time.sleep(1)
                    except Exception:
                        try:
                            item.click(timeout=3000)
                            time.sleep(1)
                        except Exception:
                            failures += 1
                            continue
                    detail = _extract_rune_detail(page)
                    content = (
                        f"赛季：{season}\n"
                        f"强化等级：{level}\n"
                        f"强化符文名称：{rune_name}\n\n"
                        f"详细信息：\n{detail}\n"
                    )
                    repository.save_rune(season, level, rune_name, content)
                    new_ids.add(rune_id)
                    saved += 1
                    try:
                        page.mouse.move(0, 0)
                    except Exception:
                        pass
                if new_ids:
                    repository.write_crawled_ids(repository.rune_crawled_key(season, level), crawled_ids | new_ids)
    LOGGER.info("rune crawl finished: saved=%s skipped=%s failures=%s", saved, skipped, failures)
