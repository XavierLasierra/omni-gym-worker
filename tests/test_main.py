import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_run_rejects_missing_key():
    response = client.post("/run", json={"job": "booking"})
    assert response.status_code == 401

def test_run_rejects_unknown_job_with_key(monkeypatch):
    import app.config as config

    monkeypatch.setattr(config.settings, "WORKER_API_KEY", "test-key", raising=False)
    response = client.post("/run", json={"job": "nope"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 400

def test_run_scrape_success(monkeypatch):
    import app.config as config
    from app.schemas import ScrapeWork, Gym

    monkeypatch.setattr(config.settings, "WORKER_API_KEY", "test-key", raising=False)

    class MockHubClient:
        def get_scrape_work(self):
            return ScrapeWork(gyms=[Gym(id="g1", name="G1", url="http://g1.com")])
        def post_result(self, payload):
            pass

    class MockScraperService:
        def __init__(self, headless):
            pass
        def scrape_gym(self, url):
            if url == "http://g1.com":
                return True, [{"class_name": "Yoga", "day_of_week": 1, "class_time": "10:00"}]
            return False, []

    monkeypatch.setattr("app.main.HubClient", MockHubClient)
    monkeypatch.setattr("app.services.scraper.ScraperService", MockScraperService)

    response = client.post("/run", json={"job": "scrape"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["result"]) == 1
    assert data["result"][0] == {"gymId": "g1", "ok": True, "scraped": 1}

def test_run_scrape_failure(monkeypatch):
    import app.config as config
    from app.schemas import ScrapeWork, Gym

    monkeypatch.setattr(config.settings, "WORKER_API_KEY", "test-key", raising=False)

    class MockHubClient:
        def get_scrape_work(self):
            return ScrapeWork(gyms=[Gym(id="g1", name="G1", url="http://g1.com")])
        def post_result(self, payload):
            pass

    class MockScraperService:
        def __init__(self, headless):
            pass
        def scrape_gym(self, url):
            return False, []

    monkeypatch.setattr("app.main.HubClient", MockHubClient)
    monkeypatch.setattr("app.services.scraper.ScraperService", MockScraperService)

    response = client.post("/run", json={"job": "scrape"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["result"][0] == {"gymId": "g1", "ok": False, "scraped": 0}

def test_run_booking(monkeypatch):
    import app.config as config
    from app.schemas import BookingWork, DueClass, Credentials

    monkeypatch.setattr(config.settings, "WORKER_API_KEY", "test-key", raising=False)

    class MockHubClient:
        def get_booking_work(self):
            return BookingWork(classesToBook=[
                DueClass(
                    gymClassId="cls-1",
                    accountId="acc-1",
                    className="Zumba",
                    classTime="10:00:00",
                    targetDate="2024-01-01",
                    gymUrl="http://gym.com"
                )
            ])
        def get_credentials(self, acc):
            return Credentials(username="usr", password="pwd")
        def post_result(self, payload):
            pass

    class MockBookingService:
        def __init__(self, headless):
            pass
        def book_class(self, params):
            return True, "Booked", None, None

    monkeypatch.setattr("app.main.HubClient", MockHubClient)
    monkeypatch.setattr("app.services.booker.BookingService", MockBookingService)

    response = client.post("/run", json={"job": "booking"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["result"][0] == {"gymClassId": "cls-1", "success": True}

def test_run_booking_failure_with_screenshot(monkeypatch):
    import app.config as config
    from app.schemas import BookingWork, DueClass, Credentials

    monkeypatch.setattr(config.settings, "WORKER_API_KEY", "test-key", raising=False)

    class MockHubClient:
        def get_booking_work(self):
            return BookingWork(classesToBook=[
                DueClass(
                    gymClassId="cls-1",
                    accountId="acc-1",
                    className="Zumba",
                    classTime="10:00:00",
                    targetDate="2024-01-01",
                    gymUrl="http://gym.com"
                )
            ])
        def get_credentials(self, acc):
            return Credentials(username="usr", password="pwd")
        def post_result(self, payload):
            pass

    class MockBookingService:
        def __init__(self, headless):
            pass
        def book_class(self, params):
            return False, "Failed", b"fake-screenshot-data", "class_not_found"

    monkeypatch.setattr("app.main.HubClient", MockHubClient)
    monkeypatch.setattr("app.services.booker.BookingService", MockBookingService)

    response = client.post("/run", json={"job": "booking"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["result"][0] == {"gymClassId": "cls-1", "success": False}
