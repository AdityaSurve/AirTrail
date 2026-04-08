# AirTrail — What to Do Next (Detailed Instructions)

This guide assumes your repo already has a **data acquisition pipeline** under `data/` (`webscrapper.py`, `daily_update.py`, HourlyData `.dat` files, monthly CSVs). The **next major effort** is building the **cloud analytics platform** (Flask, Celery, RabbitMQ, PostGIS, Redis, Streamlit, Docker, object storage) and connecting it to pollution data + GPS traces.

Use this document as a checklist. Complete phases in order unless noted.

---

## 0. Current state (baseline)

You have:

- Scripts to fetch **HourlyData** from S3-style listings.
- **Downloads** of `.dat` files and **monthly aggregated CSVs** (good raw/semi-processed inputs for the course).

You still need:

- A **serving layer** (API + dashboard).
- A **database** that understands **space and time** (PostGIS).
- **Async jobs** for heavy exposure computation.
- **Dockerized** services and a plausible **cloud deployment story**.

---

## 1. Prerequisites on your machine

1. Install **Docker Desktop** (Windows) and enable WSL2 backend if recommended.
2. Install **Python 3.11+** (you already use it for `data/`).
3. Install **Git** with LF handling for shell scripts (you have `.gitattributes` for `*.sh`).
4. Optional: **pgAdmin** or **DBeaver** to inspect PostgreSQL.

**Checkpoint:** `docker version` and `python --version` succeed.

---

## 2. Lock the v1 product scope (do this before coding the app)

Write a short **one-page spec** (can live in `docs/SCOPE_V1.md`) that freezes:

| Decision | Your v1 choice (fill in) |
|----------|---------------------------|
| GPS formats | CSV + GPX only |
| Pollutants | e.g. PM2.5 only, or PM2.5 + PM10 |
| Matching rule | e.g. nearest monitoring station within X km + nearest hour |
| CRS | WGS84 (EPSG:4326) for traces; document station CRS |
| Exposure metrics | cumulative, mean, peak; “home/campus/commute” = user-drawn polygons or labeled time windows |
| Location query | point + radius OR single polygon; time range; one pollutant at a time for demo |

**Checkpoint:** You can explain v1 in under two minutes without saying “we might also…”

---

## 3. Phase A — Repository layout for the application

Create a **separate Python package** for the web stack (keep `data/` as the ETL folder).

Suggested tree:

```text
AirTrail/
  data/                    # existing scrapers (keep)
  services/
    api/                   # Flask app
    worker/                # Celery tasks (can share code with api via parent package)
    dashboard/             # Streamlit
  packages/
    airtrail_core/         # shared: schemas, DB models, matching, exposure math
  docker/
  docs/
  docker-compose.yml
  README.md
```

**Concrete steps:**

1. Create `services/api`, `services/worker`, `services/dashboard`, `packages/airtrail_core`.
2. Add a **single** `pyproject.toml` or root `requirements.txt` listing: `flask`, `gunicorn`, `celery`, `kombu`, `redis`, `psycopg2-binary` or `asyncpg`, `geoalchemy2`, `sqlalchemy`, `alembic`, `boto3` (S3-compatible), `streamlit`, `pandas`, `pydantic`, test deps (`pytest`, `pytest-cov`).
3. Add a root **`.env.example`** with variables (no secrets): `DATABASE_URL`, `CELERY_BROKER_URL`, `REDIS_URL`, `S3_ENDPOINT`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

**Checkpoint:** `pip install -r requirements.txt` (or `pip install -e packages/airtrail_core`) works in a fresh venv.

---

## 4. Phase B — Docker Compose “full stack” locally

Goal: one command brings up **Postgres+PostGIS**, **RabbitMQ**, **Redis**, **MinIO** (or similar) for object storage, plus placeholders for API/worker/Streamlit.

**Steps:**

1. Add `docker-compose.yml` with services:
   - `postgres` — image `postgis/postgis:16-3.4` (or current stable).
   - `rabbitmq` — management plugin optional for debugging.
   - `redis`.
   - `minio` — S3-compatible; create bucket on startup via init script or document manual bucket creation.
2. Expose ports: Postgres 5432, RabbitMQ 5672 (and 15672 for UI), Redis 6379, MinIO 9000/9001.
3. Use **named volumes** for Postgres and MinIO data.
4. Document in README: `docker compose up -d`, how to open RabbitMQ UI, how to create MinIO bucket.

**Checkpoint:** You can connect to Postgres with a client; RabbitMQ and Redis accept connections; MinIO console loads.

---

## 5. Phase C — Database schema and migrations

