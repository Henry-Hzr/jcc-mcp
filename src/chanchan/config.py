from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    project_root: Path
    base_url: str
    storage_backend: str
    local_data_dir: Path
    cos_region: str
    cos_bucket: str
    cos_secret_id: str
    cos_secret_key: str
    browser_headless: bool
    browser_timeout_ms: int
    crawl_wait_seconds: float
    debug_dir: Path
    notice_max_pages: int
    notice_max_items_per_page: int

    def validate(self) -> "Settings":
        if self.storage_backend not in {"local", "cos"}:
            raise ValueError("GCC_STORAGE_BACKEND 只能是 local 或 cos")
        if self.storage_backend == "cos":
            missing = []
            if not self.cos_region:
                missing.append("GCC_COS_REGION")
            if not self.cos_bucket:
                missing.append("GCC_COS_BUCKET")
            if not self.cos_secret_id:
                missing.append("GCC_COS_SECRET_ID")
            if not self.cos_secret_key:
                missing.append("GCC_COS_SECRET_KEY")
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"COS 模式缺少环境变量: {joined}")
        return self


def load_settings() -> Settings:
    root = project_root()
    secret_id = os.getenv("GCC_COS_SECRET_ID", "").strip()
    secret_key = os.getenv("GCC_COS_SECRET_KEY", "").strip()
    default_backend = "cos" if secret_id and secret_key else "local"
    local_data_dir = Path(os.getenv("GCC_LOCAL_DATA_DIR", str(root / "data"))).expanduser()
    debug_dir = Path(os.getenv("GCC_DEBUG_DIR", str(root / "debug"))).expanduser()
    settings = Settings(
        project_root=root,
        base_url=os.getenv("GCC_BASE_URL", "https://jcc.qq.com").rstrip("/"),
        storage_backend=os.getenv("GCC_STORAGE_BACKEND", default_backend).strip().lower(),
        local_data_dir=local_data_dir,
        cos_region=os.getenv("GCC_COS_REGION", "ap-beijing").strip(),
        cos_bucket=os.getenv("GCC_COS_BUCKET", "").strip(),
        cos_secret_id=secret_id,
        cos_secret_key=secret_key,
        browser_headless=_env_bool("GCC_BROWSER_HEADLESS", True),
        browser_timeout_ms=_env_int("GCC_BROWSER_TIMEOUT_MS", 30000),
        crawl_wait_seconds=_env_float("GCC_CRAWL_WAIT_SECONDS", 1.0),
        debug_dir=debug_dir,
        notice_max_pages=_env_int("GCC_NOTICE_MAX_PAGES", 0),
        notice_max_items_per_page=_env_int("GCC_NOTICE_MAX_ITEMS_PER_PAGE", 0),
    )
    return settings.validate()
