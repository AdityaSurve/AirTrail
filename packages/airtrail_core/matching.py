from sqlalchemy.sql import text
import logging
import pandas as pd

from packages.airtrail_core.constants import pollutant_sql_in_clause

logger = logging.getLogger(__name__)

def match_gps_to_pollution(gps_points, session, pollutant="PM2.5"):
    '''
    Matches GPS points to pollution observations using PostGIS.
    gps_points: list of dicts [{'timestamp': dt, 'lat': float, 'lon': float}]
    Returns list of dicts containing the original gps point + matched site/concentration.
    '''
    matched = []
    
    # In V1, we find the nearest monitoring site within 5 km.
    # And we find the pollution observation closest in time (usually snapped to hour).
    
    # We can use a raw SQL query or SQLAlchemy constructs. Standard raw query is often easiest for complex PostGIS bounding.
    poll_in, poll_bind = pollutant_sql_in_clause(pollutant)
    query = text(f"""
        SELECT s.id as site_id,
               ST_Distance(s.location::geography, ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography) as dist,
               o.value as concentration
        FROM monitoring_sites s
        LEFT JOIN pollution_observations o ON s.id = o.site_id AND o.pollutant IN ({poll_in})
        WHERE ST_DWithin(s.location::geography, ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography, 5000)
          AND o.timestamp >= :ts_start AND o.timestamp <= :ts_end
        ORDER BY dist ASC, abs(EXTRACT(EPOCH FROM o.timestamp) - EXTRACT(EPOCH FROM CAST(:ts AS timestamp))) ASC
        LIMIT 1
    """)
    
    for pt in gps_points:
        ts = pt['timestamp']
        # search within a generous 2 hour window to find nearest hourly observation
        ts_start = ts - pd.Timedelta(hours=2)
        ts_end = ts + pd.Timedelta(hours=2)
        
        try:
            result = session.execute(
                query,
                {
                    "lon": pt["lon"],
                    "lat": pt["lat"],
                    "ts": ts,
                    "ts_start": ts_start,
                    "ts_end": ts_end,
                    **poll_bind,
                },
            ).fetchone()
            
            if result:
                matched.append({
                    **pt,
                    "matched_site_id": result.site_id,
                    "matched_concentration": result.concentration,
                })
            else:
                matched.append({
                    **pt,
                    "matched_site_id": None,
                    "matched_concentration": None,
                })
        except Exception as e:
            logger.error(f"Error matching point {pt}: {e}")
            matched.append({**pt, "matched_site_id": None, "matched_concentration": None})
            
    return matched

