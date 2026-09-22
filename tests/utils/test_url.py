import pytest

from app.utils.url import is_allowed_gym_url

def test_is_allowed_gym_url_valid():
    assert is_allowed_gym_url("https://www.example.com") is True
    assert is_allowed_gym_url("http://gym-domain.com/schedule") is True
    assert is_allowed_gym_url("https://8.8.8.8") is True

def test_is_allowed_gym_url_invalid_schemes():
    assert is_allowed_gym_url("ftp://example.com") is False
    assert is_allowed_gym_url("file:///etc/passwd") is False
    assert is_allowed_gym_url("gopher://server") is False

def test_is_allowed_gym_url_ssrf_protection():
    # Localhost aliases
    assert is_allowed_gym_url("http://localhost") is False
    assert is_allowed_gym_url("http://localhost:8080") is False
    
    # Internal TLDs
    assert is_allowed_gym_url("http://service.local") is False
    assert is_allowed_gym_url("http://db.internal") is False
    
    # Private and loopback IPs
    assert is_allowed_gym_url("http://127.0.0.1") is False
    assert is_allowed_gym_url("https://10.0.0.5") is False
    assert is_allowed_gym_url("http://192.168.1.100") is False
    assert is_allowed_gym_url("http://172.16.0.1") is False
    assert is_allowed_gym_url("http://169.254.169.254") is False  # Link-local (AWS metadata)

def test_is_allowed_gym_url_malformed():
    assert is_allowed_gym_url("not a url") is False
    assert is_allowed_gym_url("") is False
    assert is_allowed_gym_url("http://") is False
