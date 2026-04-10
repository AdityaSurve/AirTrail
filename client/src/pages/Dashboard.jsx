import { useMemo, useState, useEffect, useRef } from 'react'
import Sidebar from '../components/Sidebar'
import Navbar from '../components/Navbar'
import FileUploadModal from '../components/FileUploadModal'
import ChartsSection from '../components/ChartsSection'
import { DEFAULT_POLLUTANT, POLLUTANT_IDS } from '../constants/pollutants'
import { createEmptyDashboardModel } from '../constants/dashboardDefaults'
import {
  computeTimeBins,
  computeTimeBinsFromAnalyticsSeries,
  WHO_BIN_CONFIG,
  whoGuidelineFor,
} from '../lib/whoBinning'
import * as api from '../api/airtrail'

const formatTime = (isoString) =>
  new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const deepClone = (x) => JSON.parse(JSON.stringify(x))

const toLocalInput = (iso) => {
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Great-circle distance between two WGS84 points (km). */
function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

function tracePathLengthKm(points) {
  if (!points?.length || points.length < 2) return null
  let km = 0
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1]
    const b = points[i]
    if (
      a?.lat == null ||
      a?.lon == null ||
      b?.lat == null ||
      b?.lon == null ||
      Number.isNaN(a.lat) ||
      Number.isNaN(b.lat)
    ) {
      continue
    }
    km += haversineKm(a.lat, a.lon, b.lat, b.lon)
  }
  return km > 0 ? km : null
}

