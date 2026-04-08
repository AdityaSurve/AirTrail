def compute_metrics(matched_data):
    """
    Computes cumulative, mean, and peak exposure for a given trace's matched data.
    """
    if not matched_data:
        return {"cumulative": 0, "mean": 0, "peak": 0}
        
    concs = [x["concentration"] for x in matched_data]
    
    return {
        "cumulative": sum(concs),
        "mean": sum(concs) / len(concs),
        "peak": max(concs)
    }
