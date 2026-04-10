const highlights = [
  {
    title: 'Upload Mobility Traces',
    desc: 'Upload your CSV trace and run analysis on geospatial movement with mapped pollution readings.',
  },
  {
    title: 'Exposure Analytics',
    desc: 'Track mean, peak and cumulative exposure with time series and pollution bins.',
  },
  {
    title: 'Single location',
    desc: 'Query the ingested monitoring network for any lat/lon, time range, and pollutant (no trace upload required).',
  },
]

const workflow = [
  {
    step: '01',
    title: 'Ingest Data',
    desc: 'Upload movement traces (CSV) or start with a single location if you are in early exploration mode.',
  },
  {
    step: '02',
    title: 'Map Exposure',
    desc: 'Match trace points with nearby pollution observations and compute concentration over time.',
  },
  {
    step: '03',
    title: 'Visualize & Export',
    desc: 'Review charts and geospatial patterns, then download processed output as CSV.',
  },
]

const sections = [
  {
    title: 'What AirTrail Solves',
    body: 'Urban mobility and pollution datasets are hard to combine quickly. AirTrail creates a practical analysis surface where route traces become interpretable exposure insights in minutes.',
  },
  {
    title: 'Who It Is For',
    body: 'Researchers, public-health analysts, and urban planners who need clear route-level exposure trends and a repeatable dashboard workflow.',
  },
  {
    title: 'Why This Interface',
    body: 'The dashboard is designed for fast decision making: status-first sidebar actions, clean visual hierarchy, and rich map + chart context without clutter.',
  },
]

const Home = ({ onOpenDashboard }) => {
  return (
    <div className="home-shell">
      <div className="glow glow-a" />
      <div className="glow glow-b" />
      <div className="glow glow-c" />

      <section className="home-hero glass">
        <p className="eyebrow">AirTrail Project</p>
        <h1>Understand pollution exposure along movement traces.</h1>
        <p>
          AirTrail helps you upload trajectory data, align it with pollution measurements, and extract
          clear insights for mobility health research.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={onOpenDashboard}>
            Open Dashboard
          </button>
          <button className="btn btn-ghost" onClick={onOpenDashboard}>
            Try Single Location
          </button>
        </div>
      </section>

      <section className="home-section">
        <div className="section-header">
          <p className="eyebrow">Overview</p>
          <h2>Project Outline</h2>
        </div>
        <div className="home-cards">
          {highlights.map((item) => (
            <article key={item.title} className="glass feature-card">
              <h3>{item.title}</h3>
              <p>{item.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-section glass home-band">
        <div className="section-header">
          <p className="eyebrow">Workflow</p>
          <h2>How Analysis Flows</h2>
        </div>
        <div className="workflow-grid">
          {workflow.map((item) => (
            <article key={item.step} className="workflow-card">
              <span>{item.step}</span>
              <h3>{item.title}</h3>
              <p>{item.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="section-header">
          <p className="eyebrow">Deep Dive</p>
          <h2>System Intent & Product Thinking</h2>
        </div>
        <div className="detail-grid">
          {sections.map((item) => (
            <article key={item.title} className="glass detail-card">
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-section glass cta-band">
        <div>
          <p className="eyebrow">Ready To Explore</p>
          <h2>Open the dashboard and start with your first analysis run.</h2>
          <p>
            You can begin with single-location analytics immediately, then switch to trace mode after
            uploading your CSV.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onOpenDashboard}>
          Launch Dashboard
        </button>
      </section>
    </div>
  )
}

export default Home