from celery import Celery
import os
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from packages.airtrail_core.models import GPSTrace, JobStatus

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://airtrail:password@localhost:5432/airtrail")
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

@celery_app.task(name="compute_exposure")
def compute_exposure(trace_id):
    session = Session()
    trace = session.query(GPSTrace).get(trace_id)
    if not trace:
        session.close()
        return {"status": "FAILURE", "error": "Trace not found"}

    try:
        trace.status = JobStatus.RUNNING
        session.commit()
        
        # Download from S3 (stub)
        print(f"Downloading {trace.storage_uri} from S3...")
        
        # Spatiotemporal processing logic here (stub)
        print(f"Processing trace {trace_id}... Done.")
        
        # Update status
        trace.status = JobStatus.SUCCESS
        session.commit()
        return {"status": "SUCCESS", "trace_id": trace_id}
    except Exception as e:
        trace.status = JobStatus.FAILURE
        session.commit()
        return {"status": "FAILURE", "error": str(e)}
    finally:
        session.close()

