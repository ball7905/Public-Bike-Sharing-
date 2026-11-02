import { fmt, pct } from '../api.js'

export default function KpiCards({ k }) {
  if (!k) return null
  const items = [
    ['Total Rentals', fmt(k.total_rentals), 'Tổng lượt thuê'],
    ['Average Hourly Rentals', fmt(k.avg_hourly_rentals, 1), 'Trung bình / giờ'],
    ['Peak Hour', k.peak_hour ? `${k.peak_hour.hour}h` : '—', k.peak_hour ? `TB ${fmt(k.peak_hour.avg_rentals, 0)} lượt/giờ` : ''],
    ['Lowest Demand Hour', k.lowest_hour ? `${k.lowest_hour.hour}h` : '—', k.lowest_hour ? `TB ${fmt(k.lowest_hour.avg_rentals, 1)} lượt/giờ` : ''],
    ['Registered User Ratio', pct(k.registered_ratio), 'Người dùng đăng ký'],
    ['Casual User Ratio', pct(k.casual_ratio), 'Người dùng vãng lai'],
    ['Working Day Demand', fmt(k.working_day_avg_daily), 'TB lượt thuê / ngày làm việc'],
    ['Non-working Day Demand', fmt(k.non_working_day_avg_daily), 'TB lượt thuê / ngày nghỉ'],
  ]
  return (
    <section className="kpis">
      {items.map(([title, val, sub]) => (
        <div className="card kpi" key={title}>
          <div className="kt">{title}</div>
          <div className="kv">{val}</div>
          <div className="ks">{sub}</div>
        </div>
      ))}
    </section>
  )
}
