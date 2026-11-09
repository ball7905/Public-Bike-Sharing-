// DSS: phân loại nhu cầu (FR09) + khuyến nghị chuẩn bị xe (FR10)
// Bố cục theo luồng người dùng: chọn tình huống -> kết luận -> việc cần làm -> 24 giờ trong ngày -> chi tiết (thu gọn).
// Chọn nhiều thứ: mặc định lập kế hoạch RIÊNG cho từng thứ và đặt cạnh nhau; có thể gộp thành 1 kế hoạch trung bình.
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, get, pct } from '../api.js'

export const LEVEL_COLOR = { low: '#16a34a', medium: '#f59e0b', high: '#dc2626' }
const LEVEL_LABEL = { low: 'Thấp', medium: 'Trung bình', high: 'Cao' }
const DAY_GROUPS = [
  ['working', 'Ngày làm việc', 'Thứ 2 – thứ 6, không phải ngày lễ'],
  ['non_working', 'Ngày nghỉ', 'Cuối tuần hoặc ngày lễ'],
]
const WEATHERS = [
  [1, 'Quang đãng', 'Trời quang, ít mây'], [2, 'Sương mù', 'Nhiều mây, có sương'],
  [3, 'Mưa nhẹ', 'Mưa / tuyết nhẹ'], [4, 'Mưa lớn', 'Hiếm gặp - rất ít dữ liệu'],
]
const WEATHER_VI = Object.fromEntries(WEATHERS.map(([k, vi]) => [k, vi]))
const DAY_VI = { working: 'Ngày làm việc', non_working: 'Ngày nghỉ' }
// Thứ trong tuần theo mã nguồn (0 = Chủ nhật); hiển thị theo thứ tự T2 -> CN
const WEEKDAYS = [[1, 'T2', 'Thứ hai'], [2, 'T3', 'Thứ ba'], [3, 'T4', 'Thứ tư'], [4, 'T5', 'Thứ năm'],
  [5, 'T6', 'Thứ sáu'], [6, 'T7', 'Thứ bảy'], [0, 'CN', 'Chủ nhật']]
const WD = Object.fromEntries(WEEKDAYS.map(([k, short, name]) => [k, { short, name }]))
const LINE_COLORS = ['#2563eb', '#9333ea', '#0d9488', '#db2777', '#ea580c', '#475569', '#854d0e']
const MULTI_MODES = [
  ['each', 'Từng ngày'],
  ['merge', 'Trung bình chung'],
]
const QPRESETS = {
  '33-67': [1 / 3, 2 / 3, 'Chia đều 3 mức (P33 / P67) - mặc định'],
  '25-75': [0.25, 0.75, 'Chỉ 25% giờ đông nhất là Cao (P25 / P75)'],
}
const hh = (h) => `${String(h).padStart(2, '0')}:00`
const SEG_COLOR = { registered: '#2563eb', mixed: '#64748b', casual: '#f59e0b' }
const SEG_LABEL = { registered: 'Chủ yếu khách đăng ký', mixed: 'Khách hỗn hợp', casual: 'Nhiều khách vãng lai' }
const SegChip = ({ seg, label }) => seg ? <span className={'segchip ' + seg}>{label}</span> : null
const isWeak = (plan) => plan.hours.filter((h) => h.reliable).length < 12

const Badge = ({ level }) => level
  ? <span className="badge" style={{ background: LEVEL_COLOR[level] }}>{LEVEL_LABEL[level]}</span>
  : <span className="badge nodata">Không có dữ liệu</span>

function Segmented({ label, items, value, onChange, small }) {
  return (
    <div className="seg-group">
      {label && <span className="seg-label">{label}</span>}
      <div className={'seg' + (small ? ' small' : '')} role="radiogroup" aria-label={label}>
        {items.map(([v, text, sub]) => (
          <button type="button" key={v} role="radio" aria-checked={value === v}
            className={'seg-btn' + (value === v ? ' on' : '')} onClick={() => onChange(v)}>
            <b>{text}</b>{sub && <small>{sub}</small>}
          </button>
        ))}
      </div>
    </div>
  )
}

function periodText(filters, options) {
  const pick = (name) => (options[name] || []).filter((o) => (filters[name] || []).includes(o.value)).map((o) => o.label)
  const years = pick('year'), seasons = pick('season')
  return `${years.length ? 'Năm ' + years.join(', ') : 'Cả 2011–2012'}${seasons.length ? ' · mùa ' + seasons.join(', ') : ''}`
}

