import httpx

from app.config import settings
from app.logging import get_logger

logger = get_logger("hub_client")


class HubClient:
    """Thin client for the omni-hub internal gym API."""

    def __init__(self) -> None:
        if not settings.HUB_URL:
            raise RuntimeError("HUB_URL is not set")
        self.base = settings.HUB_URL.rstrip("/")

    def _headers(self) -> dict:
        return {"X-API-Key": settings.WORKER_API_KEY}

    def get_work(self, job: str) -> dict:
        response = httpx.get(
            f"{self.base}/api/internal/gym/work",
            params={"job": job},
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def get_credentials(self, account_id: str) -> dict:
        response = httpx.get(
            f"{self.base}/api/internal/gym/credentials",
            params={"accountId": account_id},
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def post_result(self, payload: dict) -> dict:
        response = httpx.post(
            f"{self.base}/api/internal/gym/results",
            json=payload,
            headers=self._headers(),
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()
