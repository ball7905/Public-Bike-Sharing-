import { useEffect, useState } from 'react'
import { fmt, get } from '../api.js'

const DIMS = { month: 'Tháng', weekday: 'Thứ', hour: 'Giờ', time_band: 'Khung giờ', season: 'Mùa', year: 'Năm', weather: 'Thời tiết', day_type: 'Loại ngày' }

export default function PivotTable({ filters }) {
  const [row, setRow] = useState('month')
  const [col, setCol] = useState('weather')
  const [measure, setMeasure] = useState('avg_hourly')
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (row === col) { setErr('Hàng và cột phải khác nhau'); return }
    setErr('')
    get('olap/pivot', { ...filters, row, col, measure }).then(setData).catch((e) => setErr(e.message))
  }, [row, col, measure, JSON.stringify(filters)])  // eslint-disable-line

  const cell = {}
  let max = 0
  data?.cells.forEach((c) => { cell[c.r + '|' + c.c] = c.value; max = Math.max(max, c.value) })
  const Sel = ({ v, set, label }) => (
    <label>{label} <select value={v} onChange={(e) => set(e.target.value)}>
      {Object.entries(DIMS).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></label>
  )
  return (
    <section className="card">
      <h3>Bảng Pivot</h3>
      <div className="pivotctl">
        <Sel v={row} set={setRow} label="Hàng:" /><Sel v={col} set={setCol} label="Cột:" />
        <label>Giá trị: <select value={measure} onChange={(e) => setMeasure(e.target.value)}>
          <option value="avg_hourly">Trung bình lượt thuê / giờ</option><option value="total">Tổng lượt thuê</option></select></label>
      </div>
      {err && <p className="err">{err}</p>}
      {data && !err && (
        <div className="tablewrap"><table>
          <thead><tr><th>{DIMS[row]} \ {DIMS[col]}</th>{data.cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>{data.rows.map((r) => (
            <tr key={r}><th>{r}</th>{data.cols.map((c) => {
              const v = cell[r + '|' + c]
              const a = v === undefined || !max ? 0 : v / max
              return <td key={c} style={{ background: `rgba(37,99,235,${(a * 0.7).toFixed(2)})`, color: a > 0.55 ? '#fff' : '#111' }}>
                {v === undefined ? '—' : fmt(v, measure === 'total' ? 0 : 1)}</td>
            })}</tr>))}</tbody>
        </table></div>
      )}
    </section>
  )
}
