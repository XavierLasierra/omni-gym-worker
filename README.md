# omni-gym-worker

Thin Playwright worker for the **OmniHub** gym scheduler.

It runs as the `gym-worker` service on the Omni host (Hetzner), reached by the Hub over the compose
network at `http://gym-worker:8080`. It holds **no database and no business logic**: it asks the Hub
what to do, drives a browser, and reports raw results back.

## Contract

```
Hub  →  worker   POST /run { "job": "booking" | "scrape" }   (X-API-Key)
worker →  Hub    GET  /api/internal/gym/work?job=booking|scrape   (X-API-Key)
worker →  Hub    GET  /api/internal/gym/credentials?accountId=…   (X-API-Key)
worker →  Hub    POST /api/internal/gym/results                   (X-API-Key)
```

- `booking` — book every due class, reporting a `started` event, then `success`/`failed` (with a
  screenshot on failure). Credentials are fetched per account from the Hub.
- `scrape` — scrape each gym's 7-day timetable and post the raw classes; the Hub resolves class
  types, diffs the timetable and sends alerts.
- `weekly` is handled entirely in the Hub (no browser).

## Environment

| Var | Purpose |
|---|---|
| `WORKER_API_KEY` | Shared secret with the Hub (`GYM_WORKER_API_KEY`). |
| `HUB_URL` | Hub base URL (`http://omni-hub:3000` in the compose network). |
| `HEADLESS` | `True` in production. |
| `MAX_CONCURRENCY` | Browser workers in parallel (default `2`). |

## Local run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # fill WORKER_API_KEY + HUB_URL
uvicorn app.main:app --reload --port 8080
```

## Checks

```bash
pip install ruff pytest
ruff format --check . && ruff check . && pytest -q
```

## Deploy

`.github/workflows/deploy.yml` builds and pushes `ghcr.io/xavierlasierra/omni-gym-worker:{latest,sha}`
on `main`. `omni-infra` runs it as the `gym-worker` compose service (see `docker-compose.yml`); a
deploy pulls the new `latest` image. `WORKER_API_KEY` must equal the Hub's `GYM_WORKER_API_KEY`.

Every request is rejected unless it carries the correct `X-API-Key`; the service is not published on
a host port (only reachable from the compose network).
