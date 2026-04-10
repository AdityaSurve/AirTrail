const Sidebar = ({
  hasUploadedCsv,
  activeMode,
  onUploadClick,
  onDownloadClick,
  onSingleLocationClick,
  onTraceModeClick,
  onBackHome,
  singleLocationOpen,
  singleLat,
  singleLon,
  singleRadius,
  singleStart,
  singleEnd,
  onSingleLat,
  onSingleLon,
  onSingleRadius,
  onSingleStart,
  onSingleEnd,
  hasApi = false,
  ingestedTimeBounds = null,
  onApplyIngestedTimeRange,
  apiHint,
}) => {
  const traceDisabled = !hasUploadedCsv

  return (
    <aside className="sidebar-panel glass sticky top-6 z-20 h-[calc(100vh-3rem)] w-72 shrink-0 overflow-y-auto rounded-2xl p-5">
      <div>
        <p className="eyebrow">Workspace</p>
        <h3 className="text-xl font-semibold text-slate-100">AirTrail</h3>
      </div>

      <div className="mt-6 space-y-3">
        <button type="button" className="btn btn-primary w-full" onClick={onUploadClick}>
          Upload CSV File
        </button>

        <button
          type="button"
          className="btn w-full border border-white/20 bg-white/5 text-slate-200 hover:bg-white/10"
          onClick={onDownloadClick}
        >
          Download Result CSV
        </button>

        <button
          type="button"
          className={`btn w-full border ${
            activeMode === 'single' ? 'border-cyan-300/40 bg-cyan-500/20' : 'border-white/20 bg-white/5'
          } text-slate-100 hover:bg-cyan-500/20`}
          onClick={onSingleLocationClick}
        >
          Analyze Single Location
        </button>

        <button
          type="button"
          className={`btn w-full border ${
            activeMode === 'trace' ? 'border-cyan-300/40 bg-cyan-500/20' : 'border-white/20 bg-white/5'
          } text-slate-100 hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50`}
          onClick={onTraceModeClick}
          disabled={traceDisabled}
        >
          Uploaded Trace Mode
        </button>
      </div>

      {singleLocationOpen ? (
        <div className="mt-6 space-y-3 rounded-xl border border-white/10 bg-slate-900/40 p-3 text-xs text-slate-200">
          <p className="font-semibold text-slate-100">Single location query</p>
          <label className="block">
            Latitude
            <input
              type="number"
              step="any"
              className="mt-1 w-full rounded border border-white/15 bg-slate-950/60 px-2 py-1"
              value={singleLat}
              onChange={(e) => onSingleLat(Number(e.target.value))}
            />
          </label>
          <label className="block">
            Longitude
            <input
              type="number"
              step="any"
              className="mt-1 w-full rounded border border-white/15 bg-slate-950/60 px-2 py-1"
              value={singleLon}
              onChange={(e) => onSingleLon(Number(e.target.value))}
            />
          </label>
          <label className="block">
            Radius (m)
            <input
              type="number"
              min={100}
              className="mt-1 w-full rounded border border-white/15 bg-slate-950/60 px-2 py-1"
              value={singleRadius}
              onChange={(e) => onSingleRadius(Number(e.target.value))}
            />
          </label>
          <label className="block">
            Start
            <input
              type="datetime-local"
              className="mt-1 w-full rounded border border-white/15 bg-slate-950/60 px-2 py-1"
              value={singleStart}
              onChange={(e) => onSingleStart(e.target.value)}
              title="Interpreted in your browser local timezone; API compares to stored UTC timestamps."
            />
          </label>
          <label className="block">
            End
            <input
              type="datetime-local"
              className="mt-1 w-full rounded border border-white/15 bg-slate-950/60 px-2 py-1"
              value={singleEnd}
              onChange={(e) => onSingleEnd(e.target.value)}
              title="Interpreted in your browser local timezone; API compares to stored UTC timestamps."
            />
          </label>
          
        </div>
      ) : null}

      <div className="mt-6 rounded-xl border border-white/10 bg-slate-900/50 p-3 text-xs text-slate-300">
        {hasUploadedCsv
          ? 'CSV uploaded. Switch between trace and single-location analytics.'
          : 'No CSV yet. Start with single-location analytics or upload a file.'}
      </div>

      <button type="button" className="btn btn-ghost mt-6 w-full" onClick={onBackHome}>
        Back to Home
      </button>
    </aside>
  )
}

export default Sidebar
