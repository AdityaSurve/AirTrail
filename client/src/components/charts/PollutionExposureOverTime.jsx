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
      </p>
      <div className="chart-surface mt-4 h-72 min-h-0 min-w-0 overflow-hidden rounded-xl">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="rgba(148,163,184,0.15)" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" label={{ value: unit, angle: -90, position: 'insideLeft', fill: '#94a3b8' }} />
            <Tooltip
              cursor={false}
              contentStyle={{
                backgroundColor: '#0f172acc',
                border: '1px solid rgba(148,163,184,0.35)',
                borderRadius: '10px',
                color: '#e2e8f0',
              }}
            />
            {average != null ? (
              <ReferenceLine y={average} stroke="#fb7185" strokeDasharray="5 5" label="Avg" />
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
