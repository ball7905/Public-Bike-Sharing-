// Bộ lọc đa chọn (Slice/Dice): bấm chip để bật/tắt giá trị
const GROUPS = [
  ['year', 'Năm'], ['season', 'Mùa'], ['weather', 'Thời tiết'], ['day_type', 'Loại ngày'], ['time_band', 'Khung giờ'],
]

export default function FilterBar({ options, value, onChange }) {
  const toggle = (name, v) => {
    const cur = value[name] || []
    const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]
    onChange({ ...value, [name]: next })
  }
  const active = Object.values(value).some((a) => a.length)
  return (
    <section className="card filters">
      {GROUPS.map(([name, label]) => (
        <div className="fgroup" key={name}>
          <span className="flabel">{label}</span>
          {(options[name] || []).map((o) => (
            <button key={o.value} className={'chip' + ((value[name] || []).includes(o.value) ? ' on' : '')}
              onClick={() => toggle(name, o.value)}>{o.label}</button>
          ))}
        </div>
      ))}
      <button className="reset" disabled={!active} onClick={() => onChange({})}>Xóa bộ lọc</button>
    </section>
  )
}
