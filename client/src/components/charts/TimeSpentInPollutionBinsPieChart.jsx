import { useCallback, useEffect, useRef, useState } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#34d399', '#facc15', '#fb7185']

function formatMinutes(m) {
  const n = Math.round(Number(m)) || 0
  if (n <= 0) return '0 min'
  if (n < 60) return `${n} min`
  const h = Math.floor(n / 60)
  const r = n % 60
  return r > 0 ? `${h}h ${r}m` : `${h}h`
}

function DonutCenterReadout({ hoveredIndex, total, data, colors }) {
  const idle = hoveredIndex == null || total <= 0
  const row = !idle ? data[hoveredIndex] : null
  const pct =
    !idle && row && total > 0 ? ((row.value / total) * 100).toFixed(1) : null
  const accent = !idle ? colors[hoveredIndex % colors.length] : '#64748b'

  return (
    <div
      className="pointer-events-none absolute left-1/2 z-10 w-38 -translate-x-1/2 text-center"
      style={{ top: '40%' }}
      aria-live="polite"
    >
      {idle ? (
        <div className="flex flex-col gap-0.5">
          <p className="text-[0.7rem] font-medium uppercase tracking-wider text-slate-500">
            Hover a tier
          </p>
          <p className="text-xs text-slate-600">{formatMinutes(total)} total</p>
        </div>
      ) : (
        <div className="flex flex-col gap-0.5">
          <p
            className="text-3xl font-bold tabular-nums leading-none tracking-tight"
            style={{ color: accent }}
          >
            {pct}%
          </p>
          <p className="text-sm font-semibold text-slate-100">{formatMinutes(row.value)}</p>
          <p className="truncate text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
            {row.name}
          </p>
        </div>
      )}
    </div>
  )
}

/** Recharts sorts legend `payload` (e.g. by name), so list index ≠ pie `data` index. */
function legendItemToDataIndex(item, data) {
  const name = item?.value ?? item?.payload?.name
  if (name == null) return -1
  const i = data.findIndex((d) => d.name === name)
  return i
}

function InteractiveLegend({ payload, data, colors, onEnter, onLeaveSchedule }) {
  if (!payload?.length) return null
  return (
    <ul className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-2 pt-2 pb-1">
      {payload.map((item) => {
        const dataIndex = legendItemToDataIndex(item, data)
        const safeIndex = dataIndex >= 0 ? dataIndex : 0
        return (
          <li key={item.value}>
            <button
              type="button"
              className="flex cursor-default items-center gap-2 rounded-lg border border-transparent px-2.5 py-1.5 text-left text-[11px] text-slate-300 transition-colors hover:border-white/15 hover:bg-white/5 focus-visible:border-cyan-400/40 focus-visible:outline-none"
              onMouseEnter={() => onEnter(dataIndex >= 0 ? dataIndex : null)}
              onMouseLeave={onLeaveSchedule}
              onFocus={() => onEnter(dataIndex >= 0 ? dataIndex : null)}
              onBlur={onLeaveSchedule}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-white/20"
                style={{ backgroundColor: item.color ?? colors[safeIndex % colors.length] }}
              />
              <span className="font-medium tracking-wide">{item.value}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

const TimeSpentInPollutionBinsPieChart = ({ bins, mode, binLabels, pollutant }) => {
  const short = binLabels?.shortLabel || ['AQG', 'Moderate', 'High']
  const long = binLabels?.labels || short

  const data = [
    { name: short[0], subtitle: long[0], value: Math.max(0, Math.round(bins.good)) },
    { name: short[1], subtitle: long[1], value: Math.max(0, Math.round(bins.moderate)) },
    { name: short[2], subtitle: long[2], value: Math.max(0, Math.round(bins.poor)) },
  ]

  const total = data.reduce((s, d) => s + d.value, 0)

  const [hoveredBin, setHoveredBin] = useState(null)
  const clearTimerRef = useRef(null)

  const cancelClear = useCallback(() => {
    if (clearTimerRef.current != null) {
      window.clearTimeout(clearTimerRef.current)
      clearTimerRef.current = null
    }
  }, [])

  const setHovered = useCallback(
    (index) => {
      cancelClear()
      setHoveredBin(index)
    },
    [cancelClear],
  )

  const scheduleClear = useCallback(() => {
    cancelClear()
    clearTimerRef.current = window.setTimeout(() => {
      setHoveredBin(null)
      clearTimerRef.current = null
    }, 120)
  }, [cancelClear])

  useEffect(() => () => cancelClear(), [cancelClear])

  const handlePieMouseEnter = useCallback(
    (_entry, index) => {
      const i = typeof index === 'number' ? index : Number(index)
      setHovered(Number.isFinite(i) ? i : null)
    },
    [setHovered],
  )

  const legendContent = useCallback(
    (props) => (
      <InteractiveLegend
        {...props}
        data={data}
        colors={COLORS}
        onEnter={setHovered}
        onLeaveSchedule={scheduleClear}
      />
    ),
    [data, setHovered, scheduleClear],
  )

  return (
    <article className="glass rounded-2xl p-4">
      <h3 className="text-lg font-semibold text-slate-100">
        {mode === 'trace' ? 'Time in WHO tiers (route)' : 'WHO tiers (reference trace sample)'}
      </h3>
      <p className="mt-1 text-xs text-slate-400">
        Pollutant: <span className="text-cyan-200">{pollutant}</span> — bins use WHO guideline + interim bands (
        {binLabels?.unit || 'µg/m³'}).
      </p>
      <div className="chart-surface relative mt-3 h-100 min-h-70 min-w-0 overflow-hidden rounded-xl">
        {total <= 0 ? (
          <p className="flex h-full items-center justify-center px-4 text-center text-sm text-slate-500">
            No time in tier data yet — adjust the time range, pollutant, or upload a trace with matched points.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="48%"
                outerRadius={100}
                innerRadius={60}
                label={false}
                labelLine={false}
                stroke="rgba(15,23,42,0.85)"
                strokeWidth={1}
                onMouseEnter={handlePieMouseEnter}
                onMouseLeave={scheduleClear}
              >
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Legend
                verticalAlign="bottom"
                layout="horizontal"
                align="center"
                wrapperStyle={{ width: '100%' }}
                content={legendContent}
              />
              <Tooltip
                cursor={false}
                formatter={(v) => [`${v} min`, 'Duration']}
                contentStyle={{
                  backgroundColor: '#0f172acc',
                  border: '1px solid rgba(148,163,184,0.35)',
                  borderRadius: '10px',
                  color: '#e2e8f0',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
        {total > 0 ? (
          <DonutCenterReadout
            hoveredIndex={hoveredBin}
            total={total}
            data={data}
            colors={COLORS}
          />
        ) : null}
      </div>
    </article>
  )
}

export default TimeSpentInPollutionBinsPieChart
