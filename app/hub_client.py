import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.logging import get_logger
from app.schemas import BookingWork, Credentials, ScrapeWork

logger = get_logger("hub_client")


class HubClient:
    """Thin client for the omni-hub internal gym API."""

    def __init__(self) -> None:
        if not settings.HUB_URL:
            raise RuntimeError("HUB_URL is not set")
        self.base = settings.HUB_URL.rstrip("/")

    def _headers(self) -> dict:
        return {"X-API-Key": settings.WORKER_API_KEY}

    def _validate[T: BaseModel](self, model: type[T], data: object) -> T:
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            logger.error("invalid payload from Hub: %s", exc)
            raise RuntimeError("Malformed payload from Hub") from exc

    def get_scrape_work(self) -> ScrapeWork:
        response = httpx.get(
            f"{self.base}/api/internal/gym/work",
            params={"job": "scrape"},
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return self._validate(ScrapeWork, response.json())

    def get_booking_work(self) -> BookingWork:
        response = httpx.get(
            f"{self.base}/api/internal/gym/work",
            params={"job": "booking"},
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return self._validate(BookingWork, response.json())

    def get_credentials(self, account_id: str) -> Credentials:
        response = httpx.get(
            f"{self.base}/api/internal/gym/credentials",
            params={"accountId": account_id},
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return self._validate(Credentials, response.json())

    def post_result(self, payload: dict) -> dict:
        response = httpx.post(
            f"{self.base}/api/internal/gym/results",
            json=payload,
            headers=self._headers(),
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()
