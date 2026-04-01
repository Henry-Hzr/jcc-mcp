from __future__ import annotations

import logging
import time

from ..repository import GameDataRepository
from .common import first_non_empty_text, open_page, save_debug_snapshot, unique_texts, wait


LOGGER = logging.getLogger(__name__)


def _extract_seasons(page) -> list[str]:
    elements = page.locator(".tab-bar a").all()
    return unique_texts([(element.text_content() or "") for element in elements])


def _select_season(page, season: str) -> bool:
    selectors = [
        f".tab-bar a span:has-text('{season}')",
        f".tab-bar a:has-text('{season}')",
        f".tab-bar span:has-text('{season}')",
    ]
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=5000)
            return True
        except Exception:
            continue
    return False


def _open_hero_detail(page, item) -> bool:
    candidates = [item.locator(".item-inner").first, item]
    for candidate in candidates:
        try:
            candidate.click(timeout=3000)
            page.wait_for_selector(".hero-detail-wrap", timeout=8000)
            return True
        except Exception:
            pass
        try:
            candidate.click(timeout=3000, force=True)
            page.wait_for_selector(".hero-detail-wrap", timeout=8000)
            return True
        except Exception:
            pass
        try:
            page.evaluate("(element) => element.click()", candidate)
            page.wait_for_selector(".hero-detail-wrap", timeout=8000)
            return True
        except Exception:
            continue
    return False


def _extract_skill(page) -> tuple[str, str]:
    try:
        skill_elem = page.locator(".info-item").first
    except Exception:
        return "未获取到技能名称", "未获取到技能描述"
    skill_name = first_non_empty_text(skill_elem, [".skill-name"])
    skill_name = skill_name.replace("英雄技能 :", "").replace("英雄技能：", "").strip() or "未获取到技能名称"
    skill_desc = first_non_empty_text(skill_elem, [".photo-active .scroll", ".active"])
    return skill_name, skill_desc or "未获取到技能描述"


def _extract_attributes(page) -> str:
    attrs = {}
    try:
        table = page.locator(".info-item.attri table").first
        row_count = table.locator("tr").count()
        for row_index in range(row_count):
            row = table.locator("tr").nth(row_index)
            cell_count = row.locator("td").count()
            for cell_index in range(cell_count):
                cell_text = (row.locator("td").nth(cell_index).text_content() or "").strip()
                if "：" in cell_text:
                    key, value = cell_text.split("：", 1)
                    attrs[key.strip()] = value.strip()
    except Exception:
        return "未获取到属性信息"
    if not attrs:
        return "未获取到属性信息"
    return "\n".join(f"{key}：{value}" for key, value in attrs.items())


def _restore_list(page, base_url: str, season: str, page_num: int) -> bool:
    page.goto(f"{base_url}/#/hero", timeout=30000)
    time.sleep(2)
    page.wait_for_selector(".tab-bar", timeout=10000)
    if not _select_season(page, season):
        return False
    time.sleep(1)
    if page_num > 1:
        try:
            page.locator(f".page-list .page-item:has-text('{page_num}')").first.click(timeout=5000)
            time.sleep(1)
        except Exception:
            return False
    page.wait_for_selector(".list-cont .item", timeout=5000)
    return True


def crawl(repository: GameDataRepository, settings) -> None:
    saved = 0
    skipped = 0
    failures = 0
    with open_page(settings) as page:
        page.goto(f"{settings.base_url}/#/hero", timeout=30000)
        time.sleep(3)
        page.wait_for_selector(".tab-bar", timeout=10000)
        seasons = _extract_seasons(page)
        LOGGER.info("hero seasons detected: %s", seasons)
        for season in seasons:
            if not _select_season(page, season):
                LOGGER.warning("failed to switch season: %s", season)
                continue
            time.sleep(2)
            crawled_ids = repository.read_crawled_ids(repository.hero_crawled_key(season))
            new_ids: set[str] = set()
            total_pages = page.locator(".page-list .page-item").count() or 1
            for page_num in range(1, total_pages + 1):
                if page_num > 1:
                    try:
                        page.locator(f".page-list .page-item:has-text('{page_num}')").first.click(timeout=5000)
                        time.sleep(1)
                    except Exception:
                        LOGGER.warning("failed to switch hero page %s/%s for %s", page_num, total_pages, season)
                        continue
                item_count = page.locator(".list-cont .item").count()
                for index in range(item_count):
                    item = page.locator(".list-cont .item").nth(index)
                    hero_name = first_non_empty_text(item, [".hero-name", ".img-box"])
                    if not hero_name:
                        try:
                            hero_name = (item.locator(".img-box").first.get_attribute("data-name") or "").strip()
                        except Exception:
                            hero_name = ""
                    if not hero_name:
                        continue
                    hero_id = f"{season}:{hero_name}"
                    if hero_id in crawled_ids or hero_id in new_ids:
                        skipped += 1
                        continue
                    locked = False
                    try:
                        if item.locator(".icon-lock").count() > 0:
                            locked = item.locator(".icon-lock").first.is_visible()
                    except Exception:
                        locked = False
                    if not _open_hero_detail(page, item):
                        failures += 1
                        LOGGER.warning("failed to open hero detail: %s / %s", season, hero_name)
                        save_debug_snapshot(page, settings, f"hero_{season}_{hero_name}")
                        _restore_list(page, settings.base_url, season, page_num)
                        continue
                    skill_name, skill_desc = _extract_skill(page)
                    attrs = _extract_attributes(page)
                    prefix = "【需解锁】\n" if locked else ""
                    content = (
                        f"{prefix}赛季：{season}\n"
                        f"英雄名称：{hero_name}\n\n"
                        f"英雄技能：\n"
                        f"技能名称：{skill_name}\n"
                        f"技能描述：{skill_desc}\n\n"
                        f"英雄属性：\n{attrs}\n"
                    )
                    repository.save_hero(season, hero_name, content)
                    new_ids.add(hero_id)
                    saved += 1
                    if not _restore_list(page, settings.base_url, season, page_num):
                        LOGGER.warning("failed to restore hero list for %s page %s", season, page_num)
                        break
            if new_ids:
                repository.write_crawled_ids(repository.hero_crawled_key(season), crawled_ids | new_ids)
    LOGGER.info("hero crawl finished: saved=%s skipped=%s failures=%s", saved, skipped, failures)
