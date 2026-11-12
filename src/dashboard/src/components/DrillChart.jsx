import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, get } from '../api.js'
import { barProps, barTooltip } from './chartTheme.js'

const LEVELS = ['year', 'quarter', 'month', 'day', 'hour']
const LEVEL_NAME = { year: 'Năm', quarter: 'Quý', month: 'Tháng', day: 'Ngày', hour: 'Giờ' }

// Roll-up / Drill-down: bấm cột để khoan xuống cấp sau, bấm đường dẫn phía trên để cuộn lên
export default function DrillChart({ filters }) {
  const [path, setPath] = useState([])      // [{level,key,label}]
  const [rows, setRows] = useState([])
  const level = LEVELS[path.length]

  const params = { ...filters, level }
  path.forEach((p) => { params['d_' + p.level] = p.key })   // d_year, d_quarter, d_month, d_day

  useEffect(() => {
    get('olap/drill', params).then(setRows).catch(() => setRows([]))
  }, [JSON.stringify(params)])           // eslint-disable-line

  const drillInto = (e) => {
    const row = e?.payload ?? e
    if (!row || level === 'hour') return
    setPath([...path, { level, key: row.key, label: row.label }])
  }

  return (
    <section className="card">
      <h3>Xu hướng theo thời gian (Roll-up / Drill-down)</h3>
      <div className="crumbs">
        <button onClick={() => setPath([])} className={path.length ? 'link' : 'cur'}>Tất cả các năm</button>
        {path.map((p, i) => (
          <span key={i}> › <button className={i === path.length - 1 ? 'cur' : 'link'}
            onClick={() => setPath(path.slice(0, i + 1))}>{LEVEL_NAME[p.level]} {p.label}</button></span>
        ))}
        <span className="hint">{level === 'hour' ? 'Cấp thấp nhất (giờ)' : `Bấm vào cột để khoan xuống cấp ${LEVEL_NAME[LEVELS[path.length + 1]]}`}</span>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" />
          <YAxis width={84} tickFormatter={(v) => fmt(v)} />
          <Tooltip {...barTooltip} formatter={(v) => fmt(v)} />
          <Legend />
          <Bar {...barProps} dataKey="registered" name="Đăng ký" stackId="a" fill="#2563eb" cursor={level === 'hour' ? 'default' : 'pointer'} onClick={drillInto} />
          <Bar {...barProps} dataKey="casual" name="Vãng lai" stackId="a" fill="#f59e0b" cursor={level === 'hour' ? 'default' : 'pointer'} onClick={drillInto} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
