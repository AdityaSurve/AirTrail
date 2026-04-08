from flask import Flask, jsonify, request
import os
import boto3
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from packages.airtrail_core.models import Base, GPSTrace, JobStatus
from werkzeug.utils import secure_filename

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://airtrail:password@localhost:5432/airtrail")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_BUCKET = os.getenv("S3_BUCKET", "airtrail-traces")
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

def create_app():
    app = Flask(__name__)

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
        
        try:
            # Create bucket if not exists
            try:
                s3.head_bucket(Bucket=S3_BUCKET)
            except Exception:
                s3.create_bucket(Bucket=S3_BUCKET)
                
            s3.upload_fileobj(file, S3_BUCKET, object_name)
            storage_uri = f"s3://{S3_BUCKET}/{object_name}"
            
            # Save to DB
            session = Session()
            trace = GPSTrace(storage_uri=storage_uri, status=JobStatus.PENDING)
            session.add(trace)
            session.commit()
            trace_id = trace.id
            session.close()
            
            return jsonify({"trace_id": trace_id, "message": "uploaded", "storage_uri": storage_uri}), 201
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000, host="0.0.0.0")