function verdictText(plan) {
  if (plan.summary.counts.no_data === 24) return 'Không có dữ liệu lịch sử - không khuyến nghị.'
  return plan.alerts.length === 0
    ? 'Không có khung giờ Cao - duy trì mức cơ bản.'
    : `${plan.alerts.length} khung cao điểm - chuẩn bị xong trước ${plan.alerts.map((a) => a.prepare_before).join(' và ')}.`
}

// ---------- các khối dùng chung cho 1 kế hoạch và chế độ so sánh ----------
function TodoList({ alerts }) {
  return (
    <ol className="todo">
      {alerts.map((a) => (
        <li key={a.label}>
          <div className="todo-time"><small>Hoàn tất trước</small><b>{a.prepare_before}</b></div>
          <div className="todo-body">
            <b>Chuẩn bị thêm xe và nhân sự cho khung {hh(a.start_hour)} – {String(a.end_hour).padStart(2, '0')}:59</b>
            <span>Đỉnh lúc {a.peak_hour}h, trung bình {fmt(a.peak_avg)} lượt/giờ.
              {a.low_reliability && ' Ít dữ liệu lịch sử - chỉ để tham khảo.'}</span>
            {a.segment && (
              <span className="todo-seg">
                <SegChip seg={a.segment} label={`${a.segment_label} · ${pct(a.casual_share)} vãng lai`} />
                {a.segment_advice}
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}

function LevelStrip({ hours, label }) {
  return (
    <div className="strip" role="list" aria-label={`Mức nhu cầu từng giờ${label ? ' - ' + label : ''}`}>
      {hours.map((h) => (
        <div role="listitem" key={h.hour} className={'strip-cell' + (h.reliable ? '' : ' weak')}
          style={{ background: h.level ? LEVEL_COLOR[h.level] : 'var(--line)' }}
          title={`${label ? label + ' · ' : ''}${hh(h.hour)} · ${h.level_label}${h.avg_rentals != null ? ` · ${fmt(h.avg_rentals)} lượt/giờ` : ''}`}>
          <span>{h.hour}</span>
        </div>
      ))}
    </div>
  )
}

function SegStrip({ hours, label }) {
  return (
    <div className="strip seg-strip" role="list" aria-label={`Nhóm khách từng giờ${label ? ' - ' + label : ''}`}>
      {hours.map((h) => (
        <div role="listitem" key={h.hour} className="strip-cell"
          style={{ background: h.segment ? SEG_COLOR[h.segment] : 'var(--line)' }}
          title={`${label ? label + ' · ' : ''}${hh(h.hour)} · ${h.segment_label || 'Không có dữ liệu'}${h.casual_share != null ? ` · ${pct(h.casual_share)} vãng lai` : ''}`}>
          <span>{h.hour}</span>
        </div>
      ))}
    </div>
  )
}

function LevelLegend({ th, minObs }) {
  return (
    <div className="legend">
      {['low', 'medium', 'high'].map((lv) => (
        <span key={lv}><i style={{ background: LEVEL_COLOR[lv] }} />{LEVEL_LABEL[lv]}
          {th && <em>{lv === 'low' ? ` < ${fmt(th.low)}` : lv === 'high' ? ` > ${fmt(th.high)}` : ` ${fmt(th.low)}–${fmt(th.high)}`} lượt/giờ</em>}</span>
      ))}
      <span><i className="weak-sw" />Ít dữ liệu (dưới {minObs} giờ quan sát)</span>
    </div>
  )
}

function LevelCards({ survey }) {
  return (
    <div className="levels">
      {survey.levels.map(({ level, recommendation }) => (
        <div className={'lvcard ' + level} key={level}>
          <div className="lvhead"><Badge level={level} />
            <span>{level === 'low' ? `dưới ${fmt(survey.thresholds.low)}` : level === 'high' ? `trên ${fmt(survey.thresholds.high)}`
              : `${fmt(survey.thresholds.low)} – ${fmt(survey.thresholds.high)}`} lượt/giờ</span></div>
          <p>{recommendation}</p>
        </div>
      ))}
    </div>
  )
}

function MixNote({ mix }) {
  return (
    <p className="note mixnote">
      Xe dùng chung cho cả hai nhóm nên <b>mức chuẩn bị</b> ở trên dựa trên tổng lượt thuê.
      Thành phần khách cho biết <b>cần hỗ trợ kiểu gì</b>: một giờ được xem là <i>nhiều khách vãng lai</i> khi tỷ lệ vãng lai
      từ {pct(mix.casual_heavy_at)} trở lên (gấp 1,5 lần mức chung {pct(mix.reference_casual_share)}),
      và <i>chủ yếu khách đăng ký</i> khi từ {pct(mix.registered_heavy_at)} trở xuống.
    </p>
  )
}

function SegCards({ mix }) {
  return (<>
    <div className="legend">
      {mix.segments.map((s) => <span key={s.segment}><i style={{ background: SEG_COLOR[s.segment] }} />{s.label}</span>)}
    </div>
    <div className="levels">
      {mix.segments.map((s) => (
        <div className="lvcard" key={s.segment} style={{ '--lc': SEG_COLOR[s.segment] }}>
          <div className="lvhead"><SegChip seg={s.segment} label={s.label} /></div>
          <p>{s.advice}</p>
        </div>
      ))}
    </div>
  </>)
}

// ---------- chế độ so sánh: một kế hoạch riêng cho mỗi thứ ----------
function CompareView({ items, survey, weather }) {
  const minObs = survey?.min_obs ?? 30
  const th = items[0].plan.thresholds
  const mix = items[0].plan.user_mix
  const chart = Array.from({ length: 24 }, (_, h) =>
    Object.fromEntries([['hour', h], ...items.map(({ dow, plan }) => [WD[dow].name, plan.hours[h].avg_rentals])]))
  return (<>
    <section className="card dss-verdict">
      <div className="dss-step"><span>2</span>Kết luận cho từng thứ (trời {WEATHER_VI[weather].toLowerCase()})</div>
      <div className="cmp-grid">
        {items.map(({ dow, plan }) => {
          const c = plan.summary.counts, pk = plan.summary.peak, m = plan.user_mix
          return (
            <div className="cmp-card" key={dow}>
              <div className="cmp-head"><b>{WD[dow].name}</b>
                {m?.scenario_segment && <SegChip seg={m.scenario_segment} label={`${SEG_LABEL[m.scenario_segment]} · ${pct(m.scenario_casual_share)}`} />}</div>
              <p className="cmp-verdict">{verdictText(plan)}</p>
              {isWeak(plan) && c.no_data < 24 && <p className="cmp-weak">Ít dữ liệu lịch sử - chỉ để tham khảo.</p>}
              <div className="cmp-stats">
                <span className="high"><b>{c.high}</b> Cao</span>
                <span className="medium"><b>{c.medium}</b> TB</span>
                <span className="low"><b>{c.low}</b> Thấp</span>
                {pk && <span className="pk">Đỉnh <b>{pk.hour}h</b> · {fmt(pk.avg_rentals)} lượt/giờ</span>}
              </div>
            </div>
          )
        })}
      </div>
    </section>

    {items.some(({ plan }) => plan.alerts.length) && (
      <section className="card">
        <div className="dss-step"><span>3</span>Việc cần làm theo từng thứ</div>
        {items.map(({ dow, plan }) => (
          <div className="cmp-todo" key={dow}>
            <h4>{WD[dow].name}</h4>
            {plan.alerts.length ? <TodoList alerts={plan.alerts} /> : <p className="note">Không có khung giờ Cao - duy trì mức chuẩn bị cơ bản.</p>}
          </div>
        ))}
      </section>
    )}

    <section className="card">
      <div className="dss-step"><span>{items.some(({ plan }) => plan.alerts.length) ? 4 : 3}</span>24 giờ - so sánh các thứ</div>
      <div className="cmp-strips">
        {items.map(({ dow, plan }) => (
          <div className="cmp-row" key={dow}><span className="cmp-label">{WD[dow].short}</span><LevelStrip hours={plan.hours} label={WD[dow].name} /></div>
        ))}
      </div>
      <LevelLegend th={th} minObs={minObs} />
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chart} margin={{ top: 10 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="hour" tickFormatter={(h) => `${h}h`} />
          <YAxis width={56} tickFormatter={(v) => fmt(v)} />
          <Tooltip labelFormatter={(h) => hh(h)} formatter={(v, n) => [v == null ? 'Không có dữ liệu' : `${fmt(v, 1)} lượt/giờ`, n]} />
          <Legend />
          <ReferenceLine y={th.low} stroke={LEVEL_COLOR.low} strokeDasharray="4 4" />
          <ReferenceLine y={th.high} stroke={LEVEL_COLOR.high} strokeDasharray="4 4" />
          {items.map(({ dow }, i) => (
            <Line key={dow} type="monotone" dataKey={WD[dow].name} stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2.5} dot={false} connectNulls={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="note">Mỗi đường = lượt thuê trung bình theo giờ của các ngày cùng thứ trong quá khứ. Đường nét đứt = hai ngưỡng.</p>
      {survey && <LevelCards survey={survey} />}
    </section>

    {mix?.reference_casual_share != null && (
      <section className="card">
        <div className="dss-step"><span>{items.some(({ plan }) => plan.alerts.length) ? 5 : 4}</span>Nhóm khách cần phục vụ - so sánh các thứ</div>
        <MixNote mix={mix} />
        <div className="cmp-strips">
          {items.map(({ dow, plan }) => (
            <div className="cmp-row" key={dow}><span className="cmp-label">{WD[dow].short}</span><SegStrip hours={plan.hours} label={WD[dow].name} /></div>
          ))}
        </div>
        <SegCards mix={mix} />
      </section>
    )}
  </>)
}

export default function DssPanel({ filters, options = {} }) {
  const period = { year: filters.year, season: filters.season }
  const [dayGroup, setDayGroup] = useState('working')
  const [dows, setDows] = useState([])           // [] = dùng nhóm ngày; [0..6] = một hoặc nhiều thứ cụ thể
  const [multiMode, setMultiMode] = useState('each')
  const toggleDow = (k) => setDows((cur) => cur.includes(k) ? cur.filter((x) => x !== k) : [...cur, k])
  const ordered = WEEKDAYS.map(([k]) => k).filter((k) => dows.includes(k))   // theo thứ tự T2 -> CN
  const dowNames = ordered.map((k) => WD[k].name)
  const compare = ordered.length >= 2 && multiMode === 'each'
  const [weather, setWeather] = useState(1)
  const [preset, setPreset] = useState('33-67')
  const [survey, setSurvey] = useState(null)
  const [plan, setPlan] = useState(null)
  const [cmp, setCmp] = useState(null)           // [{dow, plan}] ở chế độ so sánh
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
    const base = { ...period, q_low, q_high, day_group: dayGroup, weather }
    if (compare) {
      setCmp(null)
      Promise.all(ordered.map((d) => get('dss/plan', { ...base, day_of_week: d }).then((p) => ({ dow: d, plan: p }))))
        .then(setCmp).catch((e) => setErr(e.message))
    } else {
      get('dss/plan', { ...base, day_of_week: ordered.length ? ordered : undefined }).then(setPlan).catch((e) => setErr(e.message))
    }
  }, [key, dayGroup, ordered.join(','), weather, compare]) // eslint-disable-line

  const th = plan?.thresholds
  const counts = plan?.summary?.counts
  const peak = plan?.summary?.peak
  const scenario = `${ordered.length ? dowNames.join(' + ') : DAY_VI[dayGroup]}, trời ${WEATHER_VI[weather].toLowerCase()}`
  const noData = counts && counts.no_data === 24
  const weak = plan && isWeak(plan)        // phần lớn các giờ thiếu dữ liệu / ít mẫu -> không kết luận chắc chắn
  const mix = plan?.user_mix
  const minObs = survey?.min_obs ?? 30
  let step = 2                                   // đánh số các bước hiển thị
  const next = () => ++step

  return (
    <div className="dss">
      {/* 1. Chọn tình huống */}
      <section className="card dss-scenario">
        <div className="dss-step"><span>1</span>Chọn tình huống sắp tới</div>
        <div className="seg-row">
          <div className="seg-group">
            <Segmented label="Loại ngày" items={DAY_GROUPS} value={ordered.length ? null : dayGroup}
              onChange={(v) => { setDayGroup(v); setDows([]) }} />
            <div className="dow" role="group" aria-label="Hoặc chọn một hoặc nhiều thứ cụ thể">
              <span className="dow-label">hoặc chọn thứ (được chọn nhiều):</span>
              {WEEKDAYS.map(([k, short, name]) => (
                <button type="button" key={k} aria-pressed={dows.includes(k)} title={name} aria-label={name}
                  className={'dow-btn' + (dows.includes(k) ? ' on' : '') + (k === 0 || k === 6 ? ' wk' : '')}
                  onClick={() => toggleDow(k)}>{short}</button>
              ))}
              {dows.length > 0 && <button type="button" className="dow-clear" onClick={() => setDows([])}>Bỏ chọn</button>}
            </div>
            {ordered.length >= 2 && (
              <Segmented small items={MULTI_MODES} value={multiMode} onChange={setMultiMode} />
            )}
          </div>
          <Segmented label="Thời tiết dự báo" items={WEATHERS} value={weather} onChange={setWeather} />
        </div>
        <p className="note">
          Dựa trên dữ liệu lịch sử: <b>{periodText(filters, options)}</b> (đổi bằng bộ lọc Năm / Mùa ở trên).
          {ordered.length > 0 && <> Đang dùng các ngày <b>{dowNames.join(', ')}</b>
            {/* ngày lễ trong dữ liệu chỉ rơi vào thứ 2 - thứ 6, nên chỉ nhắc khi có chọn ngày trong tuần */}
            {ordered.some((d) => d >= 1 && d <= 5) && ' (bỏ các ngày lễ rơi vào thứ 2 – thứ 6; ngày lễ được tính vào nhóm Ngày nghỉ)'}
            {compare ? '; mỗi thứ được lập kế hoạch riêng.' : ordered.length >= 2 ? '; các thứ được gộp và lấy trung bình chung.' : ';'}
            {' '}Mỗi thứ có ít dữ liệu hơn cả nhóm nên một số giờ có thể bị gắn cờ ít dữ liệu.</>}
          {' '}Hệ thống khuyến nghị <b>mức độ</b> chuẩn bị, không tính số xe cụ thể vì dữ liệu không có số xe sẵn có hay vị trí trạm.
        </p>
        {err && <p className="err">{err}</p>}
      </section>

      {compare && cmp && <CompareView items={cmp} survey={survey} weather={weather} />}

      {!compare && plan && (<>
        {/* 2. Kết luận nhanh */}
        <section className="card dss-verdict">
          <div className="dss-step"><span>2</span>Kết luận cho: {scenario}</div>
          {noData ? (
            <p className="verdict-text">Không có dữ liệu lịch sử cho tình huống này (thời tiết này gần như chưa từng xảy ra), nên hệ thống không đưa ra khuyến nghị.</p>
          ) : (<>
            {weak && (
              <div className="caution">
                <b>Không đủ dữ liệu để kết luận chắc chắn.</b> Tình huống này hiếm gặp trong lịch sử
                ({counts.no_data} giờ không có dữ liệu, các giờ còn lại có dưới {minObs} lần quan sát).
                Kết quả bên dưới chỉ để tham khảo.
              </div>
            )}
            {ordered.length >= 2 && plan.scenario?.day_group === null && (
              <div className="caution">
                <b>Đang gộp ngày trong tuần với cuối tuần.</b> Hai loại ngày có dạng nhu cầu khác nhau nên trung bình chung
                có thể không đúng cho từng ngày - nên chọn <i>Từng ngày</i>.
              </div>
            )}
            <p className="verdict-text">
              {plan.alerts.length === 0
                ? <>Không có khung giờ nhu cầu <b className="t-high">Cao</b>. Duy trì mức chuẩn bị cơ bản và theo dõi.</>
                : <>Có <b className="t-high">{plan.alerts.length} khung giờ cao điểm</b>. Cần chuẩn bị xong trước{' '}
                    <b>{plan.alerts.map((a) => a.prepare_before).join(' và ')}</b>.</>}
            </p>
            <div className="verdict-stats">
              {['high', 'medium', 'low'].map((lv) => (
                <div className={'vstat ' + lv} key={lv}>
                  <span className="vnum">{counts[lv]}</span><span className="vlab">giờ mức {LEVEL_LABEL[lv]}</span>
                </div>
              ))}
              {counts.no_data > 0 && (
                <div className="vstat nodata"><span className="vnum">{counts.no_data}</span><span className="vlab">giờ không có dữ liệu</span></div>
              )}
              {peak && (
                <div className="vstat peak">
                  <span className="vnum">{peak.hour}h</span>
                  <span className="vlab">giờ đông nhất · {fmt(peak.avg_rentals)} lượt/giờ (gấp {peak.ratio_to_mean.toFixed(1)} lần TB)</span>
                </div>
              )}
            </div>
            {mix?.scenario_segment && (
              <p className="verdict-mix">
                <SegChip seg={mix.scenario_segment} label={SEG_LABEL[mix.scenario_segment]} />
                Khách vãng lai chiếm <b>{pct(mix.scenario_casual_share)}</b> lượt thuê trong tình huống này
                (mức chung của kỳ: {pct(mix.reference_casual_share)}).
              </p>
            )}
          </>)}
        </section>

        {/* 3. Việc cần làm */}
        {plan.alerts.length > 0 && (
          <section className="card">
            <div className="dss-step"><span>{next()}</span>Việc cần làm</div>
            <TodoList alerts={plan.alerts} />
          </section>
        )}

        {/* 4. Một ngày nhìn nhanh */}
        <section className="card">
          <div className="dss-step"><span>{next()}</span>24 giờ trong ngày</div>
          <LevelStrip hours={plan.hours} />
          <LevelLegend th={th} minObs={minObs} />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={plan.hours} margin={{ top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="hour" tickFormatter={(h) => `${h}h`} />
              <YAxis width={56} tickFormatter={(v) => fmt(v)} />
              <Tooltip formatter={(v, n, p) => [`${fmt(v, 1)} lượt/giờ (${fmt(p.payload.n_obs)} giờ quan sát)`, p.payload.level_label]}
                labelFormatter={(h) => hh(h)} />
              <ReferenceLine y={th.low} stroke={LEVEL_COLOR.low} strokeDasharray="4 4" />
              <ReferenceLine y={th.high} stroke={LEVEL_COLOR.high} strokeDasharray="4 4" />
              <Bar dataKey="avg_rentals" radius={[4, 4, 0, 0]}>
                {plan.hours.map((h) => <Cell key={h.hour} fill={LEVEL_COLOR[h.level] || '#9ca3af'} fillOpacity={h.reliable ? 1 : 0.45} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="note">Cột = số lượt thuê trung bình của giờ đó trong các ngày tương tự ở quá khứ. Đường nét đứt = hai ngưỡng.</p>
          {survey && <LevelCards survey={survey} />}
        </section>

        {/* Nhóm khách: mức chuẩn bị dựa trên tổng lượt (xe dùng chung), thành phần khách quyết định loại hỗ trợ */}
        {mix?.reference_casual_share != null && !noData && (
          <section className="card">
            <div className="dss-step"><span>{next()}</span>Nhóm khách cần phục vụ</div>
            <MixNote mix={mix} />
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={plan.hours} margin={{ top: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="hour" tickFormatter={(h) => `${h}h`} />
                <YAxis width={56} tickFormatter={(v) => fmt(v)} />
                <Tooltip labelFormatter={(h) => hh(h)} formatter={(v, n) => [`${fmt(v, 1)} lượt/giờ`, n]} />
                <Bar dataKey="avg_registered" name="Khách đăng ký" stackId="u" fill={SEG_COLOR.registered} />
                <Bar dataKey="avg_casual" name="Khách vãng lai" stackId="u" fill={SEG_COLOR.casual} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <SegStrip hours={plan.hours} />
            <SegCards mix={mix} />
          </section>
        )}
      </>)}

      {/* Chi tiết cho người phân tích (thu gọn) */}
      <section className="card dss-more">
        <h3>Chi tiết và cách hệ thống tính</h3>

        {compare && cmp && (
          <details>
            <summary>Bảng so sánh từng giờ giữa các thứ</summary>
            <div className="tablewrap"><table>
              <thead><tr><th>Giờ</th>{cmp.map(({ dow }) => <th key={dow} colSpan={2}>{WD[dow].name}</th>)}</tr></thead>
              <tbody>{Array.from({ length: 24 }, (_, h) => (
                <tr key={h}><th>{hh(h)}</th>{cmp.map(({ dow, plan: p }) => {
                  const x = p.hours[h]
                  return [<td key={dow + 'v'}>{fmt(x.avg_rentals, 1)}{x.n_obs > 0 && !x.reliable && ' *'}</td>,
                    <td key={dow + 'l'}><Badge level={x.level} /></td>]
                })}</tr>))}
              </tbody>
            </table></div>
            <p className="note">Số = lượt thuê trung bình / giờ; * = dưới {minObs} giờ quan sát.</p>
          </details>
        )}

        {!compare && plan && (
          <details>
            <summary>Bảng chi tiết từng giờ</summary>
            <div className="tablewrap"><table>
              <thead><tr><th>Giờ</th><th>TB lượt / giờ</th><th>So với TB kỳ</th><th>Số giờ quan sát</th><th>% vãng lai</th><th>Nhóm khách</th><th>Mức</th><th>Khuyến nghị</th></tr></thead>
              <tbody>{plan.hours.map((h) => (
                <tr key={h.hour} className={h.level === 'high' ? 'hi' : ''}>
                  <th>{h.label}</th><td>{fmt(h.avg_rentals, 1)}</td>
                  <td>{h.ratio_to_mean == null ? '—' : `×${h.ratio_to_mean.toFixed(2)}`}</td>
                  <td>{fmt(h.n_obs)}{h.n_obs > 0 && !h.reliable && ' *'}</td>
                  <td>{pct(h.casual_share)}</td><td className="left">{h.segment_label || '—'}</td>
                  <td><Badge level={h.level} /></td><td className="left">{h.recommendation}</td></tr>))}
              </tbody>
            </table></div>
          </details>
        )}

        {survey && (
          <details>
            <summary>Ngưỡng được xác định thế nào?</summary>
            <p className="explain">
              Hệ thống sắp xếp toàn bộ <b>{fmt(survey.distribution.n_obs)}</b> giờ trong kỳ lịch sử theo số lượt thuê và lấy các phân vị.
              Ngưỡng thấp = <b>{fmt(survey.thresholds.low)}</b>, ngưỡng cao = <b>{fmt(survey.thresholds.high)}</b> lượt/giờ.
              Mỗi giờ của tình huống được xếp mức bằng cách so <i>trung bình các giờ tương tự trong quá khứ</i> (cùng giờ, loại ngày, thời tiết) với hai ngưỡng.
            </p>
            <div className="tablewrap"><table>
              <thead><tr>{survey.distribution.percentiles.map((p) => <th key={p.q}>P{(p.q * 100).toFixed(0)}</th>)}<th>TB</th></tr></thead>
              <tbody><tr>{survey.distribution.percentiles.map((p) => <td key={p.q}>{fmt(p.value)}</td>)}<td>{fmt(survey.distribution.mean, 1)}</td></tr></tbody>
            </table></div>
            <p className="note">Tỷ lệ giờ lịch sử ở mỗi mức: Thấp {pct(survey.observation_share.low)} · Trung bình {pct(survey.observation_share.medium)} · Cao {pct(survey.observation_share.high)}.</p>
            <label className="preset">Cách chia ngưỡng (phân tích độ nhạy):{' '}
              <select value={preset} onChange={(e) => setPreset(e.target.value)}>
                {Object.entries(QPRESETS).map(([k, v]) => <option key={k} value={k}>{v[2]}</option>)}
              </select>
            </label>
          </details>
        )}

        {matrix && (
          <details>
            <summary>So sánh mọi tình huống (ma trận giờ × loại ngày × thời tiết)</summary>
            <div className="tablewrap"><table className="matrix">
              <thead><tr><th>Giờ</th>{matrix.cols.map((c) => <th key={c.label}>{DAY_VI[c.day_group]}<br /><small>{WEATHER_VI[c.weather]}</small></th>)}</tr></thead>
              <tbody>{Array.from({ length: 24 }, (_, h) => (
                <tr key={h}><th>{String(h).padStart(2, '0')}h</th>{matrix.cols.map((c) => {
                  const x = matrix.cells.find((e) => e.hour === h && e.day_group === c.day_group && e.weather === c.weather)
                  return <td key={c.label} title={x?.level ? `${fmt(x.avg_rentals, 1)} lượt/giờ, ${x.n_obs} giờ quan sát` : 'Không có dữ liệu'}
                    style={{ background: x?.level ? LEVEL_COLOR[x.level] : 'transparent', opacity: x?.reliable ? 1 : 0.45, color: x?.level ? '#fff' : 'inherit' }}>
                    {x?.level ? fmt(x.avg_rentals) : '—'}</td>
                })}</tr>))}
              </tbody>
            </table></div>
            <p className="note">Ô nhạt: dưới {minObs} giờ quan sát. "Mưa lớn" gần như không có dữ liệu lịch sử.</p>
          </details>
        )}
      </section>
    </div>
  )
}
