# omni-gym-worker

Thin Playwright worker for the **OmniHub** gym scheduler.

It runs on **GCP Cloud Run in `europe-southwest1` (Madrid)** because the gym website only
accepts a Spanish egress IP — it cannot run on the Hetzner host. It holds **no database and no
business logic**: it asks the Hub what to do, drives a browser, and reports raw results back.

## Contract

```
Hub  →  worker   POST /run { "job": "booking" | "scrape" | "daily" }   (X-API-Key)
worker →  Hub    GET  /api/internal/gym/work?job=booking|scrape        (X-API-Key)
worker →  Hub    GET  /api/internal/gym/credentials?accountId=…        (X-API-Key)
worker →  Hub    POST /api/internal/gym/results                        (X-API-Key)
```

- `booking` — book every due class, reporting a `started` event, then `success`/`failed` (with a
  screenshot on failure). Credentials are fetched per account from the Hub.
- `scrape` — scrape each gym's 7-day timetable and post the raw classes; the Hub resolves class
  types, diffs the timetable and sends alerts.
- `daily` — alias for `scrape` (the Hub adds the weekly report on Fridays).
- `weekly` is handled entirely in the Hub (no browser).

## Environment

| Var | Purpose |
|---|---|
| `WORKER_API_KEY` | Shared secret with the Hub (`GYM_WORKER_API_KEY`). |
| `HUB_URL` | Public Hub base URL (Tailscale Funnel). |
| `HEADLESS` | `True` in Cloud Run. |
| `PORT` | Provided by Cloud Run. |

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

`.github/workflows/deploy.yml` builds the image, pushes to Artifact Registry and deploys the
`gym-worker` Cloud Run service in `europe-southwest1`. Set GitHub secrets `GCP_SA_KEY`,
`GCP_PROJECT_ID` and Cloud Run secrets `GYM_WORKER_API_KEY` + `HUB_URL`.

Cloud Run is deployed `--allow-unauthenticated` and every request is rejected unless it carries the
correct `X-API-Key`. Upgrading to Cloud Run IAM/OIDC is the recommended next hardening step.
