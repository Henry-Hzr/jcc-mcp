from __future__ import annotations

import logging
import re
import time

from ..repository import GameDataRepository
from .common import first_non_empty_text, open_page


LOGGER = logging.getLogger(__name__)


def _clean_notice_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"We're sorry but.*?Please enable it to continue\.", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"英雄联盟云顶之弈正版授权手游.*?用户反馈", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"查看版权信息.*?腾讯公司版权所有", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"COPYRIGHT © .*?ALL RIGHTS RESERVED", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _read_notice_detail(page) -> str:
    selectors = [
        ".detail-container",
        ".article-content",
        ".news-content",
        ".content",
        ".detail-content",
        "article",
        ".detail",
        ".main-content",
        ".rich-text",
        ".news-detail",
    ]
    detail = first_non_empty_text(page, selectors)
    if detail:
        return _clean_notice_text(detail)
    try:
        body_text = page.locator("body").text_content() or ""
    except Exception:
        body_text = ""
    return _clean_notice_text(body_text) or "无法获取详情内容"


def crawl(repository: GameDataRepository, settings) -> None:
    saved = 0
    skipped = 0
    failures = 0
    with open_page(settings) as page:
        page.goto(f"{settings.base_url}/#/news", timeout=30000)
        time.sleep(3)
        page.wait_for_selector(".news-list", timeout=10000)
        crawled_ids = repository.read_crawled_ids(repository.notices_crawled_key())
        new_ids: set[str] = set()
        try:
            total_pages = int((page.locator(".sum-total").text_content() or "1").strip())
        except Exception:
            total_pages = 1
        if settings.notice_max_pages > 0:
            total_pages = min(total_pages, settings.notice_max_pages)
        LOGGER.info(
            "notice crawl starting: pages=%s max_items_per_page=%s",
            total_pages,
            settings.notice_max_items_per_page,
        )
        for page_num in range(1, total_pages + 1):
            if page_num > 1:
                try:
                    page.locator(f"li.page-item:text-is('{page_num}')").click(timeout=5000)
                    time.sleep(2)
                except Exception:
                    LOGGER.warning("failed to switch notice page: %s", page_num)
                    break
            item_count = page.locator(".news-list li").count()
            if settings.notice_max_items_per_page > 0:
                item_count = min(item_count, settings.notice_max_items_per_page)
            LOGGER.info("processing notice page %s with %s items", page_num, item_count)
            for index in range(item_count):
                item = page.locator(".news-list li").nth(index)
                try:
                    link = item.locator("a[href*='#/news/']").first
                    href = link.get_attribute("href") or ""
                    news_id = href.split("#/news/")[-1].strip()
                    title = first_non_empty_text(item, [".title"]) or "未知标题"
                    published = first_non_empty_text(item, [".date"]) or "未知日期"
                except Exception:
                    failures += 1
                    continue
                if not news_id:
                    continue
                if news_id in crawled_ids or news_id in new_ids:
                    skipped += 1
                    continue
                try:
                    link.click(timeout=5000)
                    time.sleep(2)
                except Exception:
                    failures += 1
                    continue
                detail = _read_notice_detail(page)
                content = (
                    f"标题：{title}\n"
                    f"日期：{published}\n"
                    f"ID：{news_id}\n\n"
                    f"{detail}\n"
                )
                repository.save_notice(f"{published}_{news_id}.txt", content)
                new_ids.add(news_id)
                saved += 1
                page.goto(f"{settings.base_url}/#/news", timeout=30000)
                time.sleep(2)
                try:
                    page.wait_for_selector(".news-list", timeout=10000)
                    if page_num > 1:
                        page.locator(f"li.page-item:text-is('{page_num}')").click(timeout=5000)
                        time.sleep(1)
                except Exception:
                    failures += 1
                    break
        if new_ids:
            repository.write_crawled_ids(repository.notices_crawled_key(), crawled_ids | new_ids)
    LOGGER.info("notice crawl finished: saved=%s skipped=%s failures=%s", saved, skipped, failures)
