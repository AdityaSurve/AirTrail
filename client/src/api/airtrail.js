const join = (base, path) => {
  const p = path.startsWith('/') ? path : `/${path}`
  const b = String(base ?? '').replace(/\/$/, '')
  return b ? `${b}${p}` : p
}

async function parseJsonResponse(res) {
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    data = { raw: text }
  }
  if (!res.ok) {
    const msg = data.error || data.message || res.statusText || 'Request failed'
    throw new Error(msg)
  }
  return data
}

export async function fetchPollutantMeta(apiBase) {
  const res = await fetch(join(apiBase, '/api/v1/meta/pollutants'))
  return parseJsonResponse(res)
}

/** Min/max observation time in DB (for default single-location date range). */
export async function fetchObservationsBounds(apiBase) {
  const res = await fetch(join(apiBase, '/api/v1/meta/observations_bounds'))
  return parseJsonResponse(res)
}

export async function uploadTrace(apiBase, file, pollutant) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('pollutant', pollutant)
  const res = await fetch(join(apiBase, '/api/v1/traces'), {
    method: 'POST',
    body: fd,
  })
  return parseJsonResponse(res)
}

export async function fetchJob(apiBase, jobId) {
  const res = await fetch(join(apiBase, `/api/v1/jobs/${jobId}`))
  return parseJsonResponse(res)
}

export async function fetchTraceExposure(apiBase, traceId) {
  const res = await fetch(join(apiBase, `/api/v1/traces/${traceId}/exposure`))
  return parseJsonResponse(res)
}

export async function fetchExposurePoints(apiBase, traceId, { start, end } = {}) {
  const q = new URLSearchParams()
  if (start) q.set('start', start)
  if (end) q.set('end', end)
  const qs = q.toString()
  const path = `/api/v1/traces/${traceId}/exposure/points${qs ? `?${qs}` : ''}`
  const res = await fetch(join(apiBase, path))
  return parseJsonResponse(res)
}

export async function fetchLocationAnalytics(apiBase, body) {
  const res = await fetch(join(apiBase, '/api/v1/analytics/location'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonResponse(res)
}

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}
