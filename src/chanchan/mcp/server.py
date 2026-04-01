from __future__ import annotations

import logging

from ..repository import GameDataRepository


def _format_names(title: str, names: list[str]) -> str:
    if not names:
        return f"{title}\n\n未找到数据。"
    body = "\n".join(f"- {name}" for name in names)
    return f"{title}\n\n{body}"


def _format_equipment(items: list[tuple[str, str]], season: str, equipment_type: str = "") -> str:
    if not items:
        label = equipment_type or "全部类型"
        return f"赛季 {season} 的 {label} 装备为空。"
    lines = []
    for item_type, name in items:
        lines.append(f"- [{item_type}] {name}")
    title = f"赛季 {season} 的装备列表"
    if equipment_type:
        title = f"赛季 {season} 的 {equipment_type} 装备列表"
    return f"{title}\n\n" + "\n".join(lines)


def _format_notices(notices: list) -> str:
    if not notices:
        return "未找到公告。"
    lines = []
    for notice in notices:
        published = notice.published_at.isoformat() if notice.published_at else "未知日期"
        lines.append(f"- [{published}] {notice.title} (ID: {notice.notice_id})")
    return "公告列表\n\n" + "\n".join(lines)


def _format_balance_updates(updates: list) -> str:
    if not updates:
        return "最近时间范围内未找到平衡性调整。"
    chunks = []
    for index, update in enumerate(updates, start=1):
        lines = [f"{index}. 【{update.published_at.isoformat()}】{update.title}"]
        for change in update.changes[:5]:
            lines.append(f"   【{change.category} - {change.season}】")
            lines.append(f"   {change.content}")
        chunks.append("\n".join(lines))
    return "近期版本调整\n\n" + "\n\n".join(chunks)


def create_mcp(repository: GameDataRepository):
    from fastmcp import FastMCP

    mcp = FastMCP("金铲铲之战数据服务")

    @mcp.tool()
    def list_seasons() -> str:
        seasons = repository.list_seasons()
        return _format_names(f"共有 {len(seasons)} 个赛季", seasons)

    @mcp.tool()
    def get_hero_info(season: str, hero_name: str) -> str:
        content = repository.get_hero(season, hero_name)
        if content is None:
            return f"未找到英雄 {hero_name} 在赛季 {season} 中的数据。"
        return content

    @mcp.tool()
    def list_heroes(season: str) -> str:
        names = repository.list_heroes(season)
        return _format_names(f"赛季 {season} 的英雄列表", names)

    @mcp.tool()
    def search_heroes(season: str, keyword: str) -> str:
        names = [name for name in repository.list_heroes(season) if keyword.lower() in name.lower()]
        return _format_names(f"赛季 {season} 中匹配 {keyword} 的英雄", names)

    @mcp.tool()
    def get_trait_info(season: str, trait_name: str, trait_type: str = "特质") -> str:
        content = repository.get_trait(season, trait_type, trait_name)
        if content is None:
            return f"未找到羁绊 {trait_name}（{trait_type}）在赛季 {season} 中的数据。"
        return content

    @mcp.tool()
    def list_traits(season: str, trait_type: str = "特质") -> str:
        names = repository.list_traits(season, trait_type)
        return _format_names(f"赛季 {season} 的 {trait_type} 列表", names)

    @mcp.tool()
    def get_hex_info(season: str, hex_name: str, level: str = "英雄强化符文") -> str:
        content = repository.get_rune(season, level, hex_name)
        if content is None:
            return f"未找到强化符文 {hex_name}（{level}）在赛季 {season} 中的数据。"
        return content

    @mcp.tool()
    def list_hexs(season: str, level: str = "英雄强化符文") -> str:
        names = repository.list_runes(season, level)
        return _format_names(f"赛季 {season} 的 {level} 列表", names)

    @mcp.tool()
    def get_equipment_info(season: str, equipment_name: str, equipment_type: str = "") -> str:
        result = repository.get_equipment(season, equipment_name, equipment_type)
        if result is None:
            label = f"（{equipment_type}）" if equipment_type else ""
            return f"未找到装备 {equipment_name}{label} 在赛季 {season} 中的数据。"
        _, content = result
        return content

    @mcp.tool()
    def list_equipment(season: str, equipment_type: str = "") -> str:
        items = repository.list_equipment(season, equipment_type)
        return _format_equipment(items, season, equipment_type)

    @mcp.tool()
    def list_notices(limit: int = 10) -> str:
        return _format_notices(repository.list_notices(limit))

    @mcp.tool()
    def search_notices(keyword: str, limit: int = 10) -> str:
        return _format_notices(repository.search_notices(keyword, limit))

    @mcp.tool()
    def get_latest_balance_updates(days: int = 60, limit: int = 10) -> str:
        return _format_balance_updates(repository.latest_balance_updates(days, limit))

    return mcp


def run_server(
    repository: GameDataRepository,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    mcp = create_mcp(repository)
    if transport == "sse":
        logging.info("Starting MCP server on http://%s:%s/sse", host, port)
        mcp.run(transport="sse", host=host, port=port)
        return
    mcp.run()
