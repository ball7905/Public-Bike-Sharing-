import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, get } from '../api.js'

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
          <Tooltip formatter={(v) => fmt(v, 1)} labelFormatter={(h) => `${h}:00`} />
          <Legend />
          <Line type="monotone" dataKey="avg_working" name="Ngày làm việc" stroke="#2563eb" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="avg_non_working" name="Ngày nghỉ" stroke="#16a34a" dot={false} strokeWidth={2} />
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
          <Tooltip formatter={(v, n, p) => [fmt(v, 1), 'TB / giờ']} labelFormatter={(l, p) => `${l} (${fmt(p?.[0]?.payload?.n_hours)} giờ quan sát)`} />
          <Bar dataKey="avg_hourly" name="TB / giờ" fill="#0ea5e9" />
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
          <Tooltip formatter={(v) => fmt(v)} labelFormatter={(l, p) => `${l} (${fmt(p?.[0]?.payload?.n_days)} ngày)`} />
          <Bar dataKey="avg_daily" name="TB / ngày" fill="#8b5cf6" />
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
          <Tooltip formatter={(v) => fmt(v)} />
          <Legend />
          <Bar dataKey="registered" name="Đăng ký" stackId="u" fill="#2563eb" />
          <Bar dataKey="casual" name="Vãng lai" stackId="u" fill="#f59e0b" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
