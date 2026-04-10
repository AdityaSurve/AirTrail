import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/** Right-aligned, just above the horizontal reference line (uses ReferenceLine label viewBox). */
function renderAverageLabel({ viewBox }) {
  if (viewBox == null) return null
  const w = viewBox.width ?? viewBox.upperWidth ?? 0
  const x0 = viewBox.x ?? 0
  const yLine = viewBox.y ?? 0
  if (w <= 0) return null
  return (
    <text
      x={x0 + w - 2}
      y={yLine}
      dy="-0.35em"
      fill="#fb7185"
      fontSize={11}
      fontWeight={600}
      textAnchor="end"
      className="recharts-reference-line-label"
    >
      Average
    </text>
  )
}

function tooltipDateTimeLabel(_label, items) {
  const row = items?.[0]?.payload
  if (row?.ts != null) {
    return new Date(row.ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  return row?.label ?? ''
}

const PollutionExposureOverTime = ({ data, mode, average, whoGuideline, unitLabel, pollutant }) => {
  const unit = unitLabel || 'µg/m³'
  return (
    <article className="glass rounded-2xl p-4">
      <h3 className="text-lg font-semibold text-slate-100">
        {mode === 'trace' ? 'Pollution Exposure Over Time' : 'Single Location Trend'}
      </h3>
      <p className="mt-1 text-xs text-slate-400">
        {pollutant ? `${pollutant} · ` : null}
        Dashed pink: session average · Dashed green: WHO guideline ({whoGuideline != null ? `${whoGuideline} ${unit}` : '—'})
        . Hover a point for full date and time.
      </p>
      <div className="chart-surface mt-4 h-72 min-h-0 min-w-0 overflow-hidden rounded-xl">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="rgba(148,163,184,0.15)" strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              stroke="rgba(148,163,184,0.2)"
              tick={false}
              tickLine={false}
              axisLine={{ stroke: 'rgba(148,163,184,0.2)' }}
              label={{ value: 'Time', position: 'insideBottom', fill: '#94a3b8' }}
            />
            <YAxis stroke="#94a3b8" label={{ value: unit, angle: -90, position: 'insideLeft', fill: '#94a3b8', offset: 20 }} tickLine={false} />
            <Tooltip
              cursor={false}
              labelFormatter={tooltipDateTimeLabel}
              formatter={(value) => [
                value != null && Number.isFinite(Number(value)) ? Number(value).toFixed(1) : '—',
                `Concentration (${unit})`,
              ]}
              contentStyle={{
                backgroundColor: '#0f172acc',
                border: '1px solid rgba(148,163,184,0.35)',
                borderRadius: '10px',
                color: '#e2e8f0',
              }}
            />
            {average != null ? (
              <ReferenceLine
                y={average}
                stroke="#fb7185"
                strokeDasharray="5 5"
                label={renderAverageLabel}
              />
            ) : null}
            {whoGuideline != null ? (
              <ReferenceLine y={whoGuideline} stroke="#4ade80" strokeDasharray="4 4" label="WHO" />
            ) : null}
            <Line
              type="monotone"
              dataKey="value"
              stroke="#22d3ee"
              strokeWidth={3}
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}

export default PollutionExposureOverTime
