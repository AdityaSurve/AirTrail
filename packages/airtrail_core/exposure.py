import pandas as pd

def compute_metrics(matched_data):
    """
    Computes cumulative, mean, and peak exposure with time-weighting.
    matched_data is a list of dicts: [{'timestamp': dt, 'matched_concentration': float, ...}]
    """
    valid_data = [d for d in matched_data if d.get('matched_concentration') is not None]
    
    if len(valid_data) < 2:
        val = valid_data[0]['matched_concentration'] if valid_data else 0
        return {"cumulative": val, "mean": val, "peak": val}
        
    df = pd.DataFrame(valid_data)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Calculate time differences between consecutive points (in hours for typical exposure metrics)
    df['time_diff_hours'] = df['timestamp'].diff().dt.total_seconds() / 3600.0
    df['time_diff_hours'] = df['time_diff_hours'].fillna(0)
    
    # Mean of adjacent concentrations multiplied by the time duration
    # integrating area under the curve
    exposure_segments = []
    for i in range(1, len(df)):
        c1 = df.loc[i-1, 'matched_concentration']
        c2 = df.loc[i, 'matched_concentration']
        dt = df.loc[i, 'time_diff_hours']
        
        segment_exposure = ((c1 + c2) / 2.0) * dt
        exposure_segments.append(segment_exposure)
        
    cumulative_exposure = sum(exposure_segments)
    
    # Total duration
    total_hours = df['time_diff_hours'].sum()
    mean_exposure = cumulative_exposure / total_hours if total_hours > 0 else df['matched_concentration'].mean()
    
    # Peak exposure
    peak_exposure = df['matched_concentration'].max()
    
    return {
        "cumulative": float(cumulative_exposure),
        "mean": float(mean_exposure),
        "peak": float(peak_exposure)
    }

