const TopBoxes = ({ processed, mode, hasUploadedCsv = false }) => {
  const avgTrace = processed.summary?.mean
  const avgSingle = processed.locationAnalytics?.average
  const avg =
    mode === 'trace'
      ? avgTrace != null && Number.isFinite(avgTrace)
        ? avgTrace.toFixed(1)
        : '—'
      : avgSingle != null && Number.isFinite(avgSingle)
        ? avgSingle.toFixed(1)
        : '—'

  const showTraceExtras = hasUploadedCsv && mode === 'trace'
  const pathKm = processed.tracePathKm
  const pathLabel =
    pathKm != null && Number.isFinite(pathKm) ? pathKm.toFixed(2) : '—'
  const sitesCount = processed.traceDistinctSitesCount ?? 0

  return (
    <div
      className="grid gap-4 grid-cols-2"
    >
      <article className="glass rounded-2xl border border-amber-500/15 bg-amber-500/4 p-4 shadow-[inset_0_1px_0_0_rgba(251,191,36,0.1)]">
        <p className="text-xs uppercase tracking-wide text-amber-200/85">Total Time Monitored</p>
        <h3 className="mt-2 text-2xl font-semibold tabular-nums text-slate-100">
          {processed.durationMinutes} <span className="text-lg font-medium text-slate-400">min</span>
        </h3>
      </article>

      <article className="glass rounded-2xl border border-rose-500/15 bg-rose-500/4 p-4 shadow-[inset_0_1px_0_0_rgba(251,113,133,0.1)]">
        <p className="text-xs uppercase tracking-wide text-rose-200/85">Average Exposure</p>
        <h3 className="mt-2 text-2xl font-semibold tabular-nums text-slate-100">
          {avg}{' '}
          <span className="text-lg font-medium text-slate-400">
            {processed.unitLabel || processed.units.pollution}
          </span>
        </h3>
      </article>

      {showTraceExtras ? (
        <>
          <article className="glass rounded-2xl border border-cyan-500/15 bg-cyan-500/4 p-4 shadow-[inset_0_1px_0_0_rgba(34,211,238,0.1)]">
            <p className="text-xs uppercase tracking-wide text-cyan-200/85">Approx. path length</p>
            <h3 className="mt-2 text-2xl font-semibold tabular-nums text-slate-100">
              {pathLabel}
              {pathLabel !== '—' ? <span className="ml-1 text-lg font-medium text-slate-400">km</span> : null}
            </h3>
          </article>

          <article className="glass rounded-2xl border border-violet-500/15 bg-violet-500/4 p-4 shadow-[inset_0_1px_0_0_rgba(167,139,250,0.1)]">
            <p className="text-xs uppercase tracking-wide text-violet-200/85">Monitoring sites used</p>
            <h3 className="mt-2 text-2xl font-semibold tabular-nums text-slate-100">{sitesCount}</h3>
          </article>
        </>
      ) : null}
    </div>
  )
}

export default TopBoxes
