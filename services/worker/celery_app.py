from celery import Celery
import os
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from packages.airtrail_core.models import GPSTrace, JobStatus, ProcessingJob

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://airtrail:password@localhost:5433/airtrail")
S3_BUCKET = os.getenv("S3_BUCKET", "airtrail-traces")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

celery_app = Celery(
    "airtrail_worker",
    broker=CELERY_BROKER_URL,
    backend=REDIS_URL,
)

from packages.airtrail_core.ingestion import parse_csv_trace
from packages.airtrail_core.matching import match_gps_to_pollution
from packages.airtrail_core.exposure import compute_metrics
from packages.airtrail_core.models import ExposureResult, ExposurePoint

@celery_app.task(name="compute_exposure")
def compute_exposure(job_id):
    session = Session()
    job = session.query(ProcessingJob).get(job_id)
    if not job:
        session.close()
        return {"status": "FAILURE", "error": "Job not found"}

    try:
        job.status = JobStatus.RUNNING
        session.commit()
        
        trace = session.query(GPSTrace).get(job.trace_id)
        
        # Download from S3
        import io
        obj_key = trace.storage_uri.split('s3://' + S3_BUCKET + '/')[-1]
        response = s3.get_object(Bucket=S3_BUCKET, Key=obj_key)
        file_bytes = response['Body'].read()
        
        gps_points = parse_csv_trace(file_bytes)
        poll = (trace.pollutant or "PM2.5").strip()
        matched_data = match_gps_to_pollution(gps_points, session, pollutant=poll)
        
        for pt in matched_data:
            ep = ExposurePoint(
                trace_id=trace.id,
                timestamp=pt['timestamp'],
                location=f"SRID=4326;POINT({pt['lon']} {pt['lat']})",
                matched_site_id=pt.get('matched_site_id'),
                matched_concentration=pt.get('matched_concentration')
            )
            session.add(ep)
            
        metrics = compute_metrics(matched_data)
        res = ExposureResult(
            trace_id=trace.id,
            cumulative_exposure=metrics['cumulative'],
            mean_exposure=metrics['mean'],
            peak_exposure=metrics['peak']
        )
        session.add(res)
        
        job.status = JobStatus.SUCCESS
        session.commit()
        return {"status": "SUCCESS", "job_id": job_id}
    except Exception as e:
        job.status = JobStatus.FAILURE
        job.error_message = str(e)
        session.commit()
        return {"status": "FAILURE", "error": str(e)}
    finally:
        session.close()

