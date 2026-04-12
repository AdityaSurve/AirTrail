# AirTrail Analytics Platform
## By Aditya Surve and Jai Damani

AirTrail is a distributed pollution-exposure analytics platform. Users upload GPS traces (CSV/GPX), which are asynchronously processed against PostGIS pollution data to calculate time-weighted and peak exposure metrics, then visualized on an interactive Streamlit dashboard.

---

AirTrail is an end-to-end system for **personal pollution exposure analytics**. Users upload GPS traces (CSV with timestamps and coordinates), and the platform matches those points to nearby air-quality monitoring data, computes time-weighted and peak exposure metrics, and serves results through a REST API, a Streamlit dashboard, and a React (Vite) web client.

## What the project does

1. **Ingestion**: GPS traces are accepted via the Flask API (multipart upload). Files are stored in **MinIO** (S3-compatible object storage), metadata and job state live in **PostgreSQL** with **PostGIS**, and asynchronous work is queued on **RabbitMQ** for **Celery** workers.

2. **Processing**: Workers pull jobs from the queue, read the trace from MinIO, align points with monitoring observations (spatial matching within configurable radii), and compute exposure summaries. Results are written back to PostgreSQL.

3. **Serving**: The API exposes pollutants metadata, trace upload, job status, exposure metrics, and map-friendly point payloads. **Redis** backs caching for faster reads where used. The **Streamlit** app (`services/dashboard`) is a lightweight ops and exploration UI. The **Vite + React** app (`client/`) is the richer dashboard with maps and charts, talking to the same API.

Shared domain logic lives in `packages/airtrail_core/` (matching, exposure, models, ingestion helpers).

## Tech stack

| Layer | Technologies |
|--------|----------------|
| API | Flask, Gunicorn, SQLAlchemy, GeoAlchemy2 |
| Workers | Celery, Kombu |
| Data | PostgreSQL 16 + PostGIS, Redis, MinIO |
| Messaging | RabbitMQ (management UI on port 15672) |
| Dashboards | Streamlit + Folium; React 19 + Vite 8 + Tailwind |
| Migrations | Alembic |

## Repository layout

- `services/api/` — Flask application (`services.api.app:app`)
- `services/worker/` — Celery worker (`services.worker.celery_app`)
- `services/dashboard/` — Streamlit entrypoint (`services/dashboard/app.py`)
- `client/` — Vite + React SPA
- `packages/airtrail_core/` — Shared Python library
- `data/` — Optional scripts and sample traces for enriching/ingesting monthly station CSVs into Postgres
- `docker-compose.yml` — Full stack orchestration
- `Dockerfile` — Python 3.11 image used for API, worker, and dashboard containers

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose v2) with enough RAM for Postgres/PostGIS
- **Python 3.11+** if you run Alembic or Python services on the host
- **Node.js 20+** (recommended) and npm for the Vite client

On Windows, use **PowerShell** or **Git Bash** for the shell commands below. You do **not** need `chmod` on Windows; `start.sh` is primarily for macOS/Linux.

---

## Run everything with Docker (recommended)

This matches the automated `start.sh` flow: infrastructure first, migrations from the host, then API, worker, and Streamlit.

### Step 1 — Clone and Python environment (for migrations)

From the repository root:

```bash
python -m venv venv
```

Activate the venv (Windows PowerShell: `.\venv\Scripts\Activate.ps1`; Windows cmd: `venv\Scripts\activate.bat`; macOS/Linux: `source venv/bin/activate`).

```bash
pip install -r requirements.txt
```

### Step 2 — Environment file (optional for host tools)

For running Alembic or Python on the host against Dockerized services, copy the example env file:

```bash
copy .env.example .env
```

On macOS/Linux use `cp .env.example .env`. Values in `.env.example` already target `localhost` with Postgres on **5433** (to avoid clashing with a local PostgreSQL on 5432). Containers use the URLs defined inside `docker-compose.yml`, not `.env`.

### Step 3 — Start infrastructure containers

From the repo root:

```bash
docker compose up -d postgres rabbitmq redis minio
```

Wait until Postgres is healthy (about 5–10 seconds). The compose file maps Postgres to host port **5433** → container **5432**.

### Step 4 — Apply database migrations

With the venv activated and infrastructure running:

```bash
alembic upgrade head
```

This uses `alembic.ini` (`localhost:5433` by default).

### Step 5 — Start API, worker, and Streamlit dashboard

```bash
docker compose up -d api worker dashboard
```

Or, on macOS/Linux, after making the script executable (`chmod +x start.sh`):

```bash
./start.sh
```

