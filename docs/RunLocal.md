# Run AirTrail locally

This guide walks through running the full stack on your machine: **PostGIS**, **RabbitMQ**, **Redis**, **MinIO**, **Flask API**, **Celery worker**, and a **dashboard**. Pollution data comes from monthly CSVs under `data/monthly_csv/` (for example `colorado_air_quality_2026_*.csv`), loaded into Postgres with the ingest script.

---

## Prerequisites

| Tool | Notes |
|------|--------|
| **Docker Desktop** (or Docker Engine + Compose) | Must be running before `docker compose` commands. |
| **Python 3.11+** | On Windows, enable **Add Python to PATH** during install. |
| **Git** | To clone the repo. |
| **Node.js 20+** (optional) | Only if you use the **React/Vite** client in `client/` instead of Streamlit. |

---

## 1. Clone and enter the repo

```bash
git clone <your-repo-url> AirTrail
cd AirTrail
```

---

## 2. Start infrastructure (database, queues, object storage)

From the **repository root** (where `docker-compose.yml` lives):

```bash
docker compose up -d postgres rabbitmq redis minio
```

Wait about **15 seconds** so Postgres finishes initializing.

### Default ports

| Service | Port | Purpose |
|---------|------|---------|
| PostGIS | **`5433` on the host** → container `5432` | `alembic.ini` and host `DATABASE_URL` use **`localhost:5433`** so you never hit a separate PostgreSQL install that already owns `5432` (common on Windows). API/worker **containers** still use hostname `postgres` and port **5432** inside Docker. |
| RabbitMQ | `5672` (AMQP), `15672` (management UI) | Celery broker |
| Redis | `6379` | Celery result backend / app cache |
| MinIO | `9000` (S3 API), `9001` (web console) | GPS trace storage (S3-compatible) |

**Postgres credentials (Docker):** user `airtrail`, password `password`, database `airtrail`. The image includes **PostGIS**.

**MinIO console:** http://localhost:9001 — login `minioadmin` / `minioadmin`.

### If `alembic` said PostGIS is missing under `C:\Program Files\PostgreSQL\...`

That means the client connected to **native PostgreSQL on your PC**, not the Docker **postgis/postgis** container. With this repo’s default **`5433`** mapping, `alembic upgrade head` should talk to Docker. Recreate the DB container after pulling changes: `docker compose up -d postgres` (or `docker compose down` then `up -d postgres`).

You can override the URL anytime: set **`DATABASE_URL`** (Alembic reads it in `alembic/env.py`).

---

## 3. Python environment and database schema

Create a venv at the repo root, install dependencies, and apply migrations **from the host** (they use `localhost:5433` → container Postgres, matching `alembic.ini`).

**Windows (cmd or PowerShell):**

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

Optional: copy `.env.example` to `.env` if you run API/worker **outside** Docker and need `DATABASE_URL`, `CELERY_BROKER_URL`, `REDIS_URL`, `S3_*` for localhost. Containers already receive these via `docker-compose.yml`.

---

## 4. Load pollution observations (monthly CSVs)

Place CSVs in `data/monthly_csv/`. The ingest script picks up:

- `colorado_air_quality_*.csv`
- `all_air_quality_data_*.csv`

CSVs must include the expected columns (see `data/ingest_monthly_csv_to_postgres.py`). If **`latitude` and `longitude` are already present**, skip the enrich step.

**Enrich** (only when coordinates are missing — rewrites CSVs in place):

```bash
python data/enrich_monthly_csvs_boulder_coords.py --monthly-dir data/monthly_csv
```

**Ingest into Postgres:**

```bash
python data/ingest_monthly_csv_to_postgres.py --monthly-dir data/monthly_csv
```

To replace previously ingested external sites and their observations:

```bash
python data/ingest_monthly_csv_to_postgres.py --monthly-dir data/monthly_csv --clear-ingested-sites
```

---

## 5. Start API, worker, and Streamlit dashboard (Docker)

```bash
docker compose up -d --build api worker dashboard
```

The first build can take several minutes.

