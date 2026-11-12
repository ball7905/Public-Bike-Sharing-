import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, get } from '../api.js'
import { activeDot, barProps, barTooltip, lineTooltip } from './chartTheme.js'

function useData(path, params) {
  const [data, setData] = useState([])
  useEffect(() => { get(path, params).then(setData).catch(() => setData([])) }, [path, JSON.stringify(params)]) // eslint-disable-line
  return data
}

export function HourlyChart({ filters }) {
  const data = useData('hourly', filters)
  return (
    <section className="card">
      <h3>Nhu cầu trung bình theo giờ trong ngày</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="hour" tickFormatter={(h) => `${h}h`} />
          <YAxis width={84} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...lineTooltip} formatter={(v) => fmt(v, 1)} labelFormatter={(h) => `${h}:00`} />
          <Legend />
          <Line type="monotone" dataKey="avg_working" name="Ngày làm việc" stroke="#2563eb" dot={false} activeDot={activeDot} strokeWidth={2} />
          <Line type="monotone" dataKey="avg_non_working" name="Ngày nghỉ" stroke="#16a34a" dot={false} activeDot={activeDot} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}

export function WeatherChart({ filters }) {
  const data = useData('weather', filters)
  return (
    <section className="card">
      <h3>Trung bình lượt thuê / giờ theo thời tiết</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis width={84} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...barTooltip} formatter={(v, n, p) => [fmt(v, 1), 'TB / giờ']} labelFormatter={(l, p) => `${l} (${fmt(p?.[0]?.payload?.n_hours)} giờ quan sát)`} />
          <Bar {...barProps} dataKey="avg_hourly" name="TB / giờ" fill="#0ea5e9" />
        </BarChart>
      </ResponsiveContainer>
      <p className="note">Mức "Heavy rain/snow" chỉ có 3 giờ quan sát nên kết quả không đủ tin cậy.</p>
    </section>
  )
}

export function DayTypeChart({ filters }) {
  const data = useData('day-type', filters)
  return (
    <section className="card">
      <h3>Trung bình lượt thuê / ngày theo loại ngày</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis width={84} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...barTooltip} formatter={(v) => fmt(v)} labelFormatter={(l, p) => `${l} (${fmt(p?.[0]?.payload?.n_days)} ngày)`} />
          <Bar {...barProps} dataKey="avg_daily" name="TB / ngày" fill="#8b5cf6" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}

export function UserChart({ filters }) {
  const [by, setBy] = useState('hour')
  const data = useData('users', { ...filters, by })
  return (
    <section className="card">
      <h3>Người dùng đăng ký và vãng lai
        <select value={by} onChange={(e) => setBy(e.target.value)}>
          <option value="hour">Theo giờ</option><option value="weekday">Theo thứ</option><option value="month">Theo tháng</option>
        </select>
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" interval="preserveStartEnd" />
          <YAxis width={84} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...barTooltip} formatter={(v) => fmt(v)} />
          <Legend />
          <Bar {...barProps} dataKey="registered" name="Đăng ký" stackId="u" fill="#2563eb" />
          <Bar {...barProps} dataKey="casual" name="Vãng lai" stackId="u" fill="#f59e0b" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}

// FR06 / Nhóm 2: ảnh hưởng của nhiệt độ và độ ẩm
const CORR_LABELS = { temp: 'Nhiệt độ', atemp: 'Nhiệt độ cảm nhận', humidity: 'Độ ẩm', windspeed: 'Tốc độ gió' }
const r3 = (v) => (v === null || v === undefined ? '—' : v.toFixed(3))

export function ClimateChart({ filters }) {
  const [by, setBy] = useState('temp')
  const [data, setData] = useState(null)
  useEffect(() => { get('climate', { ...filters, by }).then(setData).catch(() => setData(null)) }, [by, JSON.stringify(filters)]) // eslint-disable-line
  const c = data?.correlation
  return (
    <section className="card">
      <h3>Ảnh hưởng của nhiệt độ và độ ẩm đến nhu cầu
        <select value={by} onChange={(e) => setBy(e.target.value)}>
          <option value="temp">Theo nhiệt độ (°C)</option><option value="humidity">Theo độ ẩm (%)</option>
        </select>
      </h3>
      <div className="climate">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data?.bins || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" interval={0} fontSize={12} />
            <YAxis width={84} tickFormatter={(v) => fmt(v)} />
            <Tooltip formatter={(v) => fmt(v, 1)}
              labelFormatter={(l, p) => `${l} (${fmt(p?.[0]?.payload?.n_hours)} giờ quan sát${p?.[0]?.payload?.reliable === false ? ', ít mẫu' : ''})`} />
            <Legend />
            <Bar dataKey="avg_registered" name="Đăng ký (TB / giờ)" stackId="u" fill="#2563eb" />
            <Bar dataKey="avg_casual" name="Vãng lai (TB / giờ)" stackId="u" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
        {c && (
          <div>
            <table>
              <thead><tr><th>Hệ số tương quan Pearson với lượt thuê</th><th>Mức giờ</th><th>Mức ngày</th></tr></thead>
              <tbody>{Object.keys(CORR_LABELS).map((k) => (
                <tr key={k}><th>{CORR_LABELS[k]}</th><td>{r3(c.hourly[k])}</td><td>{r3(c.daily[k])}</td></tr>))}
                <tr><th>Số quan sát</th><td>{fmt(c.hourly.n)} giờ</td><td>{fmt(c.daily.n)} ngày</td></tr>
              </tbody>
            </table>
            <p className="note">
              Mức ngày dùng tổng lượt thuê / ngày và giá trị thời tiết trung bình ngày, giúp loại bớt ảnh hưởng của giờ trong ngày
              (ban đêm vừa ẩm hơn vừa ít người thuê). Tương quan không phải quan hệ nhân quả.
              {data.bins.some((b) => !b.reliable) && ` Khoảng có dưới ${data.min_obs} giờ quan sát không đủ tin cậy (vd. độ ẩm 0–10% chủ yếu là lỗi đo hum = 0).`}
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
