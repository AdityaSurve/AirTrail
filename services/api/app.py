from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import boto3
import uuid
import hashlib
import json
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from packages.airtrail_core.models import Base, GPSTrace, ProcessingJob, JobStatus, ExposureResult
from packages.airtrail_core.constants import (
    MONITORED_POLLUTANTS,
    POLLUTANT_META,
    parse_pollutant_param,
    pollutant_sql_in_clause,
)
from werkzeug.utils import secure_filename
from services.worker.celery_app import compute_exposure

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://airtrail:password@localhost:5433/airtrail")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET", "airtrail-traces")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
cache = redis.from_url(REDIS_URL)

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

def _parse_iso_dt(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.route("/api/v1/meta/pollutants", methods=["GET"])
    def meta_pollutants():
        items = []
        for p in MONITORED_POLLUTANTS:
            meta = POLLUTANT_META.get(p, {})
            items.append(
                {
                    "id": p,
                    "unit": meta.get("unit", "µg/m³"),
                    "who_guideline": meta.get("who_guideline"),
                    "who_note": meta.get("who_note", ""),
                }
            )
        return jsonify({"pollutants": items})

    @app.route("/api/v1/meta/observations_bounds", methods=["GET"])
    def meta_observations_bounds():
        """Min/max timestamp across pollution_observations (UTC naive from DB → ISO Z)."""
        session = Session()
        try:
            row = session.execute(
                text("SELECT MIN(o.timestamp), MAX(o.timestamp) FROM pollution_observations o")
            ).fetchone()
            if not row or row[0] is None or row[1] is None:
                return jsonify({"start": None, "end": None})
            t0, t1 = row[0], row[1]

            def _iso_z(dt):
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt.isoformat() + "Z"

            return jsonify({"start": _iso_z(t0), "end": _iso_z(t1)})
        finally:
            session.close()

    @app.route("/health")
    def health():
        try:
            with engine.connect() as _:
                return jsonify({"status": "ok", "db": "connected"})
        except Exception as e:
            return jsonify({"status": "error", "db": str(e)}), 500

    @app.route("/api/v1/traces", methods=["POST"])
    def upload_trace():
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
            
        filename = secure_filename(file.filename)
        object_name = f"{uuid.uuid4()}_{filename}"

        raw_poll = request.form.get("pollutant") or request.args.get("pollutant")
        pollutant, p_err = parse_pollutant_param(raw_poll)
        if p_err:
            return jsonify({"error": p_err}), 400

        try:
            try:
                s3.head_bucket(Bucket=S3_BUCKET)
            except Exception:
                s3.create_bucket(Bucket=S3_BUCKET)
                
            s3.upload_fileobj(file, S3_BUCKET, object_name)
            storage_uri = f"s3://{S3_BUCKET}/{object_name}"
            
            session = Session()
            trace = GPSTrace(storage_uri=storage_uri, pollutant=pollutant)
            session.add(trace)
            session.commit()
            
            job = ProcessingJob(trace_id=trace.id, status=JobStatus.PENDING)
            session.add(job)
            session.commit()
            
            trace_id = trace.id
            job_id = job.id
            session.close()
            
            # Enqueue to Celery
            compute_exposure.delay(job_id)
            
            return jsonify(
                {
                    "trace_id": trace_id,
                    "job_id": job_id,
                    "pollutant": pollutant,
                    "message": "uploaded and queued",
                }
            ), 201
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/v1/jobs/<int:job_id>", methods=["GET"])
    def get_job(job_id):
        session = Session()
        job = session.query(ProcessingJob).get(job_id)
        session.close()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify({"job_id": job.id, "status": job.status.value, "error": job.error_message})
        
    @app.route("/api/v1/traces/<int:trace_id>/exposure", methods=["GET"])
    def get_trace_exposure(trace_id):
        cache_key = f"exposure:v2:{trace_id}"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))
            
        session = Session()
        try:
            trace = session.get(GPSTrace, trace_id)
            res = session.query(ExposureResult).filter_by(trace_id=trace_id).first()
            if not res or not trace:
                return jsonify({"error": "Results not ready or trace not found"}), 404
            p = trace.pollutant or "PM2.5"
            meta = POLLUTANT_META.get(p, {})
            data = {
                "cumulative": res.cumulative_exposure,
                "mean": res.mean_exposure,
                "peak": res.peak_exposure,
                "pollutant": p,
                "unit": meta.get("unit", "µg/m³"),
                "who_guideline": meta.get("who_guideline"),
                "who_note": meta.get("who_note", ""),
            }
            cache.setex(cache_key, 300, json.dumps(data))
            return jsonify(data)
        finally:
            session.close()

    @app.route("/api/v1/traces/<int:trace_id>/exposure/points", methods=["GET"])
    def get_exposure_points(trace_id):
        start = _parse_iso_dt(request.args.get("start"))
        end = _parse_iso_dt(request.args.get("end"))
        session = Session()
        try:
            trace = session.get(GPSTrace, trace_id)
            if not trace:
                return jsonify({"error": "Trace not found"}), 404
            sql = """
                SELECT ST_Y(e.location::geometry) AS lat,
                       ST_X(e.location::geometry) AS lon,
                       e.timestamp,
                       e.matched_site_id,
                       e.matched_concentration,
                       ms.name AS site_name
                FROM exposure_points e
                LEFT JOIN monitoring_sites ms ON ms.id = e.matched_site_id
                WHERE e.trace_id = :tid
            """
            params = {"tid": trace_id}
            if start is not None:
                sql += " AND e.timestamp >= :start"
                params["start"] = start
            if end is not None:
                sql += " AND e.timestamp <= :end"
                params["end"] = end
            sql += " ORDER BY e.timestamp"
            rows = session.execute(text(sql), params).fetchall()
            points = []
            for r in rows:
                ts = r[2]
                points.append(
                    {
                        "lat": float(r[0]) if r[0] is not None else None,
                        "lon": float(r[1]) if r[1] is not None else None,
                        "timestamp": ts.isoformat() if ts else None,
                        "matched_site_id": r[3],
                        "matched_concentration": float(r[4]) if r[4] is not None else None,
                        "site_name": r[5],
                    }
                )
            bounds = session.execute(
                text(
                    "SELECT MIN(e.timestamp), MAX(e.timestamp) FROM exposure_points e WHERE e.trace_id = :tid"
                ),
                {"tid": trace_id},
            ).fetchone()
            p = trace.pollutant or "PM2.5"
            meta = POLLUTANT_META.get(p, {})
            tb = None
            if bounds and bounds[0] and bounds[1]:
                tb = {"start": bounds[0].isoformat(), "end": bounds[1].isoformat()}
            return jsonify(
                {
                    "points": points,
                    "pollutant": p,
                    "unit": meta.get("unit", "µg/m³"),
                    "who_guideline": meta.get("who_guideline"),
                    "who_note": meta.get("who_note", ""),
                    "time_bounds": tb,
                }
            )
        finally:
            session.close()

    @app.route("/api/v1/analytics/location", methods=["POST"])
    def location_analytics():
        params = request.json
        if not params:
            return jsonify({"error": "No JSON payload"}), 400

        try:
            lat = float(params["lat"])
            lon = float(params["lon"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "lat and lon are required numbers"}), 400

        start = _parse_iso_dt(params.get("start"))
        end = _parse_iso_dt(params.get("end"))
        if start is None or end is None:
            return jsonify({"error": "start and end ISO datetimes are required"}), 400
        if start > end:
            return jsonify({"error": "start must be before end"}), 400

        raw_p = params.get("pollutant")
        pollutant, p_err = parse_pollutant_param(raw_p if raw_p is not None else "")
        if p_err:
            return jsonify({"error": p_err}), 400

        radius_m = int(params.get("radius_m", 5000))
        param_hash = hashlib.md5(
            json.dumps(
                {
                    "lat": lat,
                    "lon": lon,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "radius_m": radius_m,
                    "pollutant": pollutant,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        cache_key = f"loc_analytics:{param_hash}"

        cached = cache.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))

        session = Session()
        poll_in, poll_bind = pollutant_sql_in_clause(pollutant)
        loc_params = {
            "lat": lat,
            "lon": lon,
            "radius": radius_m,
            "t0": start,
            "t1": end,
            **poll_bind,
        }
        try:
            agg = session.execute(
                text(
                    f"""
                    SELECT AVG(o.value) AS avg_val, COUNT(o.id) AS n
                    FROM pollution_observations o
                    JOIN monitoring_sites s ON s.id = o.site_id
                    WHERE ST_DWithin(
                        s.location::geography,
                        ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography,
                        :radius
                    )
                      AND o.timestamp >= :t0 AND o.timestamp <= :t1
                      AND o.pollutant IN ({poll_in})
                    """
                ),
                loc_params,
            ).fetchone()

            series_rows = session.execute(
                text(
                    f"""
                    SELECT date_trunc('hour', o.timestamp) AS hr, AVG(o.value) AS v
                    FROM pollution_observations o
                    JOIN monitoring_sites s ON s.id = o.site_id
                    WHERE ST_DWithin(
                        s.location::geography,
                        ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography,
                        :radius
                    )
                      AND o.timestamp >= :t0 AND o.timestamp <= :t1
                      AND o.pollutant IN ({poll_in})
                    GROUP BY 1
                    ORDER BY 1
                    """
                ),
                loc_params,
            ).fetchall()

            avg_val = float(agg[0]) if agg and agg[0] is not None else None
            n = int(agg[1]) if agg and agg[1] is not None else 0
            series = [
                {"t": r[0].isoformat() if r[0] else None, "value": float(r[1]) if r[1] is not None else None}
                for r in series_rows
            ]
            meta = POLLUTANT_META.get(pollutant, {})
            data = {
                "status": "ok",
                "average": avg_val,
                "observation_count": n,
                "radius_m": radius_m,
                "pollutant": pollutant,
                "unit": meta.get("unit", "µg/m³"),
                "who_guideline": meta.get("who_guideline"),
                "who_note": meta.get("who_note", ""),
                "series": series,
            }
            cache.setex(cache_key, 300, json.dumps(data))
            return jsonify(data)
        finally:
            session.close()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
