import base64
import secrets

from fastapi import FastAPI, Header, HTTPException

from app.config import settings
from app.hub_client import HubClient
from app.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("main")

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
    if job in ("scrape", "daily"):
        return {"status": "success", "result": _run_scrape()}
    raise HTTPException(status_code=400, detail="Unknown job")


def _run_scrape() -> list:
    from app.services.scraper import ScraperService

    hub = HubClient()
    work = hub.get_work("scrape")
    scraper = ScraperService(headless=settings.HEADLESS)

    summary = []
    for gym in work.get("gyms", []):
        success, classes = scraper.scrape_gym(gym["url"])
        if not success:
            summary.append({"gymId": gym["id"], "ok": False, "scraped": 0})
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
        hub.post_result({"kind": "scrape", "gymId": gym["id"], "classes": mapped})
        summary.append({"gymId": gym["id"], "ok": True, "scraped": len(mapped)})

    return summary


def _run_booking() -> list:
    from app.services.booker import BookingService

    hub = HubClient()
    work = hub.get_work("booking")
    booker = BookingService(headless=settings.HEADLESS)

    summary = []
    for item in work.get("classesToBook", []):
        class_id = item["gymClassId"]
        target_date = item["targetDate"]

        credentials = hub.get_credentials(item["accountId"])
        hub.post_result(
            {"kind": "booking", "events": [{"classId": class_id, "targetDate": target_date, "phase": "started"}]}
        )

        success, message, screenshot = booker.book_class(
            {
                "gym_url": item["gymUrl"],
                "gym_username": credentials["username"],
                "gym_password": credentials["password"],
                "class_name": item["className"],
                "class_time": item["classTime"],
                "target_date": target_date,
                "booking_window_hours": item.get("bookingWindowHours", 48),
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
        summary.append({"gymClassId": class_id, "success": success})

    return summary
