import pytest
import httpx
from pydantic import ValidationError

from app.hub_client import HubClient
from app.schemas import ScrapeWork, BookingWork, Credentials

def test_hub_client_init_missing_url(monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", None)
    with pytest.raises(RuntimeError, match="HUB_URL is not set"):
        HubClient()

def test_hub_client_get_scrape_work_success(respx_mock, monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", "http://test-hub")
    monkeypatch.setattr("app.config.settings.WORKER_API_KEY", "test-key")
    
    client = HubClient()
    respx_mock.get("http://test-hub/api/internal/gym/work?job=scrape").mock(
        return_value=httpx.Response(200, json={
            "gyms": [
                {
                    "id": "123",
                    "name": "My Gym",
                    "url": "http://gym.com"
                }
            ]
        })
    )
    
    work = client.get_scrape_work()
    assert isinstance(work, ScrapeWork)
    assert len(work.gyms) == 1
    assert work.gyms[0].name == "My Gym"

def test_hub_client_get_booking_work_success(respx_mock, monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", "http://test-hub")
    monkeypatch.setattr("app.config.settings.WORKER_API_KEY", "test-key")
    
    client = HubClient()
    respx_mock.get("http://test-hub/api/internal/gym/work?job=booking").mock(
        return_value=httpx.Response(200, json={
            "classesToBook": [
                {
                    "gymClassId": "cls-1",
                    "accountId": "acc-1",
                    "className": "Crossfit",
                    "classTime": "10:00:00",
                    "targetDate": "2024-01-01",
                    "gymUrl": "http://gym.com"
                }
            ]
        })
    )
    
    work = client.get_booking_work()
    assert isinstance(work, BookingWork)
    assert len(work.classesToBook) == 1
    assert work.classesToBook[0].gymClassId == "cls-1"

def test_hub_client_get_credentials_success(respx_mock, monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", "http://test-hub")
    
    client = HubClient()
    respx_mock.get("http://test-hub/api/internal/gym/credentials?accountId=acc-1").mock(
        return_value=httpx.Response(200, json={
            "username": "user",
            "password": "pwd"
        })
    )
    
    creds = client.get_credentials("acc-1")
    assert isinstance(creds, Credentials)
    assert creds.username == "user"

def test_hub_client_post_result_success(respx_mock, monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", "http://test-hub")
    client = HubClient()
    
    respx_mock.post("http://test-hub/api/internal/gym/results").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    
    result = client.post_result({"kind": "scrape"})
    assert result == {"ok": True}

def test_hub_client_invalid_payload(respx_mock, monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", "http://test-hub")
    client = HubClient()
    
    # Missing fields for Gym in ScrapeWork
    respx_mock.get("http://test-hub/api/internal/gym/work?job=scrape").mock(
        return_value=httpx.Response(200, json={"gyms": [{"invalid": "data"}]})
    )
    
    with pytest.raises(RuntimeError, match="Malformed payload from Hub"):
        client.get_scrape_work()

def test_hub_client_http_error(respx_mock, monkeypatch):
    monkeypatch.setattr("app.config.settings.HUB_URL", "http://test-hub")
    client = HubClient()
    
    respx_mock.post("http://test-hub/api/internal/gym/results").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    
    with pytest.raises(httpx.HTTPStatusError):
        client.post_result({"kind": "scrape"})
