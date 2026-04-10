import { useState } from 'react'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'

/** Empty string = same-origin `/api/...` (Vite dev proxy → Flask :5000). */
const apiBase = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')
const useSampleOnly = import.meta.env.VITE_USE_SAMPLE_ONLY === 'true'
const hasApi = !useSampleOnly

const App = () => {
  const [page, setPage] = useState('home')

  return page === 'home' ? (
    <Home onOpenDashboard={() => setPage('dashboard')} />
  ) : (
    <Dashboard apiBase={apiBase} hasApi={hasApi} onBackHome={() => setPage('home')} />
  )
}

export default App