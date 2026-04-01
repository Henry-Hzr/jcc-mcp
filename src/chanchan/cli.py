from __future__ import annotations

import argparse
import logging
import sys

from .config import load_settings
from .mcp.server import run_server
from .repository import GameDataRepository
from .storage import build_storage


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _build_repository() -> tuple:
    settings = load_settings()
    storage = build_storage(settings)
    repository = GameDataRepository(storage)
    return settings, repository


def _run_crawler(target: str, repository: GameDataRepository, settings) -> int:
    from .crawlers import equipment, heroes, notices, runes, traits

    runners = {
        "heroes": heroes.crawl,
        "traits": traits.crawl,
        "runes": runes.crawl,
        "equipment": equipment.crawl,
        "notices": notices.crawl,
    }
    if target == "all":
        for name in ["heroes", "traits", "runes", "equipment", "notices"]:
            logging.info("Running crawler: %s", name)
            runners[name](repository, settings)
        return 0
    runners[target](repository, settings)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="铲铲新命令行入口")
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl_parser = subparsers.add_parser("crawl", help="运行抓取器")
    crawl_parser.add_argument(
        "target",
        choices=["heroes", "traits", "runes", "equipment", "notices", "all"],
    )

    mcp_parser = subparsers.add_parser("mcp", help="启动 MCP 服务")
    mcp_parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    mcp_parser.add_argument("--host", default="127.0.0.1")
    mcp_parser.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    settings, repository = _build_repository()

    if args.command == "crawl":
        return _run_crawler(args.target, repository, settings)
    if args.command == "mcp":
        run_server(repository, transport=args.transport, host=args.host, port=args.port)
        return 0
    parser.error("未知命令")
    return 2
