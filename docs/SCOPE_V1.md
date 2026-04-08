# AirTrail V1 Scope

This document defines the frozen scope for the initial version (V1) of the AirTrail platform.

| Decision | V1 Choice |
|----------|-----------|
| **GPS formats** | CSV + GPX only |
| **Pollutants** | PM2.5 and PM10 |
| **Matching rule** | Nearest monitoring station within 5 km + nearest hour |
| **CRS** | WGS84 (EPSG:4326) for traces and stations |
| **Exposure metrics** | Cumulative, mean, peak. Time windows defined by overall trace data |
| **Location query** | Point + radius; time range; one pollutant at a time |
