# AirTrail Analytics Platform
## By Aditya Surve and Jai Damani

AirTrail is a distributed pollution-exposure analytics platform. Users upload GPS traces (CSV/GPX), which are asynchronously processed against PostGIS pollution data to calculate time-weighted and peak exposure metrics, then visualized on an interactive Streamlit dashboard.

---

## Architecture & System Flow

| Layer | Component | Role |
|-------|-----------|------|
| **Frontend** | Streamlit Dashboard | Upload GPS traces, view exposure maps & analytics |
| **API** | Flask + Gunicorn | REST endpoints for trace upload, job status, result retrieval |
| **Worker** | Celery | Async GPS processing, PostGIS spatial queries, exposure calculation |
| **Broker** | RabbitMQ | Task queue between API and workers |
| **Cache** | Redis | Caching analytics results for fast dashboard reads |
| **Database** | PostgreSQL + PostGIS | Persistent storage for traces, results, and geospatial pollution data |
| **Object Storage** | MinIO (S3-compatible) | Raw GPS file storage |

### Data Flow

```
User ──▶ Streamlit Dashboard ──▶ Flask API ──▶ MinIO (store file)
                                      │
                                      ▼
                                  RabbitMQ ──▶ Celery Worker
                                                    │
                                        ┌───────────┴───────────┐
                                        ▼                       ▼
                                  PostGIS (spatial)      PostgreSQL (results)
                                                                │
                                                                ▼
                                  Redis (cache) ◀── Dashboard reads
```

---

## Prerequisites

Before deploying AirTrail, ensure the following are installed on your machine:

| Requirement | Minimum Version | Purpose |
|-------------|-----------------|---------|
| **Docker** | 20.10+ | Container runtime |
| **Docker Compose** | v2.0+ (bundled with Docker Desktop) | Multi-container orchestration |
| **Python** | 3.11+ | Local scripts, migrations, seeding |
| **Git** | 2.30+ | Cloning the repository |

