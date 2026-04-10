import { DEFAULT_POLLUTANT } from './pollutants'

/** Default map / single-location query center (Boulder, CO). */
export const DEFAULT_MAP_CENTER = { lat: 40.015, lon: -105.2705 }

function isoDaysAgoUTC(days) {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - days)
  return d.toISOString()
}

function isoNowUTC() {
  return new Date().toISOString()
}

/** Wide fallback when DB bounds are unknown (covers e.g. 2026 monthly CSVs queried later in 2026). */
const FALLBACK_RANGE_DAYS = 450

/**
 * Initial dashboard shape: no fabricated measurements.
 * Trace + single-location values come from the API after ingest (`data/ingest_monthly_csv_to_postgres.py`).
 */
export function createEmptyDashboardModel() {
  return {
    meta: {
      timezone: 'UTC',
      units: { pollution: 'µg/m³', distance: 'm' },
    },
    upload_trace_tab: {
      upload_response: {
        trace_id: null,
        job_id: null,
        pollutant: DEFAULT_POLLUTANT,
        message: null,
      },
      job_status_samples: [],
      exposure_summary: null,
      file_time_bounds: {
        start: isoDaysAgoUTC(1),
        end: isoNowUTC(),
      },
      time_filtered_points_response: { points: [] },
    },
    single_location_tab: {
      default_query: {
        lat: DEFAULT_MAP_CENTER.lat,
        lon: DEFAULT_MAP_CENTER.lon,
        // Synthetic Boulder disk uses up to ~8 km radius; stay above that.
        radius_m: 12000,
        start: isoDaysAgoUTC(FALLBACK_RANGE_DAYS),
        end: isoNowUTC(),
      },
      analytics_response: {
        status: 'empty',
        series: [],
        observation_count: 0,
        average: null,
        pollutant: DEFAULT_POLLUTANT,
        radius_m: 12000,
        unit: 'µg/m³',
        who_guideline: null,
        who_note: '',
      },
    },
  }
}
