// DSS: phân loại nhu cầu (FR09) + khuyến nghị chuẩn bị xe (FR10)
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, get, pct } from '../api.js'

export const LEVEL_COLOR = { low: '#16a34a', medium: '#f59e0b', high: '#dc2626' }
const LEVEL_LABEL = { low: 'Thấp', medium: 'Trung bình', high: 'Cao' }
const WEATHERS = [[1, 'Clear'], [2, 'Mist'], [3, 'Light rain/snow'], [4, 'Heavy rain/snow']]
const QPRESETS = { '33-67': [1 / 3, 2 / 3, 'P33 / P67 (mặc định)'], '25-75': [0.25, 0.75, 'P25 / P75'] }

const Badge = ({ level }) => level
  ? <span className="badge" style={{ background: LEVEL_COLOR[level] }}>{LEVEL_LABEL[level]}</span>
  : <span className="badge nodata">Không có dữ liệu</span>

export default function DssPanel({ filters }) {
  // Bước 1: kỳ lịch sử = bộ lọc Năm / Mùa ở trên; tình huống sắp tới chọn tại đây
  const period = { year: filters.year, season: filters.season }
  const [dayGroup, setDayGroup] = useState('working')
  const [weather, setWeather] = useState(1)
  const [preset, setPreset] = useState('33-67')
  const [survey, setSurvey] = useState(null)
  const [plan, setPlan] = useState(null)
  const [matrix, setMatrix] = useState(null)
  const [err, setErr] = useState('')
  const [q_low, q_high] = QPRESETS[preset]
  const key = JSON.stringify(period) + preset

  useEffect(() => {
    setErr('')
    get('dss/thresholds', { ...period, q_low, q_high }).then(setSurvey).catch((e) => setErr(e.message))
    get('dss/matrix', { ...period, q_low, q_high }).then(setMatrix).catch(() => setMatrix(null))
  }, [key]) // eslint-disable-line
  useEffect(() => {
    get('dss/plan', { ...period, q_low, q_high, day_group: dayGroup, weather }).then(setPlan).catch((e) => setErr(e.message))
  }, [key, dayGroup, weather]) // eslint-disable-line

  const th = plan?.thresholds
  return (
    <section className="card dss">
      <h3>Hệ hỗ trợ quyết định: mức chuẩn bị xe theo giờ</h3>
      <p className="note">
        Kỳ lịch sử dùng để tính: theo bộ lọc <b>Năm</b> và <b>Mùa</b> ở trên (các bộ lọc khác không áp dụng cho DSS).
        Hệ thống chỉ khuyến nghị <b>mức độ</b> chuẩn bị vì dữ liệu nguồn không có số xe sẵn sàng hay vị trí trạm.
      </p>

      <div className="dssctl">
        <label>Loại ngày sắp tới: <select value={dayGroup} onChange={(e) => setDayGroup(e.target.value)}>
          <option value="working">Ngày làm việc</option><option value="non_working">Ngày nghỉ (cuối tuần / lễ)</option></select></label>
        <label>Thời tiết dự kiến: <select value={weather} onChange={(e) => setWeather(Number(e.target.value))}>
          {WEATHERS.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></label>
        <label>Ngưỡng phân loại: <select value={preset} onChange={(e) => setPreset(e.target.value)}>
          {Object.entries(QPRESETS).map(([k, v]) => <option key={k} value={k}>{v[2]}</option>)}</select></label>
      </div>
      {err && <p className="err">{err}</p>}

      {survey && (
        <div className="dssgrid">
          <div className="sub">
            <h4>Khảo sát phân phối lượt thuê / giờ ({fmt(survey.distribution.n_obs)} giờ quan sát)</h4>
            <table><tbody>
              <tr>{survey.distribution.percentiles.map((p) => <th key={p.q}>P{(p.q * 100).toFixed(0)}</th>)}<th>TB</th></tr>
              <tr>{survey.distribution.percentiles.map((p) => <td key={p.q}>{fmt(p.value)}</td>)}<td>{fmt(survey.distribution.mean, 1)}</td></tr>
            </tbody></table>
          </div>
          <div className="sub">
            <h4>Quy tắc ra quyết định</h4>
            <table><tbody>
              <tr><th>Mức</th><th>Điều kiện (TB lượt thuê / giờ)</th><th>% giờ quan sát</th><th>Khuyến nghị</th></tr>
              {survey.levels.map(({ level, recommendation }) => (
                <tr key={level}><td><Badge level={level} /></td>
                  <td>{level === 'low' ? `< ${fmt(survey.thresholds.low)}` : level === 'high' ? `> ${fmt(survey.thresholds.high)}`
                    : `${fmt(survey.thresholds.low)} – ${fmt(survey.thresholds.high)}`}</td>
                  <td>{pct(survey.observation_share[level])}</td>
                  <td className="left">{recommendation}</td></tr>))}
            </tbody></table>
          </div>
        </div>
      )}

      {plan && (<>
        <div className="alerts">
          {plan.alerts.length === 0 && <div className="alert ok">Không có khung giờ nhu cầu cao trong tình huống này: duy trì mức chuẩn bị cơ bản / theo dõi.</div>}
          {plan.alerts.map((a) => (
            <div className="alert" key={a.label}>⚠ {a.message}{a.low_reliability && ' (ít dữ liệu lịch sử, chỉ để tham khảo)'}</div>))}
          {plan.notes.map((n) => <div className="alert info" key={n}>{n}</div>)}
        </div>

        <h4>Mức nhu cầu dự kiến theo giờ: {plan.scenario.day_group_label}, {plan.scenario.weather_label}</h4>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={plan.hours}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="hour" tickFormatter={(h) => `${h}h`} />
            <YAxis width={84} tickFormatter={(v) => fmt(v)} />
            <Tooltip formatter={(v, n, p) => [`${fmt(v, 1)} lượt/giờ (${fmt(p.payload.n_obs)} giờ quan sát)`, p.payload.level_label]}
              labelFormatter={(h) => `${String(h).padStart(2, '0')}:00`} />
            <ReferenceLine y={th.low} stroke={LEVEL_COLOR.low} strokeDasharray="4 4" label={{ value: 'Ngưỡng thấp', position: 'insideTopLeft', fontSize: 11 }} />
            <ReferenceLine y={th.high} stroke={LEVEL_COLOR.high} strokeDasharray="4 4" label={{ value: 'Ngưỡng cao', position: 'insideTopLeft', fontSize: 11 }} />
            <Bar dataKey="avg_rentals">
              {plan.hours.map((h) => <Cell key={h.hour} fill={LEVEL_COLOR[h.level] || '#9ca3af'} fillOpacity={h.reliable ? 1 : 0.45} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="note">Cột nhạt = nhóm có dưới {survey?.min_obs ?? 30} giờ quan sát (độ tin cậy thấp).</p>

        <div className="tablewrap"><table>
          <thead><tr><th>Giờ</th><th>TB lượt / giờ</th><th>So với TB kỳ</th><th>Số giờ quan sát</th><th>% người dùng đăng ký</th><th>Mức</th><th>Khuyến nghị</th></tr></thead>
          <tbody>{plan.hours.map((h) => (
            <tr key={h.hour} className={h.level === 'high' ? 'hi' : ''}>
              <th>{h.label}</th><td>{fmt(h.avg_rentals, 1)}</td>
              <td>{h.ratio_to_mean == null ? '—' : `×${h.ratio_to_mean.toFixed(2)}`}</td>
              <td>{fmt(h.n_obs)}{h.n_obs > 0 && !h.reliable && ' *'}</td>
              <td>{pct(h.registered_share)}</td>
              <td><Badge level={h.level} /></td><td className="left">{h.recommendation}</td></tr>))}
          </tbody>
        </table></div>
      </>)}

      {matrix && (<>
        <h4>Ma trận phân loại: giờ × loại ngày × thời tiết</h4>
        <div className="tablewrap"><table className="matrix">
          <thead><tr><th>Giờ</th>{matrix.cols.map((c) => <th key={c.label}>{c.label}</th>)}</tr></thead>
          <tbody>{Array.from({ length: 24 }, (_, h) => (
            <tr key={h}><th>{String(h).padStart(2, '0')}h</th>{matrix.cols.map((c) => {
              const x = matrix.cells.find((e) => e.hour === h && e.day_group === c.day_group && e.weather === c.weather)
              return <td key={c.label} title={x?.level ? `${fmt(x.avg_rentals, 1)} lượt/giờ, ${x.n_obs} giờ quan sát` : 'Không có dữ liệu'}
                style={{ background: x?.level ? LEVEL_COLOR[x.level] : 'transparent', opacity: x?.reliable ? 1 : 0.45, color: x?.level ? '#fff' : 'inherit' }}>
                {x?.level ? fmt(x.avg_rentals) : '—'}</td>
            })}</tr>))}
          </tbody>
        </table></div>
        <p className="note">Ô nhạt: dưới {survey?.min_obs ?? 30} giờ quan sát. "Heavy rain/snow" gần như không có dữ liệu lịch sử.</p>
      </>)}
    </section>
  )
}
