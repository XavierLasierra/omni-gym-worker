import base64
import secrets
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, Header, HTTPException

from app.config import settings
from app.hub_client import HubClient
from app.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("main")

import logging

class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.args and len(record.args) >= 3 and record.args[2] != "/"

logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

app = FastAPI(title="Omni Gym Worker")


def _require_key(api_key: str | None) -> None:
    if not settings.WORKER_API_KEY or not secrets.compare_digest(api_key or "", settings.WORKER_API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run")
def run(payload: dict, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
    _require_key(x_api_key)
    job = (payload or {}).get("job")

    if job == "booking":
        return {"status": "success", "result": _run_booking()}
    if job == "scrape":
        return {"status": "success", "result": _run_scrape()}
    raise HTTPException(status_code=400, detail="Unknown job")


def _run_scrape() -> list:
    from app.services.scraper import ScraperService

    hub = HubClient()
    work = hub.get_scrape_work()
    scraper = ScraperService(headless=settings.HEADLESS)

    summary = []
    for gym in work.gyms:
        success, classes = scraper.scrape_gym(gym.url)
        if not success:
            summary.append({"gymId": gym.id, "ok": False, "scraped": 0})
            continue

        mapped = [
            {
                "className": item["class_name"],
                "dayOfWeek": item["day_of_week"],
                "classTime": item["class_time"],
                "monitor": item.get("monitor") or None,
            }
            for item in classes
        ]
        hub.post_result({"kind": "scrape", "gymId": gym.id, "classes": mapped})
        summary.append({"gymId": gym.id, "ok": True, "scraped": len(mapped)})

    return summary


def _run_booking() -> list:
    from app.services.booker import BookingService

    hub = HubClient()
    work = hub.get_booking_work()
    booker = BookingService(headless=settings.HEADLESS)

    def process_item(item):
        class_id = item.gymClassId
        target_date = item.targetDate

        credentials = hub.get_credentials(item.accountId)
        hub.post_result(
            {"kind": "booking", "events": [{"classId": class_id, "targetDate": target_date, "phase": "started"}]}
        )

        success, message, screenshot = booker.book_class(
            {
                "gym_url": item.gymUrl,
                "gym_username": credentials.username,
                "gym_password": credentials.password,
                "class_name": item.className,
                "class_time": item.classTime,
                "target_date": target_date,
                "booking_window_hours": item.bookingWindowHours,
            }
        )

        event = {
            "classId": class_id,
            "targetDate": target_date,
            "phase": "success" if success else "failed",
            "message": message,
        }
        if screenshot:
            event["screenshotBase64"] = base64.b64encode(screenshot).decode()
        hub.post_result({"kind": "booking", "events": [event]})
        return {"gymClassId": class_id, "success": success}

    summary = []
    with ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENCY) as executor:
        futures = [executor.submit(process_item, item) for item in work.classesToBook]
        for future in as_completed(futures):
            summary.append(future.result())
            
    return summary