const Dashboard = ({ apiBase, hasApi, onBackHome }) => {
  const [emptyBase] = useState(() => createEmptyDashboardModel())
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [hasUploadedCsv, setHasUploadedCsv] = useState(false)
  const [activeMode, setActiveMode] = useState('single')
  const [selectedPollutant, setSelectedPollutant] = useState(DEFAULT_POLLUTANT)
  const [liveTrace, setLiveTrace] = useState(null)
  const [singleLive, setSingleLive] = useState(null)
  const [jobStatus, setJobStatus] = useState('UNKNOWN')
  const [uploadBusy, setUploadBusy] = useState(false)
  const [uploadError, setUploadError] = useState(null)

  const b0 = emptyBase.upload_trace_tab.file_time_bounds
  const [traceTimeRange, setTraceTimeRange] = useState(() => [
    new Date(b0.start),
    new Date(b0.end),
  ])

  const dq = emptyBase.single_location_tab.default_query
  const [singleLat, setSingleLat] = useState(dq.lat)
  const [singleLon, setSingleLon] = useState(dq.lon)
  const [singleRadius, setSingleRadius] = useState(dq.radius_m)
  const [singleStart, setSingleStart] = useState(toLocalInput(dq.start))
  const [singleEnd, setSingleEnd] = useState(toLocalInput(dq.end))

  const didSyncRangeFromDb = useRef(false)
  const traceJustUploadedRef = useRef(false)
  const [ingestedTimeBounds, setIngestedTimeBounds] = useState(null)

  useEffect(() => {
    if (!hasApi) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const ob = await api.fetchObservationsBounds(apiBase)
        if (cancelled) return
        if (ob?.start && ob?.end) {
          setIngestedTimeBounds({ start: ob.start, end: ob.end })
          if (!didSyncRangeFromDb.current) {
            didSyncRangeFromDb.current = true
            setSingleStart(toLocalInput(ob.start))
            setSingleEnd(toLocalInput(ob.end))
          }
        } else {
          setIngestedTimeBounds(null)
        }
      } catch {
        if (!cancelled) setIngestedTimeBounds(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [hasApi, apiBase])

  const applyIngestedTimeRange = () => {
    if (!ingestedTimeBounds?.start || !ingestedTimeBounds?.end) return
    setSingleStart(toLocalInput(ingestedTimeBounds.start))
    setSingleEnd(toLocalInput(ingestedTimeBounds.end))
  }

  const dataModel = useMemo(() => {
    const m = deepClone(emptyBase)
    if (liveTrace) {
      const { exposure, pointsPayload, jobId, traceId } = liveTrace
      m.upload_trace_tab.upload_response = {
        trace_id: traceId,
        job_id: jobId,
        message: 'uploaded and queued',
        pollutant: liveTrace.uploadedPollutant ?? exposure.pollutant ?? liveTrace.pollutant,
      }
      m.upload_trace_tab.job_status_samples = [{ job_id: jobId, status: jobStatus, error: null }]
      m.upload_trace_tab.exposure_summary = {
        cumulative: exposure.cumulative,
        mean: exposure.mean,
        peak: exposure.peak,
        pollutant: exposure.pollutant,
        unit: exposure.unit,
        who_guideline: exposure.who_guideline,
      }
      const tb = pointsPayload.time_bounds
      if (tb?.start && tb?.end) {
        m.upload_trace_tab.file_time_bounds = { start: tb.start, end: tb.end }
      }
      m.upload_trace_tab.time_filtered_points_response = { points: pointsPayload.points || [] }
      if (pointsPayload.unit) {
        m.meta.units.pollution = pointsPayload.unit
      }
    }
    if (singleLive) {
      m.single_location_tab.default_query = singleLive.query
      m.single_location_tab.analytics_response = singleLive.analytics
    }
    return m
  }, [emptyBase, liveTrace, singleLive, jobStatus])

  const activePollutant = selectedPollutant

  const pointsFull = dataModel.upload_trace_tab.time_filtered_points_response.points || []
  const bounds = dataModel.upload_trace_tab.file_time_bounds

  const filteredPoints = useMemo(() => {
    if (!traceTimeRange?.[0] || !traceTimeRange?.[1] || !pointsFull.length) return pointsFull
    const [t0, t1] = traceTimeRange
    const a = t0.getTime()
    const b = t1.getTime()
    return pointsFull.filter((p) => {
      const t = new Date(p.timestamp).getTime()
      return t >= a && t <= b
    })
  }, [pointsFull, traceTimeRange])

  const processed = useMemo(() => {
    const uploadData = dataModel.upload_trace_tab
    const points = filteredPoints
    const b = uploadData.file_time_bounds
    const durationMinutes = Math.max(0, (new Date(b.end) - new Date(b.start)) / 60000)

    const singleA = dataModel.single_location_tab.analytics_response
    const singleQ = dataModel.single_location_tab.default_query
    const bins =
      activeMode === 'single'
        ? computeTimeBinsFromAnalyticsSeries(
            singleA?.series,
            singleQ?.end || b.end,
            selectedPollutant,
          )
        : computeTimeBins(points, b.end, activePollutant)

    const locationStats = {}
    points.forEach((point) => {
      const key = point.site_name || 'Unknown'
      if (!locationStats[key]) {
        locationStats[key] = { site: key, exposure: 0, count: 0, lat: point.lat, lon: point.lon }
      }
      if (point.matched_concentration != null) {
        locationStats[key].exposure += point.matched_concentration
        locationStats[key].count += 1
      }
    })

    const traceSites = Object.values(locationStats)
      .filter((e) => e.count > 0)
      .map((entry) => ({
        site: entry.site,
        lat: entry.lat,
        lon: entry.lon,
        avgExposure: entry.exposure / entry.count,
      }))
      .sort((a, b) => a.site.localeCompare(b.site))

    const tracePathKm = tracePathLengthKm(points)
    const traceDistinctSitesCount = traceSites.length

    const timeline = points.map((point) => ({
      label: formatTime(point.timestamp),
      ts: point.timestamp,
      value: point.matched_concentration,
    }))

    const singleLocationSeries = (singleA?.series || []).map((item) => ({
      label: formatTime(item.t),
      ts: item.t,
      value: item.value,
    }))

    const singleQuery = dataModel.single_location_tab.default_query
    const summary = uploadData.exposure_summary
    const whoG =
      activeMode === 'trace'
        ? (summary?.who_guideline ?? whoGuidelineFor(activePollutant))
        : (singleA?.who_guideline ?? whoGuidelineFor(selectedPollutant))

    const unit =
      activeMode === 'trace'
        ? (summary?.unit || dataModel.meta.units.pollution)
        : (singleA?.unit || dataModel.meta.units.pollution)

    return {
      points,
      pointsFull,
      bounds: b,
      durationMinutes,
      bins,
      binLabels: WHO_BIN_CONFIG[activePollutant] || WHO_BIN_CONFIG['PM2.5'],
      timeline,
      traceSites,
      tracePathKm,
      traceDistinctSitesCount,
      singleLocationSeries,
      summary,
      singleQuery,
      job: uploadData.upload_response,
      statusFlow: uploadData.job_status_samples,
      units: dataModel.meta.units,
      unitLabel: unit,
      locationAnalytics: singleA,
      whoGuideline: whoG,
      activePollutant,
    }
  }, [dataModel, filteredPoints, activePollutant, activeMode, selectedPollutant])

  useEffect(() => {
    if (liveTrace?.pointsPayload?.time_bounds?.start && liveTrace?.pointsPayload?.time_bounds?.end) {
      const { start, end } = liveTrace.pointsPayload.time_bounds
      setTraceTimeRange([new Date(start), new Date(end)])
    }
  }, [liveTrace])

  useEffect(() => {
    if (!hasApi || activeMode !== 'trace' || !liveTrace?.traceId) return undefined
    if (traceJustUploadedRef.current) {
      traceJustUploadedRef.current = false
      return undefined
    }
    const tid = liveTrace.traceId
    let cancelled = false
    ;(async () => {
      try {
        const [exposure, pointsPayload] = await Promise.all([
          api.fetchTraceExposure(apiBase, tid, { pollutant: selectedPollutant }),
          api.fetchExposurePoints(apiBase, tid, { pollutant: selectedPollutant }),
        ])
        if (!cancelled) {
          setLiveTrace((prev) =>
            prev && prev.traceId === tid ? { ...prev, exposure, pointsPayload } : prev,
          )
        }
      } catch (e) {
        if (!cancelled) setUploadError(e?.message || String(e))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [hasApi, activeMode, apiBase, liveTrace?.traceId, selectedPollutant])

  useEffect(() => {
    if (!hasApi || activeMode !== 'single') {
      setSingleLive(null)
      return undefined
    }
    let cancelled = false
    ;(async () => {
      try {
        const analytics = await api.fetchLocationAnalytics(apiBase, {
          lat: Number(singleLat),
          lon: Number(singleLon),
          start: new Date(singleStart).toISOString(),
          end: new Date(singleEnd).toISOString(),
          radius_m: Number(singleRadius),
          pollutant: selectedPollutant,
        })
        if (!cancelled) {
          setSingleLive({
            query: {
              lat: Number(singleLat),
              lon: Number(singleLon),
              radius_m: Number(singleRadius),
              start: new Date(singleStart).toISOString(),
              end: new Date(singleEnd).toISOString(),
            },
            analytics,
          })
        }
      } catch {
        if (!cancelled) setSingleLive(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [hasApi, activeMode, apiBase, singleLat, singleLon, singleStart, singleEnd, singleRadius, selectedPollutant])

  const handleLiveUpload = async (file) => {
    if (!hasApi) return
    setUploadError(null)
    setUploadBusy(true)
    setJobStatus('PENDING')
    try {
      const up = await api.uploadTrace(apiBase, file, selectedPollutant)
      const { trace_id, job_id } = up
      let terminal = false
      for (let i = 0; i < 90; i++) {
        const j = await api.fetchJob(apiBase, job_id)
        setJobStatus(j.status)
        if (j.status === 'SUCCESS') {
          terminal = true
          break
        }
        if (j.status === 'FAILURE') {
          throw new Error(j.error || 'Worker failed')
        }
        await api.sleep(2000)
      }
      if (!terminal) throw new Error('Processing timed out — try again or check worker logs')

      traceJustUploadedRef.current = true
      const exposure = await api.fetchTraceExposure(apiBase, trace_id)
      const pointsPayload = await api.fetchExposurePoints(apiBase, trace_id)
      setLiveTrace({
        traceId: trace_id,
        jobId: job_id,
        uploadedPollutant: up.pollutant,
        pollutant: exposure.pollutant || selectedPollutant,
        exposure,
        pointsPayload,
      })
      setHasUploadedCsv(true)
      setActiveMode('trace')
      setJobStatus('SUCCESS')
    } catch (e) {
      const msg = e?.message || String(e)
      setUploadError(msg)
      setJobStatus('FAILURE')
      throw e
    } finally {
      setUploadBusy(false)
    }
  }

  const currentMode = hasUploadedCsv ? activeMode : 'single'

  const downloadCsv = async () => {
    const esc = (item) => `"${String(item).replaceAll('"', '""')}"`

    if (hasApi && hasUploadedCsv && liveTrace?.traceId) {
      try {
        const start = traceTimeRange?.[0]?.toISOString()
        const end = traceTimeRange?.[1]?.toISOString()
        const payload = await api.fetchExposurePoints(apiBase, liveTrace.traceId, {
          allPollutants: true,
          start,
          end,
        })
        const pols = payload.pollutants || POLLUTANT_IDS
        const headers = ['timestamp', 'lat', 'lon', 'site_name', ...pols.map((p) => `conc_${p}`)]
        const rows = (payload.points || []).map((point) => {
          const conc = point.concentrations || {}
          return [point.timestamp, point.lat, point.lon, point.site_name, ...pols.map((p) => conc[p])]
        })
        const csv = [headers, ...rows].map((row) => row.map(esc).join(',')).join('\n')
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = 'airtrail_results.csv'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      } catch (e) {
        setUploadError(e?.message || String(e))
      }
      return
    }

    const headers = ['timestamp', 'lat', 'lon', 'site_name', 'pollutant', 'concentration']
    const rows = processed.points.map((point) => [
      point.timestamp,
      point.lat,
      point.lon,
      point.site_name,
      processed.activePollutant,
      point.matched_concentration,
    ])
    const csv = [headers, ...rows].map((row) => row.map(esc).join(',')).join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'airtrail_results.csv'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const navStatus = liveTrace || hasApi ? jobStatus : 'UNKNOWN'

  return (
    <div className="app-shell min-h-screen">
      <div className="glow glow-a" />
      <div className="glow glow-b" />
      <div className="glow glow-c" />

      <Sidebar
        hasUploadedCsv={hasUploadedCsv}
        activeMode={currentMode}
        onUploadClick={() => setIsUploadOpen(true)}
        onDownloadClick={downloadCsv}
        onSingleLocationClick={() => setActiveMode('single')}
        onTraceModeClick={() => setActiveMode('trace')}
        onBackHome={onBackHome}
        singleLocationOpen={currentMode === 'single'}
        singleLat={singleLat}
        singleLon={singleLon}
        singleRadius={singleRadius}
        singleStart={singleStart}
        singleEnd={singleEnd}
        onSingleLat={setSingleLat}
        onSingleLon={setSingleLon}
        onSingleRadius={setSingleRadius}
        onSingleStart={setSingleStart}
        onSingleEnd={setSingleEnd}
        hasApi={hasApi}
        ingestedTimeBounds={ingestedTimeBounds}
        onApplyIngestedTimeRange={applyIngestedTimeRange}
        apiHint={
          hasApi
            ? apiBase
              ? `API: ${apiBase}`
              : 'API: Vite proxy → /api (Flask on :5000)'
            : 'API off (VITE_USE_SAMPLE_ONLY=true) — enable false and run Flask + ingest CSVs'
        }
      />

      <main className="content-shell">
        <Navbar
          onUploadClick={() => setIsUploadOpen(true)}
          traceId={processed.job.trace_id}
          status={navStatus}
          currentMode={currentMode}
          hasUploadedCsv={hasUploadedCsv}
          pollutants={POLLUTANT_IDS}
          selectedPollutant={selectedPollutant}
          onPollutantChange={setSelectedPollutant}
        />

        {uploadError ? (
          <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-950/40 px-4 py-2 text-sm text-rose-200">
            {uploadError}
          </div>
        ) : null}

        {currentMode === 'single' &&
        hasApi &&
        ingestedTimeBounds &&
        (processed.locationAnalytics?.observation_count ?? 0) === 0 ? (
          <div className="mb-4 rounded-xl border border-amber-500/35 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
            No observations in the selected <strong>Start</strong>–<strong>End</strong> window. Ingested rows in
            Postgres span roughly{' '}
            <strong>{new Date(ingestedTimeBounds.start).toLocaleString()}</strong> –{' '}
            <strong>{new Date(ingestedTimeBounds.end).toLocaleString()}</strong> (your local time). Narrow files
            (e.g. one hourly file) often cover only a single day or hour — align the filter or use &quot;Use DB
            time range&quot; in the sidebar.
          </div>
        ) : null}

        <section>
          <ChartsSection
            processed={processed}
            mode={currentMode}
            hasUploadedCsv={hasUploadedCsv}
            traceTimeRange={traceTimeRange}
            traceBoundsMin={new Date(bounds.start)}
            traceBoundsMax={new Date(bounds.end)}
            onTraceTimeRangeChange={setTraceTimeRange}
          />
        </section>
      </main>

      <FileUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        message={processed.job.message}
        jobId={processed.job.job_id}
        hasApi={hasApi}
        uploadBusy={uploadBusy}
        onLiveUpload={handleLiveUpload}
      />
    </div>
  )
}

export default Dashboard