Goal: persistent tables for traces, jobs, pollution, exposure results, with **PostGIS** types.

**Steps:**

1. In `packages/airtrail_core`, define SQLAlchemy models (or raw SQL migration files) for tables discussed in your architecture doc, minimally:
   - `gps_traces`, `processing_jobs`, `exposure_results`
   - `monitoring_sites` (or `pollution_stations`) with `geometry(Point,4326)` or `geography`
   - `pollution_observations` with `(site_id, timestamp, pollutant, value, unit)` and indexes
2. Use **Alembic** migrations; first migration enables `postgis` extension and creates tables + `GIST` index on site geometry + time indexes on observations.
3. Write a **seed script** that loads a **small** subset of your real data:
   - Either ingest from your **monthly CSV** (station id, lat/lon if you join to a station file) into `monitoring_sites` + `pollution_observations`
   - Or use a tiny CSV committed under `docs/sample_data/` for reproducibility

**Checkpoint:** After `alembic upgrade head`, you can `SELECT COUNT(*)` on observations and run a simple `ST_DWithin` query in SQL.

---

## 6. Phase D — Flask API (synchronous path first)

Goal: HTTP API that proves **upload → storage → DB row** without Celery.

**Steps:**

1. Flask app factory in `services/api/app.py`; use `gunicorn` in Docker.
2. Endpoints (v1):
   - `GET /health` — checks DB connectivity.
   - `POST /api/v1/traces` — multipart file upload; validate extension/size; stream file to **MinIO/S3**; insert `gps_traces` with `storage_uri`, `status=PENDING`.
3. Return JSON: `{ "trace_id": "...", "message": "uploaded" }`.
4. Add **structured logging** (trace id, request id).

**Checkpoint:** `curl` or Postman upload creates a row and an object in object storage.

---

## 7. Phase E — Celery + RabbitMQ worker

Goal: **async** processing path; API enqueues, worker executes.

**Steps:**

1. Celery app in `services/worker/celery_app.py` with broker URL pointing to RabbitMQ.
2. Define task `compute_exposure(trace_id)` (name can vary):
   - Load trace metadata from DB; download file from object storage.
   - Parse CSV/GPX → normalized points `(timestamp, lat, lon)` (stub parser OK at first).
   - Update `processing_jobs` state transitions: `PENDING` → `RUNNING` → `SUCCESS`/`FAILURE`.
3. Flask endpoint `POST /api/v1/traces/{id}/process` or auto-enqueue after upload — pick one for v1 and document it.
4. Endpoint `GET /api/v1/jobs/{job_id}` returns state from DB.

**Checkpoint:** Upload triggers job; worker logs show task received; job row ends in `SUCCESS` (even if matching is still a stub returning dummy exposure).

---

## 8. Phase F — Spatiotemporal matching + exposure math (core course value)

Goal: replace stubs with **real v1 logic** (single strategy, documented).

**Steps:**

1. Implement in `packages/airtrail_core/matching.py`:
   - For each GPS point (or batch), find **nearest** `monitoring_sites` within max distance using PostGIS (`<->` or `ST_DWithin`).
   - Align time: e.g. match observation at same **hour** (truncate to hour) or nearest timestamp within ±30 minutes — **document the rule in `docs/MATCHING_POLICY.md`**.
2. Implement in `packages/airtrail_core/exposure.py`:
   - Per-point matched concentration → compute **cumulative** (sum or time-weighted sum — define units in README), **mean**, **peak** (max and window).
3. Write results to `exposure_results` (and optional detail table later).
4. Add **unit tests** with synthetic points and known fake stations.

**Checkpoint:** For a toy trace and seeded data, computed metrics match hand-calculated expectations in tests.

---

## 9. Phase G — Redis caching

Goal: speed up repeated reads.

**Steps:**

1. On `GET /api/v1/traces/{id}/exposure`, check Redis key e.g. `exposure:summary:{trace_id}`.
2. On cache miss, read Postgres, populate cache with TTL (e.g. 300 seconds).
3. Invalidate or overwrite cache when a new job completes for that trace.

**Checkpoint:** Second identical GET is served from cache (log “cache hit”) or timing improves.

---

## 10. Phase H — Location-based analytics API

Goal: second main workflow without GPS upload.

**Steps:**

1. `POST /api/v1/analytics/location` with lat, lon, radius (m), time range, pollutant.
2. PostGIS query: observations from sites within radius; aggregate time series + mean, percentiles (compute in SQL or pandas).
3. “High events”: values above threshold (config constant, e.g. EPA AQI breakpoint for demo).
4. Cache with key from hashed parameters.

