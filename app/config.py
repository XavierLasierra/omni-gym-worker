import os
from dataclasses import dataclass, field


def _as_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


def _as_int(value: str, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(low, min(high, parsed))


@dataclass
class Settings:
    WORKER_API_KEY: str = field(default_factory=lambda: os.environ.get("WORKER_API_KEY", ""))
    HUB_URL: str = field(default_factory=lambda: os.environ.get("HUB_URL", ""))
    HEADLESS: bool = field(default_factory=lambda: _as_bool(os.environ.get("HEADLESS", "True")))
    MAX_CONCURRENCY: int = field(
        default_factory=lambda: _as_int(os.environ.get("MAX_CONCURRENCY", "2"), 2, 1, 10)
    )


settings = Settings()
