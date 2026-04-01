from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from pathlib import Path

from ..pathing import sanitize_segment


LOGGER = logging.getLogger(__name__)

DEFAULT_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1024,768",
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@contextmanager
def open_page(settings):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=settings.browser_headless,
            args=DEFAULT_BROWSER_ARGS,
        )
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        page.set_default_timeout(settings.browser_timeout_ms)
        page.set_extra_http_headers(DEFAULT_HEADERS)
        try:
            yield page
        finally:
            browser.close()


def wait(settings) -> None:
    time.sleep(settings.crawl_wait_seconds)


def unique_texts(values: list[str]) -> list[str]:
    results = []
    seen = set()
    for value in values:
        cleaned = (value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        results.append(cleaned)
    return results


def first_non_empty_text(locator, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            text = locator.locator(selector).first.text_content()
        except Exception:
            continue
        if text and text.strip():
            return text.strip()
    return ""


def click_any(page_or_locator, selectors: list[str], timeout: int = 3000) -> bool:
    for selector in selectors:
        try:
            page_or_locator.locator(selector).first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


def save_debug_snapshot(page, settings, name: str) -> None:
    settings.debug_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_segment(name) or "debug"
    html_path = Path(settings.debug_dir) / f"{safe_name}.html"
    png_path = Path(settings.debug_dir) / f"{safe_name}.png"
    try:
        html_path.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(png_path))
    except Exception as exc:
        LOGGER.warning("save debug snapshot failed: %s", exc)
