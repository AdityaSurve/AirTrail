const Navbar = ({
  traceId,
  status,
  currentMode,
  hasUploadedCsv,
  pollutants,
  selectedPollutant,
  onPollutantChange,
  tracePollutant,
  pollutantLocked,
  onUploadClick,
}) => {
  return (
    <header className="glass mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4">
      <div>
        <p className="eyebrow">AirTrail Dashboard</p>
        <h2 className="text-lg font-semibold text-slate-100">
          {currentMode === 'trace' ? 'Trace Exposure Analysis' : 'Single Location Analysis'}
        </h2>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2 text-slate-300">
          <span className="text-xs uppercase tracking-wide text-slate-400">Pollutant</span>
          <select
            className="rounded-lg border border-white/20 bg-slate-900/70 px-3 py-1.5 text-slate-100 disabled:opacity-60"
            value={pollutantLocked ? tracePollutant : selectedPollutant}
            onChange={(e) => onPollutantChange(e.target.value)}
            disabled={pollutantLocked}
            title={
              pollutantLocked
                ? 'Pollutant is fixed for this upload. Re-upload to change.'
                : 'WHO-based binning updates when you change pollutant'
            }
          >
            {(pollutants || []).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>

        <button type="button" className="btn btn-primary text-sm" onClick={onUploadClick}>
          Upload CSV
        </button>

        <span className="rounded-full border border-white/20 bg-slate-900/60 px-3 py-1 text-slate-300">
          {hasUploadedCsv
            ? traceId != null
              ? `Trace #${traceId}`
              : 'Trace (pending id)'
            : 'No CSV uploaded'}
        </span>
        <span className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">
          {status}
        </span>
      </div>
    </header>
  )
}

export default Navbar
