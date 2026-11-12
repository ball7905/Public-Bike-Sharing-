// Kiểm định ngoài mẫu (backtest) của mô hình DSS: huấn luyện trên 2011, kiểm tra trên 2012
import { useEffect, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, get, pct } from '../api.js'
import { LEVEL_COLOR, LEVEL_LABEL } from './DssPanel.jsx'

const LEVELS = ['low', 'medium', 'high']

export default function BacktestPanel() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const [selId, setSelId] = useState('full_static')

  useEffect(() => { get('dss/backtest').then(setData).catch((e) => setErr(e.message)) }, [])

  if (err) return <section className="card dss"><p className="err">Không tải được kết quả kiểm định ({err}).</p></section>
  if (!data) return <section className="card dss"><p className="note">Đang tính kết quả kiểm định…</p></section>

  const exp = data.experiments.find((e) => e.id === selId) || data.experiments[0]
  const m = exp.metrics
  const adjusted = exp.scheme === 'expanding_adjusted'
  const share = (actual, predicted) => {
    const row = m.confusion[actual]
    const total = LEVELS.reduce((s, p) => s + (row[p] || 0), 0)
    return total ? (row[predicted] || 0) / total : 0
  }

  return (
    <section className="card dss">
      <h3>Kiểm định ngoài mẫu (backtest): huấn luyện 2011, kiểm tra 2012</h3>
      <p className="note">
        Với từng giờ của năm {data.test_year}, mô hình chỉ dùng dữ liệu xuất hiện <b>trước</b> đó để dự báo mức nhu cầu.
        Mức thực tế là lượt thuê thực tế được phân loại bằng <b>cùng ngưỡng</b> P{(data.q_low * 100).toFixed(0)} / P{(data.q_high * 100).toFixed(0)}.
        Kiểm tra {fmt(data.n_test)} giờ; huấn luyện tĩnh dùng {fmt(data.n_train_static)} giờ.
      </p>

      <div className="tablewrap"><table>
        <thead><tr>
          <th>Cách huấn luyện</th><th>Độ chính xác</th><th>F1 trung bình</th><th>Recall mức Cao</th>
          <th>Thiếu chuẩn bị</th><th>Dư chuẩn bị</th><th>MAE (lượt/giờ)</th>
        </tr></thead>
        <tbody>{data.experiments.map((e) => (
          <tr key={e.id} className={`pick${e.id === exp.id ? ' sel' : ''}`} onClick={() => setSelId(e.id)}
              aria-selected={e.id === exp.id}>
            <th className="left">{e.label}</th>
            <td>{pct(e.metrics.accuracy)}</td>
            <td>{fmt(e.metrics.macro_f1, 3)}</td>
            <td>{pct(e.metrics.per_level.high.recall)}</td>
            <td>{pct(e.metrics.under_prepared_rate)}</td>
            <td>{pct(e.metrics.over_prepared_rate)}</td>
            <td>{fmt(e.metrics.mae, 1)}</td>
          </tr>))}
        </tbody>
      </table></div>
      <p className="note">Nhấn vào một dòng để xem chi tiết. "Thiếu chuẩn bị": mức thực tế cao hơn mức dự báo. "Dư chuẩn bị": mức dự báo cao hơn mức thực tế.</p>

      <div className="dssgrid">
        <div className="sub">
          <h4>Ma trận nhầm lẫn: {exp.label}</h4>
          <div className="tablewrap"><table className="matrix">
            <thead><tr><th>Thực tế \ Dự báo</th>{LEVELS.map((p) => <th key={p}>{LEVEL_LABEL[p]}</th>)}</tr></thead>
            <tbody>{LEVELS.map((a) => (
              <tr key={a}><th><span className="badge" style={{ background: LEVEL_COLOR[a] }}>{LEVEL_LABEL[a]}</span></th>
                {LEVELS.map((p) => (
                  <td key={p} style={{ background: `rgba(37, 99, 235, ${share(a, p) * 0.9})`,
                                       color: share(a, p) > 0.5 ? '#fff' : 'inherit' }}
                      title={`${fmt(m.confusion[a][p])} giờ (${pct(share(a, p))} số giờ thực tế mức này)`}>
                    {fmt(m.confusion[a][p])}<br /><small>{pct(share(a, p))}</small>
                  </td>))}
              </tr>))}
            </tbody>
          </table></div>
          <p className="note">Ô tô đậm: tỷ lệ cao trong từng hàng (mức thực tế). Đường chéo là dự báo đúng.</p>
        </div>

        <div className="sub">
          <h4>Độ chính xác theo tháng ({data.test_year})</h4>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={exp.monthly}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tickFormatter={(x) => `T${x}`} />
              <YAxis yAxisId="left" domain={[0, 1]} width={56} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              {adjusted && <YAxis yAxisId="right" orientation="right" domain={[0.5, 2]} width={48} tickFormatter={(v) => fmt(v, 2)} />}
              <Tooltip formatter={(v, n) => (n === 'Hệ số điều chỉnh' ? fmt(v, 2) : pct(v))}
                labelFormatter={(x) => `Tháng ${x}`} />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="accuracy" name="Độ chính xác" stroke="#2563eb" strokeWidth={2} />
              <Line yAxisId="left" type="monotone" dataKey="high_recall" name="Recall mức Cao" stroke="#dc2626" strokeWidth={2} connectNulls />
              {adjusted && <Line yAxisId="right" type="monotone" dataKey="factor" name="Hệ số điều chỉnh" stroke="#6b7280" strokeDasharray="4 4" />}
            </LineChart>
          </ResponsiveContainer>
          <p className="note">Recall mức Cao bỏ trống ở tháng không có giờ thực tế thuộc mức Cao.{adjusted && ' Hệ số điều chỉnh (trục phải) = tổng thực tế / tổng dự báo trong 30 ngày trước tháng.'}</p>
        </div>
      </div>
    </section>
  )
}
