from packages.airtrail_core.exposure import compute_metrics

def test_compute_metrics():
    matches = [{"concentration": 10}, {"concentration": 20}]
    results = compute_metrics(matches)
    assert results["cumulative"] == 30
    assert results["mean"] == 15
    assert results["peak"] == 20
