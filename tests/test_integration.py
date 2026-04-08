import requests
import pytest
import time

API_URL = "http://localhost:5000"

def test_full_pipeline_upload_to_results():
    """
    Integration test validating the full e2e pipeline:
    1. Upload CSV to `/api/v1/traces`
    2. Wait for Celery worker to finish
    3. Retrieve job status
    4. Retrieve exposure metrics
    """
    csv_content = "timestamp,lat,lon\n2023-10-01 10:00:00,37.7749,-122.4194\n2023-10-01 11:00:00,37.7849,-122.4194"
    files = {"file": ("test_trace.csv", csv_content, "text/csv")}
    
    upload_res = requests.post(f"{API_URL}/api/v1/traces", files=files)
    assert upload_res.status_code == 201
    
    data = upload_res.json()
    trace_id = data["trace_id"]
    job_id = data["job_id"]
    
    # Poll job status
    max_retries = 10
    for _ in range(max_retries):
        job_res = requests.get(f"{API_URL}/api/v1/jobs/{job_id}")
        assert job_res.status_code == 200
        status = job_res.json()["status"]
        if status in ["SUCCESS", "FAILURE"]:
            break
        time.sleep(1)
        
    assert status == "SUCCESS", f"Job failed with status: {status}"
    
    # Get exposure results
    exposure_res = requests.get(f"{API_URL}/api/v1/traces/{trace_id}/exposure")
    assert exposure_res.status_code == 200
    metrics = exposure_res.json()
    
    assert "cumulative" in metrics
    assert "mean" in metrics
    assert "peak" in metrics
