# Scoop — Australian Liquor Price Search (POC)

Compares current prices across major Australian liquor retailers
(Dan Murphy's, BWS, Liquorland) for a given product + postcode, with
location-aware pricing, volume normalization, and $/L calculation.

## Stack

- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy / Alembic / PostgreSQL
- **Frontend**: React / TypeScript / Vite / Tailwind / shadcn/ui
- **Deploy**: Docker Compose

## Quick start (Docker Compose)

Requires Docker Desktop (or compatible engine) to be running.

```bash
cp .env.example .env
docker compose up -d --build
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Local dev (without Docker)

If Docker isn't available, both services run natively:

Backend:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # MSYS bash on Windows
pip install -r requirements.txt
DATABASE_URL=sqlite:///./data/scoop.db alembic upgrade head
DATABASE_URL=sqlite:///./data/scoop.db python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
VITE_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

## How the scrapers work

Each retailer is implemented as an async adapter behind a common
`RetailerScraper` interface (see `backend/app/scrapers/base.py`).
Adapters use the cheapest available method:

- **Liquorland** (Coles group): parses `__NEXT_DATA__` from the
  Next.js SSR'd search page (`/search/products?q=...`). Returns
  embedded JSON with prices, was/now, comparable $/L, and volume.
- **BWS** (Endeavour group): JSON `POST` to `api.bws.com.au/apis/ui/`.
- **Dan Murphy's** (Endeavour group): JSON `POST` to
  `api.danmurphys.com.au/apis/ui/`.

All other pages and search behaviour (filters, sorting, deep linking)
work against the unified `GET /api/search` endpoint.

## Acceptance test

The POC is successful when the acceptance criteria in the brief are met:
search "jack daniels" + postcode 4000 returns results from at least two
retailers with retail price, $/L, and a clear "cheapest" indicator.

## Limitations

- POC only — no auth, no scheduling, no cache pre-warming.
- Some retailers may rate-limit or change endpoints.
- Location context is best-effort; the brief is explicit that
  comparing materially different location contexts should be flagged.

### Retailer coverage (verified Aug 2026)

| Retailer    | Status     | Notes |
|-------------|-----------|-------|
| **BWS**     | ✅ Working | `POST api.bws.com.au/apis/ui/Search/Products` returns nested products with prices, sale state, brand, package size, URL slug. |
| **Liquorland** | ⚠️ Blocked from this server | `coles.com.au/search/products` is Incapsula-bot-blocked from this IP. The adapter is wired and tested against a saved fixture, but live scraping requires a residential proxy or browser session. |
| **Dan Murphy's** | ⚠️ Partially wired | `POST api.danmurphys.com.au/apis/ui/Search/Products` returns 200 but the payload doesn't include the `query` filter — DM's frontend builds the request dynamically. The adapter surfaces this as a `ScraperError` in the `errors` array, satisfying the brief's failure-isolation requirement. |

When Liquorland or DM are blocked, the search still succeeds — the
`errors` array in the response names the failed retailers, and the UI
shows an `Alert` so the user knows some results are missing. This
matches the brief's explicit "Failure isolation" requirement: one
broken retailer must not break the overall search.