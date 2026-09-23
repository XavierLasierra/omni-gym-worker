import pytest
import logging
import json
from datetime import datetime, timezone
from app.logging import _redact_string, JsonFormatter, configure_logging, get_logger

def test_redact_string():
    assert _redact_string("Bearer my_super_secret_token") == "Bearer [REDACTED]"
    assert _redact_string("bearer ABCDEF12345") == "bearer [REDACTED]"
    assert _redact_string("password=secret123") == "password=[REDACTED]"
    assert _redact_string("Token: mytoken123") == "Token=[REDACTED]"
    assert _redact_string("This is an api_key=123 value") == "This is an api_key=[REDACTED] value"
    assert _redact_string("Safe string with no secrets") == "Safe string with no secrets"
    # Testing multiple redactions
    assert _redact_string("Bearer token and password=123") == "Bearer [REDACTED] and password=[REDACTED]"

def test_json_formatter():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Logged password=secret123",
        args=(),
        exc_info=None,
    )
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data["level"] == "info"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Logged password=[REDACTED]"
    assert "timestamp" in data
    assert "exception" not in data

def test_json_formatter_with_exception():
    formatter = JsonFormatter()
    try:
        raise ValueError("Error with Bearer secret-abc")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=10,
        msg="An error occurred",
        args=(),
        exc_info=exc_info,
    )
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data["level"] == "error"
    assert "exception" in data
    assert "Bearer [REDACTED]" in data["exception"]
    assert "secret-abc" not in data["exception"]

def test_configure_logging():
    configure_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)

def test_get_logger():
    logger = get_logger("my_logger")
    assert logger.name == "my_logger"
    assert isinstance(logger, logging.Logger)
