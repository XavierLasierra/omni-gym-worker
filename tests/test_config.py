from app.config import Settings, _as_bool, _as_int


def test_as_bool():
    assert _as_bool("true") is True
    assert _as_bool("1") is True
    assert _as_bool("yes") is True
    assert _as_bool("True") is True
    assert _as_bool("false") is False
    assert _as_bool("0") is False
    assert _as_bool("") is False


def test_as_int():
    assert _as_int("5", default=2, low=1, high=10) == 5
    # below low bounds
    assert _as_int("0", default=2, low=1, high=10) == 1
    # above high bounds
    assert _as_int("15", default=2, low=1, high=10) == 10
    # ValueError fallback
    assert _as_int("invalid", default=2, low=1, high=10) == 2


def test_settings_initialization(monkeypatch):
    monkeypatch.setenv("WORKER_API_KEY", "test-key")
    monkeypatch.setenv("HUB_URL", "http://hub")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("MAX_CONCURRENCY", "4")

    s = Settings()
    assert s.WORKER_API_KEY == "test-key"
    assert s.HUB_URL == "http://hub"
    assert s.HEADLESS is False
    assert s.MAX_CONCURRENCY == 4
