import { useEffect, useState } from 'react'
import { get } from './api.js'
import FilterBar from './components/FilterBar.jsx'
import KpiCards from './components/KpiCards.jsx'
import DrillChart from './components/DrillChart.jsx'
import PivotTable from './components/PivotTable.jsx'
import { DayTypeChart, HourlyChart, UserChart, WeatherChart } from './components/Charts.jsx'

export default function App() {
  const [options, setOptions] = useState({})
  const [filters, setFilters] = useState({})
  const [kpi, setKpi] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { get('filters').then(setOptions).catch((e) => setError(e.message)) }, [])
  useEffect(() => { get('kpis', filters).then(setKpi).catch((e) => setError(e.message)) }, [JSON.stringify(filters)]) // eslint-disable-line

  return (
    <main>
      <header>
        <h1>Dashboard phân tích nhu cầu thuê xe đạp công cộng</h1>
        <p>Kho dữ liệu Bike Sharing (2011–2012) · mọi biểu đồ cập nhật theo bộ lọc bên dưới</p>
      </header>
      {error && <div className="card err">Không kết nối được API ({error}). Hãy chắc chắn FastAPI đang chạy ở cổng 8000.</div>}
      <FilterBar options={options} value={filters} onChange={setFilters} />
      <KpiCards k={kpi} />
      <DrillChart filters={filters} />
      <div className="grid2">
        <HourlyChart filters={filters} />
        <WeatherChart filters={filters} />
        <DayTypeChart filters={filters} />
        <UserChart filters={filters} />
      </div>
      <PivotTable filters={filters} />
    </main>
  )
}
