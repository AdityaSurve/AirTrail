import { useEffect, useMemo, useRef, useState } from 'react'
import ArcGISMap from '@arcgis/core/Map'
import MapView from '@arcgis/core/views/MapView'
import Graphic from '@arcgis/core/Graphic'
import GraphicsLayer from '@arcgis/core/layers/GraphicsLayer'
import '@arcgis/core/assets/esri/themes/dark/main.css'
import { classifyWHO, WHO_BIN_CONFIG } from '../lib/whoBinning'

const formatTime = (isoString) =>
  isoString
    ? new Date(isoString).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
    : '—'

/** Marker + UI: matches WHO-style bins (good / moderate / poor). */
const TIER_STYLE = {
  good: {
    hex: '#34d399',
    outline: '#6ee7b7',
    dotClass: 'bg-emerald-400',
    glowClass: 'shadow-[0_0_22px_rgba(52,211,153,0.65)]',
    ringClass: 'ring-emerald-400/50',
    chipClass: 'border-emerald-400/40 bg-emerald-500/20 text-emerald-100',
  },
  moderate: {
    hex: '#fbbf24',
    outline: '#fde68a',
    dotClass: 'bg-amber-400',
    glowClass: 'shadow-[0_0_22px_rgba(251,191,36,0.55)]',
    ringClass: 'ring-amber-400/50',
    chipClass: 'border-amber-400/40 bg-amber-500/20 text-amber-100',
  },
  poor: {
    hex: '#f87171',
    outline: '#fecaca',
    dotClass: 'bg-rose-400',
    glowClass: 'shadow-[0_0_22px_rgba(248,113,113,0.55)]',
    ringClass: 'ring-rose-400/50',
    chipClass: 'border-rose-400/40 bg-rose-500/25 text-rose-100',
  },
  unknown: {
    hex: '#94a3b8',
    outline: '#cbd5e1',
    dotClass: 'bg-slate-400',
    glowClass: 'shadow-[0_0_14px_rgba(148,163,184,0.4)]',
    ringClass: 'ring-slate-400/40',
    chipClass: 'border-slate-500/40 bg-slate-600/30 text-slate-200',
  },
}

function tierShortLabel(tier, pollutantId) {
  if (tier === 'unknown') return 'No reading'
  const cfg = WHO_BIN_CONFIG[pollutantId] || WHO_BIN_CONFIG['PM2.5']
  const idx = tier === 'good' ? 0 : tier === 'moderate' ? 1 : 2
  return cfg.shortLabel?.[idx] ?? tier
}