`start.sh` runs steps 3–5 in order (with a short sleep after infra).

### Step 6 — Open the Streamlit app

- **Streamlit dashboard**: [http://localhost:8501](http://localhost:8501)

### Service URLs (Docker)

| Service | URL |
|---------|-----|
| Streamlit dashboard | http://localhost:8501 |
| Flask API | http://localhost:5000 |
| RabbitMQ management | http://localhost:15672 (guest / guest) |
| MinIO API | http://localhost:9000 |
| MinIO console | http://localhost:9001 (minioadmin / minioadmin) |
| Postgres (host) | `localhost:5433` (user `airtrail`, password `password`, db `airtrail`) |
| Redis | `localhost:6379` |

The API creates the default S3 bucket (`airtrail-traces` unless overridden) on startup when missing.

### Docker commands you will use often

```bash
# View logs (all services)
docker compose logs -f

# Logs for one service
docker compose logs -f api

# Stop application containers (keep data volumes)
docker compose stop api worker dashboard

# Stop everything including infra
docker compose down

# Stop and remove volumes (wipes Postgres + MinIO data)
docker compose down -v

# Rebuild images after Dockerfile or dependency changes
docker compose build --no-cache
docker compose up -d api worker dashboard
```

---

## Run the Vite (React) app locally

The SPA lives in `client/` and proxies `/api` to the Flask API during development.

### Step 1 — Install dependencies

```bash
cd client
npm install
```

### Step 2 — Environment (dev proxy)

For `npm run dev`, keep the default: **do not** set `VITE_API_BASE_URL`, so the browser calls `/api/...` and Vite proxies to `http://localhost:5000` (see `client/vite.config.js`). Optionally copy `client/.env.example` to `client/.env` and leave `VITE_API_BASE_URL` unset or commented.

If the API runs on another origin without the proxy, set:

```env
VITE_API_BASE_URL=http://127.0.0.1:5000
```

### Step 3 — Start the dev server

```bash
npm run dev
```

Open the URL printed in the terminal (typically [http://localhost:5173](http://localhost:5173)).

**Requirement**: the Flask API must be reachable at the proxied target (usually `http://localhost:5000`), e.g. via Docker `api` service or local Gunicorn/Flask as below.

### Production build (optional)

```bash
npm run build
npm run preview
```

---

## Optional: load / enrich pollution station data

Monthly CSV workflows are documented in comments inside `start.sh`. When you have data under `data/monthly_csv`, you can run from the repo root (venv activated, DB reachable):

```bash
python data/enrich_monthly_csvs_boulder_coords.py --monthly-dir data/monthly_csv
python data/ingest_monthly_csv_to_postgres.py --monthly-dir data/monthly_csv
```

Sample traces for testing uploads live under `data/sample_traces/`.

---

## Advanced: run Python services on the host (Docker infra only)

Use this when you want to debug Flask, Celery, or Streamlit outside containers while keeping Postgres, Redis, RabbitMQ, and MinIO in Docker.

1. Start infra: `docker compose up -d postgres rabbitmq redis minio`
2. `alembic upgrade head`
3. Set environment variables to match `.env.example` (`DATABASE_URL` with port **5433**, `CELERY_BROKER_URL`, `REDIS_URL`, `S3_*` for MinIO on localhost).
4. From the repo root, with `PYTHONPATH` set to the project root (Windows PowerShell: `$env:PYTHONPATH = (Get-Location).Path`):

```bash
# Terminal 1 — API
gunicorn --bind 0.0.0.0:5000 services.api.app:app

# Terminal 2 — Worker
celery -A services.worker.celery_app worker --loglevel=info

# Terminal 3 — Streamlit
set API_URL=http://localhost:5000
streamlit run services/dashboard/app.py
```

On PowerShell, use `$env:API_URL = "http://localhost:5000"` before `streamlit run ...`.

Then run `npm run dev` in `client/` as above.

---

## Testing

With the API and worker running (Docker or local), from the repo root:

```bash
pytest tests/
```

The integration test in `tests/test_integration.py` expects the API at `http://localhost:5000`.

---

## Architecture summary

1. **User interaction**: Upload GPS traces via Streamlit, the React client, or HTTP clients calling the API directly.
2. **API layer**: Flask stores objects in MinIO, records jobs in PostgreSQL, and enqueues Celery tasks on RabbitMQ.
3. **Worker layer**: Celery workers process traces, match to PostGIS-backed monitoring data, compute exposure, and persist results.
4. **Analytics retrieval**: API endpoints (and Redis where applicable) serve metrics and geometries to Streamlit and the Vite app.
