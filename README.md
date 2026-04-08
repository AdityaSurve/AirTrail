# AirTrail Analytics Platform

## Architecture & System Flow

1. **User Interaction**: Users upload GPS traces (CSV/GPX) via the Streamlit dashboard or raw API.
2. **API layer**: Flask receives the trace, stores it securely into **MinIO** object storage, logs it in **PostgreSQL**, and places an async task ID via **RabbitMQ** to celery worker pools.
3. **Worker layer**: **Celery** workers ingest the task, pull the GPS file, filter noisy data, and query **PostGIS** matching parameters (within 5km radiuses) for nearest pollution nodes. Calculates time-weighted and peak exposure. Results are stored back in PostgreSQL.
4. **Analytics Retrieval**: Real-time read operations utilizing **Redis** caching to supply rapid map visualizations back to Streamlit endpoints.

## Runnable System Instructions
Before running AirTrail, assure Docker Desktop and Python 3.11+ are installed locally.
1. Make `start.sh` executable by running `chmod +x start.sh`, or execute the `.bat` pipeline directly.
2. Ensure you have activated your local Python virtual environment matching `requirements.txt`.
3. Launch entire infrastructure and apps with `./start.sh`!
4. The dashboard is accessible via `http://localhost:8501`.
