# AGENTS.md

## Logging

All code logs structured JSON via `app/logging.py` — never `print`. Use
`get_logger(__name__)` and lazy `%`-style formatting for parameters.

## Layout

- `app/main.py` — FastAPI app and job orchestration (browser services are imported lazily).
- `app/hub_client.py` — calls the omni-hub internal gym API.
- `app/services/` — Playwright scrapers/bookers (browser work only).
- `app/utils/` — exceptions and string helpers.

## Rules

- Keep the worker thin: no database access, no scheduling, no message formatting. That all lives in
  the Hub.
- Never log credentials. Fetch them per account from the Hub and pass them straight to Playwright.
- Run `ruff format --check .`, `ruff check .`, and `pytest -q` before committing.
