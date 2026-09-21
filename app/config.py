import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


@dataclass
class Settings:
    WORKER_API_KEY: str = os.environ.get("WORKER_API_KEY", "")
    HUB_URL: str = os.environ.get("HUB_URL", "")
    HEADLESS: bool = _as_bool(os.environ.get("HEADLESS", "True"))
    MAX_CONCURRENCY: int = int(os.environ.get("MAX_CONCURRENCY", "2"))


settings = Settings()
