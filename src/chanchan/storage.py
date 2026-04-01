from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .config import Settings


class StorageBackend(ABC):
    @abstractmethod
    def read_text(self, key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def write_text(self, key: str, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def list_directories(self, prefix: str = "") -> list[str]:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        target = (self.root / key.replace("/", "\\")).resolve()
        target.relative_to(self.root)
        return target

    def read_text(self, key: str) -> str | None:
        path = self._resolve(key)
        if not path.exists() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def write_text(self, key: str, content: str) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self._resolve(prefix) if prefix else self.root
        if not base.exists():
            return []
        if base.is_file():
            return [str(base.relative_to(self.root)).replace("\\", "/")]
        results = []
        for file_path in base.rglob("*"):
            if file_path.is_file():
                results.append(str(file_path.relative_to(self.root)).replace("\\", "/"))
        return sorted(results)

    def list_directories(self, prefix: str = "") -> list[str]:
        base = self._resolve(prefix) if prefix else self.root
        if not base.exists() or not base.is_dir():
            return []
        return sorted(path.name for path in base.iterdir() if path.is_dir())


class CosStorage(StorageBackend):
    def __init__(self, settings: Settings) -> None:
        from qcloud_cos import CosConfig, CosS3Client

        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
        )
        self.bucket = settings.cos_bucket
        self.client = CosS3Client(config)

    def read_text(self, key: str) -> str | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception:
            return None
        return response["Body"].get_raw_stream().read().decode("utf-8")

    def write_text(self, key: str, content: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content.encode("utf-8"))

    def list_keys(self, prefix: str = "") -> list[str]:
        response = self.client.list_objects(Bucket=self.bucket, Prefix=prefix or "")
        keys = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            keys.append(key)
        return sorted(keys)

    def list_directories(self, prefix: str = "") -> list[str]:
        normalized = prefix.strip("/")
        cos_prefix = f"{normalized}/" if normalized else ""
        response = self.client.list_objects(
            Bucket=self.bucket,
            Prefix=cos_prefix,
            Delimiter="/",
        )
        directories = []
        for item in response.get("CommonPrefixes", []):
            child = item["Prefix"].rstrip("/").split("/")[-1]
            if child:
                directories.append(child)
        return sorted(directories)


def build_storage(settings: Settings) -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalStorage(settings.local_data_dir)
    return CosStorage(settings)
