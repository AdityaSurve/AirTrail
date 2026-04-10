from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base
from geoalchemy2 import Geometry
import datetime
import enum

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

class GPSTrace(Base):
    __tablename__ = "gps_traces"
    id = Column(Integer, primary_key=True)
    storage_uri = Column(String, nullable=False)
    pollutant = Column(String(64), nullable=False, default="PM2.5")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(Integer, primary_key=True)
    trace_id = Column(Integer, ForeignKey("gps_traces.id"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    error_message = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MonitoringSite(Base):
    __tablename__ = "monitoring_sites"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    # AirNow / AQCSV "Station ID" / AQSID (string, zero-padded); NULL if unknown.
    external_station_id = Column(String(64), nullable=True, unique=True)
    location = Column(Geometry('POINT', srid=4326))

class PollutionObservation(Base):
    __tablename__ = "pollution_observations"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("monitoring_sites.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    pollutant = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, default="ug/m3")

class ExposureResult(Base):
    __tablename__ = "exposure_results"
    id = Column(Integer, primary_key=True)
    trace_id = Column(Integer, ForeignKey("gps_traces.id"), nullable=False)
    cumulative_exposure = Column(Float)
    mean_exposure = Column(Float)
    peak_exposure = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ExposurePoint(Base):
    __tablename__ = "exposure_points"
    id = Column(Integer, primary_key=True)
    trace_id = Column(Integer, ForeignKey("gps_traces.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    location = Column(Geometry('POINT', srid=4326))
    matched_site_id = Column(Integer, ForeignKey("monitoring_sites.id"), nullable=True)
    matched_concentration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
