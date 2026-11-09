import { useEffect, useState } from 'react'
import { get } from './api.js'
import FilterBar from './components/FilterBar.jsx'
import KpiCards from './components/KpiCards.jsx'
import DrillChart from './components/DrillChart.jsx'
import PivotTable from './components/PivotTable.jsx'
import DssPanel from './components/DssPanel.jsx'
import { ClimateChart, DayTypeChart, HourlyChart, UserChart, WeatherChart } from './components/Charts.jsx'

// Biểu tượng đường nét (stroke) 20x20 cho menu
const ICONS = {
  overview: 'M3 10.5 10 4l7 6.5M5 9v7h4v-4h2v4h4V9',
  time: 'M10 3.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM10 6.5V10l2.5 2',
  weather: 'M6 14.5h8a3 3 0 0 0 .4-6A4.5 4.5 0 0 0 5.6 9 2.8 2.8 0 0 0 6 14.5Z',
  pivot: 'M3.5 4h13v12h-13zM3.5 8h13M8 4v12',
  dss: 'M10 3 3.5 6v4.2c0 3.4 2.8 5.9 6.5 6.8 3.7-.9 6.5-3.4 6.5-6.8V6L10 3ZM7.2 10l2 2 3.6-3.8',
}

// Mỗi trang một nhóm câu hỏi nghiệp vụ; bộ lọc dùng chung giữa các trang.
const PAGES = [
  { id: 'overview', label: 'Tổng quan', title: 'Tổng quan', desc: 'Chỉ số chính (KPI) và xu hướng lượt thuê theo thời gian. Bấm vào cột để xem chi tiết hơn (drill-down).' },
  { id: 'time', label: 'Theo thời gian', title: 'Nhu cầu theo thời gian', desc: 'Nhóm 1 - nhu cầu theo giờ trong ngày, theo loại ngày và theo nhóm người dùng.' },
  { id: 'weather', label: 'Thời tiết & khí hậu', title: 'Thời tiết & khí hậu', desc: 'Nhóm 2 - ảnh hưởng của thời tiết, nhiệt độ và độ ẩm đến nhu cầu thuê xe.' },
  { id: 'pivot', label: 'Bảng Pivot', title: 'Bảng Pivot', desc: 'Phân tích chéo hai chiều: chọn hàng, cột và độ đo.' },
  { id: 'dss', label: 'Hỗ trợ quyết định', title: 'Hỗ trợ quyết định', desc: 'Nhóm 3 - phân loại mức nhu cầu theo giờ, khuyến nghị và cảnh báo chuẩn bị xe. Kỳ lịch sử lấy từ bộ lọc Năm và Mùa.',
    fields: ['year', 'season'] },
]
const pageFromHash = () => {
  const id = window.location.hash.replace(/^#\/?/, '')
  return PAGES.some((p) => p.id === id) ? id : 'overview'
}

function Icon({ d }) {
  return <svg className="ico" viewBox="0 0 20 20" aria-hidden="true"><path d={d} /></svg>
}

export default function App() {
  const [options, setOptions] = useState({})
  const [filters, setFilters] = useState({})
  const [kpi, setKpi] = useState(null)
  const [error, setError] = useState('')
  const [page, setPage] = useState(pageFromHash)

  useEffect(() => { get('filters').then(setOptions).catch((e) => setError(e.message)) }, [])
  useEffect(() => { get('kpis', filters).then(setKpi).catch((e) => setError(e.message)) }, [JSON.stringify(filters)]) // eslint-disable-line
  useEffect(() => {                       // nút Back/Forward của trình duyệt và link #/<trang>
    const onHash = () => { setPage(pageFromHash()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const current = PAGES.find((p) => p.id === page)

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo" aria-hidden="true">
            <svg viewBox="0 0 24 24"><circle cx="6" cy="16" r="3.5" /><circle cx="18" cy="16" r="3.5" /><path d="M6 16l4-7h5l3 7M10 9 8.5 6H7m8 3-1.5-3h2.5" /></svg>
          </span>
          <span><b>Bike Sharing</b><small>Kho dữ liệu &amp; DSS</small></span>
        </div>
        <nav aria-label="Các trang dashboard">
          {PAGES.map((p) => (
            <a key={p.id} href={`#/${p.id}`} className={p.id === page ? 'nav on' : 'nav'}
               aria-current={p.id === page ? 'page' : undefined}>
              <Icon d={ICONS[p.id]} /><span>{p.label}</span>
            </a>
          ))}
        </nav>
        <p className="side-foot">Capital Bikeshare, Washington D.C.<br />Dữ liệu 2011–2012 · 17.379 giờ</p>
      </aside>

      <div className="content">
        <header className="pagehead">
          <h1>{current.title}</h1>
          <p>{current.desc}</p>
        </header>
        <FilterBar options={options} value={filters} onChange={setFilters} fields={current.fields} />
        {error && <div className="card err">Không kết nối được API ({error}). Hãy chắc chắn FastAPI đang chạy ở cổng 8000.</div>}

        <div className="pagebody">
          {page === 'overview' && (<>
            <KpiCards k={kpi} />
            <DrillChart filters={filters} />
          </>)}
          {page === 'time' && (<>
            <HourlyChart filters={filters} />
            <div className="grid2">
              <DayTypeChart filters={filters} />
              <UserChart filters={filters} />
            </div>
          </>)}
          {page === 'weather' && (<>
            <WeatherChart filters={filters} />
            <ClimateChart filters={filters} />
          </>)}
          {page === 'pivot' && <PivotTable filters={filters} />}
          {page === 'dss' && <DssPanel filters={filters} />}
        </div>
      </div>
    </div>
  )
}
