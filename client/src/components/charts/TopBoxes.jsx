const TopBoxes = ({ processed, mode }) => {
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

  return (
    <div className="grid grid-cols-2 gap-4">
      <article className="glass rounded-2xl p-4">
        <p className="text-xs uppercase tracking-wide text-slate-400">Total Time Monitored</p>
        <h3 className="mt-2 text-2xl font-semibold text-slate-100">{processed.durationMinutes} min</h3>
      </article>

      <article className="glass rounded-2xl p-4">
        <p className="text-xs uppercase tracking-wide text-slate-400">Average Exposure</p>
        <h3 className="mt-2 text-2xl font-semibold text-slate-100">
          {avg} {processed.unitLabel || processed.units.pollution}
        </h3>
      </article>
    </div>
  )
}

export default TopBoxes