> **Windows users**: Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) which includes both Docker and Docker Compose.
>
> **macOS/Linux users**: Install [Docker Desktop](https://docs.docker.com/desktop/) or Docker Engine + Compose plugin.

---

## Deployment

### Option 1 — One-Command Deploy (Recommended)

This is the fastest way to get the entire platform running.

#### Linux / macOS

```bash
# 1. Clone the repository
git clone https://github.com/AdityaSurve/AirTrail.git
cd AirTrail

# 2. Copy the environment template
cp .env.example .env

# 3. Make the start script executable and run it
chmod +x start.sh
./start.sh
```

#### Windows

```powershell
# 1. Clone the repository
git clone https://github.com/AdityaSurve/AirTrail.git
cd AirTrail

# 2. Copy the environment template
copy .env.example .env

# 3. Run initial setup (creates venv and installs dependencies)
.\setup.bat

# 4. Activate the virtual environment
.\venv\Scripts\activate

# 5. Start infrastructure services
docker compose up -d postgres rabbitmq redis minio

# 6. Wait ~10 seconds for services to initialize, then run migrations
timeout /t 10
alembic upgrade head

# 7. Seed the database with pollution data
python packages/airtrail_core/seed.py

# 8. Start application containers
docker compose up -d api worker dashboard
```

### Option 2 — Docker Compose Only (Full Containerized)

If you want everything running inside Docker with no local Python environment:

```bash
# 1. Clone and enter the project
git clone https://github.com/AdityaSurve/AirTrail.git
cd AirTrail

# 2. Copy the environment template
cp .env.example .env          # Linux/macOS
copy .env.example .env        # Windows

# 3. Build and start all services
docker compose up --build -d
```

> **Note**: When using this method, database migrations and seeding run against the containerized PostgreSQL. You may need to exec into the `api` container to run Alembic:
> ```bash
> docker compose exec api alembic upgrade head
> docker compose exec api python packages/airtrail_core/seed.py
> ```

### Option 3 — Local Development (No Docker for App Services)

For contributors who want to run the application services locally while keeping infrastructure in Docker:

```bash
# 1. Clone and enter the project
git clone https://github.com/AdityaSurve/AirTrail.git
cd AirTrail

# 2. Create and activate a Python virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
.\venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment template and configure
cp .env.example .env

# 5. Start only the infrastructure services
docker compose up -d postgres rabbitmq redis minio

# 6. Wait for services to be ready (~10 seconds), then run migrations
sleep 10                        # Linux/macOS
timeout /t 10                   # Windows
alembic upgrade head

# 7. Seed the database
python packages/airtrail_core/seed.py

# 8. Start each application service in a separate terminal:

# Terminal 1 — Flask API
gunicorn --bind 0.0.0.0:5000 services.api.app:app

# Terminal 2 — Celery Worker
celery -A services.worker.celery_app worker --loglevel=info

# Terminal 3 — Streamlit Dashboard
streamlit run services/dashboard/app.py
```

---

## Environment Configuration

Copy `.env.example` to `.env` and customize values as needed:

```ini
# Database Configuration
DATABASE_URL=postgresql://airtrail:password@localhost:5432/airtrail

# Message Broker and Cache
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
REDIS_URL=redis://localhost:6379/0

# Object Storage (MinIO)
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=airtrail-traces
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

> **Important**: When running app services inside Docker (Options 1 & 2), the `docker-compose.yml` overrides these with container-internal hostnames (e.g., `postgres` instead of `localhost`). The `.env` file is only used for **local** runs.

---

## Verifying the Deployment

After starting all services, verify everything is healthy:

| Service | URL | Expected |
|---------|-----|----------|
| **Streamlit Dashboard** | [http://localhost:8501](http://localhost:8501) | Interactive map & upload UI |
| **Flask API** | [http://localhost:5000](http://localhost:5000) | JSON API responses |
| **RabbitMQ Management** | [http://localhost:15672](http://localhost:15672) | Login with `guest` / `guest` |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | Login with `minioadmin` / `minioadmin` |

### Check running containers

```bash
docker compose ps
```

You should see all six services listed as `running`:

```
NAME           SERVICE     STATUS
airtrail-postgres-1    postgres    running
airtrail-rabbitmq-1    rabbitmq    running
airtrail-redis-1       redis       running
airtrail-minio-1       minio       running
airtrail-api-1         api         running
airtrail-worker-1      worker      running
airtrail-dashboard-1   dashboard   running
```

### Run tests

```bash
pytest tests/ -v --cov
```

---

## Exposed Ports Summary

| Port | Service | Protocol |
|------|---------|----------|
| `5000` | Flask API | HTTP |
| `5432` | PostgreSQL | TCP |
| `5672` | RabbitMQ (AMQP) | TCP |
| `6379` | Redis | TCP |
| `8501` | Streamlit Dashboard | HTTP |
| `9000` | MinIO S3 API | HTTP |
| `9001` | MinIO Web Console | HTTP |
| `15672` | RabbitMQ Management UI | HTTP |

> Ensure these ports are not in use by other applications before starting.

---

## Stopping the Platform

```bash
# Stop all services (containers remain)
docker compose stop

# Stop and remove all containers, networks, and volumes
docker compose down -v
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Port already in use** | Stop the conflicting process or change the port mapping in `docker-compose.yml` |
| **Database connection refused** | Wait 10–15 seconds after `docker compose up` for PostgreSQL to initialize |
| **Alembic migration fails** | Ensure PostgreSQL is running: `docker compose ps postgres` |
| **MinIO bucket not found** | The API auto-creates the `airtrail-traces` bucket on first upload; verify MinIO is running at `localhost:9001` |
| **Celery worker not picking up tasks** | Ensure RabbitMQ is healthy: `docker compose logs rabbitmq` |
| **Dashboard can't reach API** | When running locally, set `API_URL=http://localhost:5000`; inside Docker, the compose file handles this |
| **Docker build fails** | Run `docker compose build --no-cache` to rebuild from scratch |

---

## Project Structure

```
AirTrail/
├── services/
│   ├── api/            # Flask REST API
│   ├── worker/         # Celery async workers
│   └── dashboard/      # Streamlit UI
├── packages/
│   └── airtrail_core/  # Shared models, utilities, seed data
├── alembic/            # Database migration scripts
├── tests/              # Integration & unit tests
├── data/               # Sample GPS traces and datasets
├── docs/               # Additional documentation
├── docker-compose.yml  # Multi-service orchestration
├── Dockerfile          # Python 3.11-slim app image
├── requirements.txt    # Python dependencies
├── start.sh            # One-command Linux/macOS launcher
├── setup.bat           # Windows initial setup script
├── .env.example        # Environment variable template
└── alembic.ini         # Alembic migration configuration
```
