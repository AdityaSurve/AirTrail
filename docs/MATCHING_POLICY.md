# Matching Policy

For V1, spatiotemporal matching operates as follows:
- **Spatial:** For a given GPS coordinate, the nearest monitoring station within a 5 km radius is selected. If multiple exist, the closest one is used.
- **Temporal:** We snap the GPS timestamp to the nearest hour and query the pollution measurement for that exact hour.
