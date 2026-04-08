import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def parse_csv_trace(file_bytes):
    """
    Parses a CSV trace that should contain at minimum:
    timestamp, lat, lon
    """
    try:
        df = pd.read_csv(BytesIO(file_bytes))
        # Basic validation
        required_cols = {'timestamp', 'lat', 'lon'}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"CSV must contain columns: {required_cols}")
        
        # Parse timestamps and sort
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Noise removal: Drop NaNs and out of bounds coords
        df = df.dropna(subset=['lat', 'lon'])
        df = df[(df['lat'] >= -90) & (df['lat'] <= 90) & (df['lon'] >= -180) & (df['lon'] <= 180)]
        
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Failed to parse CSV: {e}")
        raise ValueError(f"Invalid CSV format: {e}")

def parse_gpx_trace(file_bytes):
    """
    Placeholder for GPX trace parsing using xml parsing.
    Returns list of dicts: [{'timestamp': dt, 'lat': float, 'lon': float}]
    """
    # In a full implementation, we'd use xml.etree.ElementTree or gpxpy
    raise NotImplementedError("GPX parsing is not fully implemented in V1 yet.")
