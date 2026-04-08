# AirTrail API Contract

## 1. System Health
`GET /health`
Validates connectivity to database.
**Response**: `{"status": "ok", "db": "connected"}`

## 2. Upload GPS Trace
`POST /api/v1/traces`
Uploads a `.csv` or `.gpx` file via multipart form.
**Request**: `multipart/form-data` with key `file`
**Response (201)**: `{"trace_id": 1, "job_id": 1, "message": "uploaded and queued"}`

## 3. Job Status
`GET /api/v1/jobs/{job_id}`
Retrieves async job processing status.
**Response**: `{"job_id": 1, "status": "SUCCESS|PENDING|RUNNING|FAILURE", "error": null}`

## 4. Exposure Analytics
`GET /api/v1/traces/{trace_id}/exposure`
Retrieves cumulative, mean, and peak metrics for a processed trace.
**Response**: `{"cumulative": 154.5, "mean": 12.3, "peak": 25.4}`

## 5. Location Analytics
`POST /api/v1/analytics/location`
Extracts location trends.
**Payload**: `{"lat": 37.77, "lon": -122.41, "radius_m": 5000}`
**Response**: `{"status": "ok", "average": 15.2, "trend": [12, 14, 15]}`
