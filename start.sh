#!/bin/bash
set -e

echo "Starting infrastructure..."
docker compose up -d postgres rabbitmq redis minio
sleep 5 # Wait for dependent services

echo "Applying migrations..."
alembic upgrade head

echo "Pollution data: enrich (optional) + ingest monthly CSVs into Postgres when ready:"
echo "  python data/enrich_monthly_csvs_boulder_coords.py --monthly-dir data/monthly_csv"
echo "  python data/ingest_monthly_csv_to_postgres.py --monthly-dir data/monthly_csv"

echo "Starting application containers..."
docker compose up -d api worker dashboard

echo "AirTrail Platform is running!"
echo "API: http://localhost:5000"
echo "Dashboard: http://localhost:8501"
