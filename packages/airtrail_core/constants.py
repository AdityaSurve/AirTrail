"""Shared pollutant definitions (must match `pollution_observations.pollutant` values where possible)."""

MONITORED_POLLUTANTS = ("PM2.5", "PM10", "SO2", "NO", "NO2", "O3", "CO")

DEFAULT_POLLUTANT = "PM2.5"

# WHO guideline concentrations for short-term context (used for API metadata / UI reference lines).
# Values align with WHO global air quality guidelines (2021) where a 24-hour AQG exists; O3 uses 8-hour AQG.
POLLUTANT_META = {
    "PM2.5": {"unit": "µg/m³", "who_guideline": 15.0, "who_note": "WHO 24-hour AQG"},
    "PM10": {"unit": "µg/m³", "who_guideline": 45.0, "who_note": "WHO 24-hour AQG"},
    "SO2": {"unit": "µg/m³", "who_guideline": 40.0, "who_note": "WHO 24-hour AQG"},
    "NO": {"unit": "ppb", "who_guideline": None, "who_note": "No WHO AQG; tiers are approximate (ppb)"},
    "NO2": {"unit": "µg/m³", "who_guideline": 25.0, "who_note": "WHO 24-hour AQG"},
    "O3": {"unit": "µg/m³", "who_guideline": 100.0, "who_note": "WHO 8-hour AQG"},
    "CO": {"unit": "µg/m³", "who_guideline": 6000.0, "who_note": "Approx. 6 ppm (8-hour) expressed as µg/m³ for display"},
}


def pollutant_db_variants(canonical: str) -> tuple[str, ...]:
    """
    Spellings that may appear in `pollution_observations.pollutant`.
    AirNow hourly .dat / monthly CSV use OZONE; the public API uses O3.
    """
    aliases: dict[str, tuple[str, ...]] = {
        "O3": ("OZONE",),
    }
    out: list[str] = [canonical]
    out.extend(aliases.get(canonical, ()))
    seen: set[str] = set()
    unique: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return tuple(unique)


def pollutant_sql_in_clause(canonical: str) -> tuple[str, dict[str, str]]:
    """SQL `IN (...)` fragment and bind params for pollutant matching."""
    variants = pollutant_db_variants(canonical)
    keys = [f"poll_{i}" for i in range(len(variants))]
    clause = ", ".join(f":{k}" for k in keys)
    return clause, dict(zip(keys, variants))


def parse_pollutant_param(raw: str | None) -> tuple[str | None, str | None]:
    """
    Returns (pollutant, error_message). If raw is empty, defaults to PM2.5.
    If raw is non-empty and unknown, returns (None, error).
    """
    if raw is None:
        return DEFAULT_POLLUTANT, None
    if isinstance(raw, str) and raw.strip() == "":
        return DEFAULT_POLLUTANT, None
    n = str(raw).strip()
    if n not in MONITORED_POLLUTANTS:
        return None, f"Invalid pollutant. Use one of: {list(MONITORED_POLLUTANTS)}"
    return n, None
