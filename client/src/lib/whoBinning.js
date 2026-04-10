/**
 * WHO-oriented 3-bin time exposure (route segments), using guideline + interim tier.
 * PM2.5 / PM10 / NO2: WHO 2021 24-hour AQG + IT-2 (approximate bands for “moderate”).
 * O3: 8-hour AQG + common upper interim band.
 * SO2 / CO: AQG + practical upper interim for dashboard binning (µg/m³).
 */
export const WHO_BIN_CONFIG = {
  'PM2.5': {
    unit: 'µg/m³',
    guideline: 15,
    interimHigh: 35,
    labels: ['Within WHO 24h AQG', 'Between AQG and IT-2 (24h)', 'Above IT-2 (24h)'],
    shortLabel: ['AQG', 'Moderate', 'High'],
  },
  PM10: {
    unit: 'µg/m³',
    guideline: 45,
    interimHigh: 120,
    labels: ['Within WHO 24h AQG', 'Between AQG and IT-2 (24h)', 'Above IT-2 (24h)'],
    shortLabel: ['AQG', 'Moderate', 'High'],
  },
  SO2: {
    unit: 'µg/m³',
    guideline: 40,
    interimHigh: 114,
    labels: ['Within WHO 24h AQG', 'Between AQG and IT-1 (24h)', 'Above IT-1 (24h)'],
    shortLabel: ['AQG', 'Moderate', 'High'],
  },
  NO: {
    unit: 'ppb',
    guideline: 25,
    interimHigh: 60,
    labels: ['Low (approx.)', 'Moderate (approx.)', 'Elevated (approx.)'],
    shortLabel: ['Low', 'Moderate', 'High'],
  },
  NO2: {
    unit: 'µg/m³',
    guideline: 25,
    interimHigh: 120,
    labels: ['Within WHO 24h AQG', 'Between AQG and IT-2 (24h)', 'Above IT-2 (24h)'],
    shortLabel: ['AQG', 'Moderate', 'High'],
  },
  O3: {
    unit: 'µg/m³',
    guideline: 100,
    interimHigh: 160,
    labels: ['Within WHO 8h AQG', 'Between AQG and upper interim', 'Above upper interim'],
    shortLabel: ['AQG', 'Moderate', 'High'],
  },
  CO: {
    unit: 'µg/m³',
    guideline: 6000,
    interimHigh: 10000,
    labels: ['Within approx. WHO 8h level (µg/m³)', 'Elevated', 'High'],
    shortLabel: ['AQG*', 'Moderate', 'High'],
  },
}

export function classifyWHO(value, pollutantId) {
  if (value == null || Number.isNaN(value)) return 'unknown'
  const cfg = WHO_BIN_CONFIG[pollutantId] || WHO_BIN_CONFIG['PM2.5']
  if (value <= cfg.guideline) return 'good'
  if (value <= cfg.interimHigh) return 'moderate'
  return 'poor'
}

/**
 * Time-weighted minutes in each bin along ordered points (same logic as prior Dashboard).
 * @param {Array<{timestamp: string, matched_concentration: number|null}>} points
 * @param {string} boundsEndIso - end of trace window for last segment
 */
export function computeTimeBins(points, boundsEndIso, pollutantId) {
  const bins = { good: 0, moderate: 0, poor: 0 }
  if (!points?.length || !boundsEndIso) return bins

  const getMinutes = (a, b) => Math.max(0, (new Date(b) - new Date(a)) / 60000)

  points.forEach((point, index) => {
    const nextPoint = points[index + 1]
    const current = point.timestamp
    const next = nextPoint ? nextPoint.timestamp : boundsEndIso
    const span = getMinutes(current, next)
    const c = point.matched_concentration
    const tier = classifyWHO(c, pollutantId)
    if (tier === 'good') bins.good += span
    else if (tier === 'moderate') bins.moderate += span
    else bins.poor += span
  })

  return bins
}

/**
 * Same time-weighted bin logic for `/api/...` location analytics `series` items `{ t, value }`.
 */
export function computeTimeBinsFromAnalyticsSeries(series, boundsEndIso, pollutantId) {
  if (!series?.length || !boundsEndIso) {
    return { good: 0, moderate: 0, poor: 0 }
  }
  const points = series.map((item) => ({
    timestamp: item.t,
    matched_concentration: item.value,
  }))
  return computeTimeBins(points, boundsEndIso, pollutantId)
}

export function whoGuidelineFor(pollutantId) {
  return WHO_BIN_CONFIG[pollutantId]?.guideline ?? WHO_BIN_CONFIG['PM2.5'].guideline
}
