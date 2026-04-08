# AirTrail Cloud Deployment Narrative

## Infrastructure Layout

Our distributed system will be deployed across several virtual machines in the cloud:

1. **VM A (Database Tier):** Hosts the PostgreSQL/PostGIS container, isolated from the public internet. Used for storing structured application data and pollution measurements.
2. **VM B (Message Bus & Cache):** Hosts RabbitMQ and Redis. Used for managing the async processing pipeline and caching spatial queries.
3. **VM C (Application Tier):** Runs the Flask API and the Streamlit Dashboard. This is the only node exposed to the public internet via Port 80/443 (proxied to internal ports).
4. **VM(s) D (Worker Tier):** Runs the Celery backend workers. These nodes grab tasks from RabbitMQ, process GPS traces against the PostGIS database, and offload results to Object Storage / Postgres.

### Storage
- An Object Storage bucket (e.g., MinIO or AWS S3) is used to persist uploaded `.csv/.gpx` traces in their raw format for batch analysis.
