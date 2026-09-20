import json
import logging
import re
import sys
from datetime import datetime, timezone

REDACT_KEY_PARTS = ("password", "secret", "token", "api_key", "apikey", "authorization", "cookie")
_BEARER_RE = re.compile(r"(?i)(bearer\s+)[\w\-.]+")


def _redact_string(value: str) -> str:
    return _BEARER_RE.sub(r"\1[REDACTED]", value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": _redact_string(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
