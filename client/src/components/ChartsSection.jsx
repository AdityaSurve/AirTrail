import TopBoxes from './charts/TopBoxes'
import PollutionExposureOverTime from './charts/PollutionExposureOverTime'
import TimeSpentInPollutionBinsPieChart from './charts/TimeSpentInPollutionBinsPieChart'
import Map from './Map'

const ChartsSection = ({
  processed,
  mode,
  hasUploadedCsv,
  traceTimeRange,
  traceBoundsMin,
  traceBoundsMax,
  onTraceTimeRangeChange,
}) => {
  const chartData = mode === 'trace' ? processed.timeline : processed.singleLocationSeries

  return (
    <section className="charts-column min-w-0 space-y-4 overflow-hidden">
      {!hasUploadedCsv ? (
        <div className="glass rounded-2xl p-4 text-sm text-slate-300">
          You are in single-location mode. Upload a CSV to unlock route-based trace analytics.
        </div>
      ) : null}

      {hasUploadedCsv && mode === 'trace' && traceTimeRange ? (
        <div className="glass rounded-2xl p-4">
          <p className="text-sm font-medium text-slate-100">Trace time filter</p>
          <p className="mt-1 text-xs text-slate-400">
            Slide to restrict map and charts to a window within your file (WHO bins use the filtered segment
            durations).
          </p>
          <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center">
            <label className="flex flex-1 flex-col text-xs text-slate-400">
              From
              <input
                type="datetime-local"
                className="mt-1 rounded-lg border border-white/15 bg-slate-900/60 px-2 py-2 text-slate-100"
                value={toLocal(traceTimeRange[0])}
                min={toLocal(traceBoundsMin)}
                max={toLocal(traceBoundsMax)}
                onChange={(e) => {
                  const next = new Date(e.target.value)
                  onTraceTimeRangeChange([next, traceTimeRange[1]])
                }}
              />
            </label>
            <label className="flex flex-1 flex-col text-xs text-slate-400">
              To
              <input
                type="datetime-local"
                className="mt-1 rounded-lg border border-white/15 bg-slate-900/60 px-2 py-2 text-slate-100"
                value={toLocal(traceTimeRange[1])}
                min={toLocal(traceBoundsMin)}
                max={toLocal(traceBoundsMax)}
                onChange={(e) => {
                  const next = new Date(e.target.value)
                  onTraceTimeRangeChange([traceTimeRange[0], next])
                }}
              />
            </label>
          </div>
        </div>
      ) : null}

      <div className="flex w-full flex-col items-stretch justify-center gap-4 lg:flex-row">
        <div className="flex w-full min-w-0 flex-col gap-4 lg:max-w-[min(100%,520px)]">
          <TopBoxes processed={processed} mode={mode} hasUploadedCsv={hasUploadedCsv} />
          <TimeSpentInPollutionBinsPieChart
            bins={processed.bins}
            mode={mode}
            binLabels={processed.binLabels}
            pollutant={processed.activePollutant}
          />
        </div>
        <Map
          mode={mode}
          points={processed.points}
          traceSites={processed.traceSites}
          singleQuery={processed.singleQuery}
          unitLabel={processed.unitLabel}
          activePollutant={processed.activePollutant}
        />
      </div>
      <PollutionExposureOverTime
        data={chartData}
        mode={mode}
        average={mode === 'trace' ? processed.summary?.mean : processed.locationAnalytics?.average}
        whoGuideline={processed.whoGuideline}
        unitLabel={processed.unitLabel}
        pollutant={processed.activePollutant}
      />
    </section>
  )
}

function toLocal(d) {
  const x = d instanceof Date ? d : new Date(d)
  const pad = (n) => String(n).padStart(2, '0')
  return `${x.getFullYear()}-${pad(x.getMonth() + 1)}-${pad(x.getDate())}T${pad(x.getHours())}:${pad(x.getMinutes())}`
}

export default ChartsSection
