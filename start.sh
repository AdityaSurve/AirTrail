#!/bin/bash
set -e

echo "Starting infrastructure..."
docker compose up -d postgres rabbitmq redis minio
sleep 5 # Wait for dependent services

echo "Applying migrations..."
alembic upgrade head

echo "Seeding database..."
python packages/airtrail_core/seed.py

echo "Starting application containers..."
docker compose up -d api worker dashboard

echo "AirTrail Platform is running!"
echo "API: http://localhost:5000"
echo "Dashboard: http://localhost:8501"