**Checkpoint:** Streamlit or curl returns a JSON time series for a known seeded location.

---

## 11. Phase I — Streamlit dashboard

Goal: demo UI for both workflows.

**Pages (minimal):**

1. **Upload & jobs** — file uploader; show `job_id`; poll status; link to results.
2. **Exposure results** — metrics table; line chart of matched concentration over time; map of trace (and optionally matched sites).
3. **Location explorer** — inputs for lat/lon, radius, dates; charts for trends and threshold events.

**Steps:**

1. `services/dashboard/app.py` uses `requests` or `httpx` to call Flask API (base URL from env).
2. Run Streamlit in Docker on port 8501; document URL.

**Checkpoint:** End-to-end demo: upload sample GPX/CSV → job completes → charts populate.

---

## 12. Phase J — Testing and reliability

**Steps:**

1. **Unit tests:** parsing, exposure math, cache key helpers (`pytest packages/airtrail_core/tests`).
2. **Integration test:** Docker Compose test profile or `pytest` with testcontainers (optional); or a `scripts/integration_smoke.sh` that curls health + upload.
3. **Logging:** ensure worker logs include `job_id`, `trace_id`, exception stack traces on failure.

**Checkpoint:** `pytest` passes in CI or locally; you have at least one integration smoke path documented.

---

## 13. Phase K — Cloud deployment narrative (course VMs)

You do not need full production hardening; you need a **clear story**.

**Steps:**

1. Document in `docs/DEPLOYMENT.md`:
   - VM A: Postgres (managed RDS vs container — pick one).
   - VM B: RabbitMQ + Redis (or managed ElastiCache / CloudAMQP — optional).
   - VM C: API + Streamlit behind firewall/security groups.
   - VM D: Celery workers (scale horizontally).
   - Object storage: S3 bucket; env vars on workers and API.
2. Diagram: arrows between components (reuse your architecture text).

**Checkpoint:** Someone can read `DEPLOYMENT.md` and understand where each Docker service runs in the cloud.

---

## 14. Course deliverables checklist

Before submission, ensure you have:

- [ ] `README.md` — how to run `docker compose up`, run migrations, seed data, open Streamlit.
- [ ] `docs/NEXT_STEPS.md` (this file) updated if your plan changed.
- [ ] `docs/MATCHING_POLICY.md` — frozen v1 matching rules.
- [ ] `docs/SCOPE_V1.md` — frozen scope.
- [ ] API list (OpenAPI/Swagger optional, markdown table OK).
- [ ] Demo script: sample GPS file + expected outcome.
- [ ] Short video or live demo flow (upload + location query).

---

## 15. Suggested order for the next 7 work sessions

| Session | Focus | Done when |
|--------|--------|-----------|
| 1 | Docker Compose + `.env.example` + Postgres/PostGIS running | Compose up, connect to DB |
| 2 | Alembic schema + seed pollution subset | Spatial query returns rows |
| 3 | Flask upload + MinIO + `gps_traces` row | curl upload works |
| 4 | Celery task + job status API | Worker processes stub job |
| 5 | Real matching + exposure + tests | Tests green, real metrics |
| 6 | Redis + location analytics endpoint | Cache + second workflow |
| 7 | Streamlit + README + deployment doc | Full demo path |

---

## 16. Connecting your existing `data/` pipeline to the app

Your scrapers produce **HourlyData** and **monthly CSVs**. For the app DB you typically:

1. **ETL script** (new file under `data/` or `scripts/`): read monthly CSV → dedupe → bulk insert into `pollution_observations` with correct timestamps and station foreign keys.
2. Ensure **station locations** exist in `monitoring_sites` (from your `monitoring_site_locations.csv` or similar if you use it).
3. Run ETL **after** migrations, on a schedule or manually before demos.

Do **not** point the Flask app at raw `.dat` files for every request in v1; load into PostGIS once (or incrementally) for performance and to match the course “database-centric” story.

---

## 17. If you get stuck (common blockers)

- **PostGIS distances:** use `geography` for meters-accurate distance, or `geometry` with `ST_Transform` — pick one and document.
- **Celery not consuming:** wrong `CELERY_BROKER_URL`, or worker not on same Docker network as RabbitMQ.
- **Large files:** enforce max upload size in Flask; consider simplifying demo traces.
- **Windows paths:** keep object storage URIs **S3-style keys**, not local Windows paths, inside the database.

---

When you finish a phase, add a one-line note at the bottom of this file with the date and what you completed, so your report/presentation can cite concrete progress.

---

## Progress log (optional)

| Date | Phase completed | Notes |
|------|-----------------|-------|
|      |                 |       |