function IconChevronLeft({ className = 'h-4 w-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M15 18l-6-6 6-6"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconChevronRight({ className = 'h-4 w-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const Map = ({
  mode,
  points,
  traceSites = [],
  singleQuery,
  unitLabel = 'µg/m³',
  activePollutant = 'PM2.5',
}) => {
  const mapRef = useRef(null)
  const viewRef = useRef(null)
  const layerRef = useRef(null)
  const [currentIdx, setCurrentIdx] = useState(0)

  const pointsSignature = points.map((p) => p.timestamp).join('\n')
  useEffect(() => {
    if (mode !== 'trace') return
    setCurrentIdx(0)
  }, [mode, pointsSignature])

  const n = points.length
  const safeIdx = n ? Math.min(Math.max(0, currentIdx), n - 1) : 0
  const currentPoint = n ? points[safeIdx] : null

  const concentrationTier = useMemo(() => {
    if (!currentPoint) return 'unknown'
    return classifyWHO(currentPoint.matched_concentration, activePollutant)
  }, [currentPoint, activePollutant])

  const tierUi = TIER_STYLE[concentrationTier] || TIER_STYLE.unknown
  const tierLabel = tierShortLabel(concentrationTier, activePollutant)

  // Create / destroy MapView when mode or single-location anchor changes
  useEffect(() => {
    if (!mapRef.current) return undefined

    const graphicsLayer = new GraphicsLayer()
    layerRef.current = graphicsLayer
    const map = new ArcGISMap({
      basemap: 'dark-gray-vector',
      layers: [graphicsLayer],
    })

    const centerLon =
      mode === 'single' ? singleQuery.lon : points[0]?.lon ?? singleQuery.lon
    const centerLat =
      mode === 'single' ? singleQuery.lat : points[0]?.lat ?? singleQuery.lat

    const view = new MapView({
      container: mapRef.current,
      map,
      center: [centerLon, centerLat],
      zoom: 13,
    })
    viewRef.current = view

    return () => {
      viewRef.current = null
      layerRef.current = null
      view.destroy()
    }
  }, [mode, singleQuery.lon, singleQuery.lat])

  // Redraw graphics (and step navigation center) without recreating the view
  useEffect(() => {
    const view = viewRef.current
    const layer = layerRef.current
    if (!view || !layer) return

    layer.removeAll()

    if (mode === 'single') {
      layer.add(
        new Graphic({
          geometry: {
            type: 'point',
            longitude: singleQuery.lon,
            latitude: singleQuery.lat,
          },
          symbol: {
            type: 'simple-marker',
            color: '#22d3ee',
            size: 10,
            outline: { color: '#67e8f9', width: 1 },
          },
        }),
      )
      return
    }

    if (mode === 'trace') {
      if (points.length > 1) {
        layer.add(
          new Graphic({
            geometry: {
              type: 'polyline',
              paths: [points.map((point) => [point.lon, point.lat])],
            },
            symbol: {
              type: 'simple-line',
              color: '#22d3ee',
              width: 3,
            },
          }),
        )
      }

      traceSites.forEach((location) => {
        const v = location.avgExposure
        const vLabel = v != null && Number.isFinite(v) ? v.toFixed(1) : '—'
        layer.add(
          new Graphic({
            geometry: {
              type: 'point',
              longitude: location.lon,
              latitude: location.lat,
            },
            symbol: {
              type: 'simple-marker',
              color: '#f97316',
              size: 8,
              outline: { color: '#fdba74', width: 1 },
            },
            attributes: { site: location.site, value: vLabel },
            popupTemplate: {
              title: '{site}',
              content: `Avg exposure (trace): {value} ${unitLabel}`,
            },
          }),
        )
      })

      if (currentPoint && currentPoint.lon != null && currentPoint.lat != null) {
        const c = currentPoint.matched_concentration
        const cLabel = c != null && Number.isFinite(c) ? c.toFixed(1) : '—'
        const tierKey = classifyWHO(c, activePollutant)
        const ts = TIER_STYLE[tierKey] || TIER_STYLE.unknown
        layer.add(
          new Graphic({
            geometry: {
              type: 'point',
              longitude: currentPoint.lon,
              latitude: currentPoint.lat,
            },
            symbol: {
              type: 'simple-marker',
              color: ts.hex,
              size: 14,
              outline: { color: ts.outline, width: 2 },
            },
            attributes: {
              t: formatTime(currentPoint.timestamp),
              site: currentPoint.site_name || '—',
              value: cLabel,
              pol: activePollutant,
            },
            popupTemplate: {
              title: 'Current trace point',
              content: `<div style="font-size:12px;line-height:1.5">
                <div><b>Time:</b> {t}</div>
                <div><b>Site:</b> {site}</div>
                <div><b>${activePollutant}:</b> {value} ${unitLabel}</div>
              </div>`,
            },
          }),
        )

        view
          .goTo({
            center: [currentPoint.lon, currentPoint.lat],
            zoom: Math.max(view.zoom, 14),
          })
          .catch(() => { })
      }
    }
  }, [
    mode,
    points,
    traceSites,
    safeIdx,
    currentPoint,
    unitLabel,
    singleQuery,
    activePollutant,
  ])

  const showStepper = mode === 'trace' && n > 0
  const conc =
    currentPoint?.matched_concentration != null && Number.isFinite(currentPoint.matched_concentration)
      ? currentPoint.matched_concentration.toFixed(1)
      : null

  return (
    <article className="glass w-full rounded-2xl p-4">
      <h3 className="mb-3 text-lg font-semibold text-slate-100">
        {mode === 'trace' ? 'Trace path, all sites & point navigator' : 'Single Location Map'}
      </h3>
      <div ref={mapRef} className="h-130 w-full rounded-xl border border-white/10" />
      {showStepper ? (
        <div className="mt-4 overflow-hidden rounded-2xl border border-white/[0.07] bg-slate-950/55 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05),0_12px_40px_-12px_rgba(0,0,0,0.65)] backdrop-blur-md">
          <div className="flex flex-col sm:flex-row sm:items-stretch">
            <div
              className="min-w-0 flex-1 bg-linear-to-br from-slate-900/40 via-slate-950/30 to-transparent p-4 sm:p-5"
              style={{
                borderLeftWidth: 4,
                borderLeftStyle: 'solid',
                borderLeftColor: tierUi.hex,
                boxShadow: `inset 0 0 48px -20px ${tierUi.hex}18`,
              }}
            >
              <p className="mb-3 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
                Along the trace
              </p>
              <div className="flex items-start gap-3.5">
                <div
                  className={`relative mt-0.5 h-5 w-5 shrink-0 rounded-full border-2 border-white/25 ring-2 ring-offset-2 ring-offset-slate-950 ${tierUi.dotClass} ${tierUi.ringClass} ${tierUi.glowClass}`}
                  title={`${activePollutant} — ${tierLabel}`}
                  aria-hidden
                />
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-semibold tracking-tight text-slate-50">
                      Point {safeIdx + 1}
                      <span className="ml-1.5 text-sm font-normal text-slate-500">/ {n}</span>
                    </span>
                    <span
                      className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide ${tierUi.chipClass}`}
                    >
                      {tierLabel}
                    </span>
                  </div>
                  {currentPoint ? (
                    <>
                      <p className="text-sm font-medium text-slate-200">{formatTime(currentPoint.timestamp)}</p>
                      <p className="truncate text-sm text-slate-400">
                        {currentPoint.site_name ? (
                          <span className="text-slate-300">{currentPoint.site_name}</span>
                        ) : (
                          <span className="italic text-slate-500">Unknown site</span>
                        )}
                      </p>
                      <p className="pt-0.5 text-lg font-semibold tabular-nums text-slate-100">
                        {conc != null ? (
                          <>
                            {conc}{' '}
                            <span className="text-sm font-medium text-slate-400">{unitLabel}</span>
                            <span className="ml-2 text-xs font-normal text-slate-500">({activePollutant})</span>
                          </>
                        ) : (
                          <span className="text-base font-normal text-slate-500">No concentration for this point</span>
                        )}
                      </p>
                    </>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="flex border-t border-white/6 bg-slate-950/40 p-3 sm:w-[min(100%,13rem)] sm:flex-col sm:justify-center sm:border-t-0 sm:border-l sm:border-white/6 sm:p-3">
              <div className="flex w-full gap-2 sm:flex-col sm:gap-2">
                <button
                  type="button"
                  aria-label="Go to previous point on trace"
                  disabled={safeIdx <= 0}
                  onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
                  className="group relative flex min-h-11.5 flex-1 items-center justify-center gap-2 overflow-hidden rounded-xl border border-white/8 bg-linear-to-b from-slate-800/95 to-slate-900 px-4 py-2.5 text-sm font-semibold text-slate-100 shadow-[0_2px_8px_rgba(0,0,0,0.35)] transition-all duration-200 hover:border-cyan-400/30 hover:from-slate-700/95 hover:text-white hover:shadow-[0_0_28px_rgba(34,211,238,0.14)] active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400/60 disabled:pointer-events-none disabled:border-white/4 disabled:from-slate-900/80 disabled:to-slate-950 disabled:text-slate-600 disabled:shadow-none sm:w-full"
                >
                  <span className="absolute inset-0 bg-linear-to-r from-cyan-500/0 via-cyan-400/0 to-cyan-500/0 opacity-0 transition-opacity duration-300 group-hover:from-cyan-500/10 group-hover:via-cyan-400/5 group-hover:to-cyan-500/10 group-hover:opacity-100" />
                  <IconChevronLeft className="relative h-4 w-4 shrink-0 text-cyan-400/85 transition-colors group-hover:text-cyan-300" />
                  <span className="relative">Previous</span>
                </button>
                <button
                  type="button"
                  aria-label="Go to next point on trace"
                  disabled={safeIdx >= n - 1}
                  onClick={() => setCurrentIdx((i) => Math.min(n - 1, i + 1))}
                  className="group relative flex min-h-11.5 flex-1 items-center justify-center gap-2 overflow-hidden rounded-xl border border-white/8 bg-linear-to-b from-slate-800/95 to-slate-900 px-4 py-2.5 text-sm font-semibold text-slate-100 shadow-[0_2px_8px_rgba(0,0,0,0.35)] transition-all duration-200 hover:border-teal-400/30 hover:from-slate-700/95 hover:text-white hover:shadow-[0_0_28px_rgba(45,212,191,0.14)] active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-400/60 disabled:pointer-events-none disabled:border-white/4 disabled:from-slate-900/80 disabled:to-slate-950 disabled:text-slate-600 disabled:shadow-none sm:w-full"
                >
                  <span className="absolute inset-0 bg-linear-to-r from-teal-500/0 via-teal-400/0 to-teal-500/0 opacity-0 transition-opacity duration-300 group-hover:from-teal-500/10 group-hover:via-teal-400/5 group-hover:to-teal-500/10 group-hover:opacity-100" />
                  <span className="relative">Next</span>
                  <IconChevronRight className="relative h-4 w-4 shrink-0 text-teal-400/85 transition-colors group-hover:text-teal-300" />
                </button>
              </div>
            </div>
          </div>

          <div className="border-t border-white/5 bg-slate-950/70 px-4 py-3">
            <div className="mb-1.5 flex items-center justify-between text-[0.65rem] font-medium uppercase tracking-wider text-slate-500">
              <span>Progress</span>
              <span className="tabular-nums text-slate-400">
                {safeIdx + 1} / {n}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800/90 ring-1 ring-white/6">
              <div
                className="h-full rounded-full bg-linear-to-r from-cyan-400 via-teal-400 to-emerald-400/90 shadow-[0_0_12px_rgba(34,211,238,0.35)] transition-[width] duration-300 ease-out"
                style={{ width: `${((safeIdx + 1) / n) * 100}%` }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </article>
  )
}

export default Map
