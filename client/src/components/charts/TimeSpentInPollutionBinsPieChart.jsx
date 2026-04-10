import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#34d399', '#facc15', '#fb7185']

const TimeSpentInPollutionBinsPieChart = ({ bins, mode, binLabels, pollutant }) => {
  const short = binLabels?.shortLabel || ['AQG', 'Moderate', 'High']
  const long = binLabels?.labels || short

  const data = [
    { name: short[0], subtitle: long[0], value: Math.max(0, Math.round(bins.good)) },
    { name: short[1], subtitle: long[1], value: Math.max(0, Math.round(bins.moderate)) },
    { name: short[2], subtitle: long[2], value: Math.max(0, Math.round(bins.poor)) },
  ]
  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <article className="glass rounded-2xl p-4">
      <h3 className="text-lg font-semibold text-slate-100">
        {mode === 'trace' ? 'Time in WHO tiers (route)' : 'WHO tiers (reference trace sample)'}
      </h3>
      <p className="mt-1 text-xs text-slate-400">
        Pollutant: <span className="text-cyan-200">{pollutant}</span> — bins use WHO guideline + interim bands (
        {binLabels?.unit || 'µg/m³'}).
      </p>
      {/* h-103 is not a default Tailwind size — parent height was effectively missing, so ResponsiveContainer collapsed */}
      <div className="chart-surface mt-3 h-100 min-h-70 min-w-0 overflow-hidden rounded-xl">
        {total <= 0 ? (
          <p className="flex h-full items-center justify-center px-4 text-center text-sm text-slate-500">
            No time in tier data yet — adjust the time range, pollutant, or upload a trace with matched points.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                innerRadius={60}
                label={false}
                labelLine={false}
              >
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Legend verticalAlign="bottom" height={32} wrapperStyle={{ color: '#cbd5e1', fontSize: 11 }} />
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
      </div>
    </article>
  )
}

export default TimeSpentInPollutionBinsPieChart