| URL | What |
|-----|------|
| http://localhost:5000 | Flask API (health and `/api/v1/...`) |
| http://localhost:8501 | **Streamlit** dashboard (`services/dashboard/app.py`) |
| http://localhost:9001 | MinIO console |

The API creates the `airtrail-traces` bucket in MinIO on first GPS upload when needed.

---

## 6. (Optional) React dashboard in `client/`

Use this if you prefer the Vite + React UI.

1. Complete **sections 2–4** above (infra + migrations + ingest).
2. Keep **API and worker** running, e.g.:

   ```bash
   docker compose up -d --build api worker
   ```

   Do **not** need the `dashboard` service for the React app.

3. In another terminal:

   ```bash
   cd client
   npm install
   npm run dev
   ```

4. Open the URL Vite prints (usually **http://localhost:5173**). The dev server **proxies** `/api` to `http://localhost:5000` (see `client/vite.config.js`). Leave `VITE_API_BASE_URL` unset in dev unless you know you need a full origin (see `client/.env.example`).

---

## 7. One-shot helper script (Linux / macOS)

From the repo root, after Docker is installed:

```bash
chmod +x start.sh
./start.sh
```

This brings up infra, runs `alembic upgrade head`, then starts `api`, `worker`, and `dashboard`. You still run **enrich** and **ingest** yourself when CSVs are ready (commands are echoed by the script).

---

## 8. Useful commands

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f worker
docker compose down              # stop app containers; add -v to drop volumes (wipes DB)
```

---

## 9. Troubleshooting

**`docker compose --build` sits on “load build context” for minutes**

- The daemon uploads the whole project directory (minus `.dockerignore`). **`client/node_modules`** alone is often hundreds of MB. That folder is listed in `.dockerignore` so API/worker images stay small; if you add other huge trees, exclude them too.

**`role "airtrail" does not exist` or migrations connect to the wrong Postgres**

- Ensure Docker Postgres is reachable on **`localhost:5433`**, or set **`DATABASE_URL`** / edit `alembic.ini` to match your `docker-compose.yml` host port.
- To reset Docker Postgres data: `docker compose down`, remove volume `postgres_data` (e.g. `docker volume rm airtrail_postgres_data`), then `docker compose up -d postgres` and wait before `alembic upgrade head`.

**`permission denied for schema public` (PostgreSQL 15+)**

- On a **native** Postgres install, as superuser:  
  `ALTER DATABASE airtrail OWNER TO airtrail;`  
  or  
  `GRANT ALL ON SCHEMA public TO airtrail;`  
  then rerun `alembic upgrade head`.

**`extension "postgis" is not available`**

- You are on **plain PostgreSQL** without PostGIS. Prefer the **Docker** `postgis/postgis` image, or install PostGIS for your server version and run `CREATE EXTENSION postgis;` in the `airtrail` database.

**Re-ingested CSVs but the dashboard still shows old numbers**

- Ingest must target the **same database** the API uses: from the host, `DATABASE_URL` should point at Docker Postgres (**`localhost:5433`** by default in this repo), not a different PostgreSQL install.
- Re-run: `python data/ingest_monthly_csv_to_postgres.py --monthly-dir data/monthly_csv` — ingest **updates** existing rows when site + timestamp + pollutant match (so regenerated Colorado CSVs overwrite old values).
- Location analytics are cached in **Redis** for about **5 minutes**. To clear immediately:  
  `docker compose exec redis redis-cli FLUSHDB`
- Hard-refresh the browser (or disable cache) on the Vite app.

**Celery tasks never finish**

- Confirm `worker` is running: `docker compose ps` and `docker compose logs worker`.
- Confirm RabbitMQ and Redis are up and URLs match `docker-compose.yml`.

---

## 10. What each piece does (short)

- **PostGIS** — monitoring sites and `pollution_observations` time series.
- **MinIO** — raw GPS trace files (S3 API).
- **API** — uploads, trace metadata, exposure/matching endpoints used by the dashboards.
- **Worker** — reads traces from MinIO, runs matching against observations, writes results back.

For a full reset of application data in Docker Postgres, stop containers, remove the `postgres_data` volume, bring Postgres back up, run `alembic upgrade head`, then ingest CSVs again.
