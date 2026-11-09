import { useEffect, useRef, useState } from 'react'

// Bộ lọc đa chọn (Slice/Dice) dạng select dropdown. Không chọn gì = tất cả.
export const FILTER_GROUPS = [
  ['year', 'Năm'], ['season', 'Mùa'], ['weather', 'Thời tiết'], ['day_type', 'Loại ngày'], ['time_band', 'Khung giờ'],
]

function MultiSelect({ label, options, selected, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])

  const toggle = (v) => onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v])
  const names = options.filter((o) => selected.includes(o.value)).map((o) => o.label)
  const summary = names.length === 0 ? 'Tất cả' : names.length <= 2 ? names.join(', ') : `${names.length} mục đã chọn`

  return (
    <div className={'ms' + (open ? ' open' : '') + (names.length ? ' active' : '')} ref={ref}>
      <button type="button" className="ms-btn" aria-haspopup="true" aria-expanded={open} aria-label={`${label}: ${summary}`} onClick={() => setOpen(!open)}>
        <span className="ms-label">{label}</span>
        <span className="ms-value">{summary}</span>
        <svg className="ms-caret" viewBox="0 0 20 20" aria-hidden="true"><path d="M5.5 7.5 10 12l4.5-4.5" /></svg>
      </button>
      {open && (
        <div className="ms-menu" role="group" aria-label={label}>
          <button type="button" className={'ms-opt all' + (names.length === 0 ? ' on' : '')} onClick={() => onChange([])}>
            <span className="ms-check" aria-hidden="true" />Tất cả
          </button>
          {options.map((o) => (
            <label key={o.value} className={'ms-opt' + (selected.includes(o.value) ? ' on' : '')}>
              <input type="checkbox" checked={selected.includes(o.value)} onChange={() => toggle(o.value)} />
              <span className="ms-check" aria-hidden="true" />{o.label}
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

export default function FilterBar({ options, value, onChange, fields }) {
  const groups = FILTER_GROUPS.filter(([name]) => !fields || fields.includes(name))
  const set = (name, vals) => onChange({ ...value, [name]: vals })
  const pills = groups.flatMap(([name, label]) =>
    (options[name] || []).filter((o) => (value[name] || []).includes(o.value)).map((o) => ({ name, label, o })))

  return (
    <section className="filterbar" aria-label="Bộ lọc">
      <div className="fb-row">
        <span className="fb-title">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M6 10h8M8.5 15h3" /></svg>Bộ lọc
        </span>
        {groups.map(([name, label]) => (
          <MultiSelect key={name} label={label} options={options[name] || []}
            selected={value[name] || []} onChange={(v) => set(name, v)} />
        ))}
        {pills.length > 0 && <button type="button" className="fb-reset" onClick={() => onChange({})}>Xóa tất cả</button>}
      </div>
      {pills.length > 0 && (
        <div className="fb-pills">
          {pills.map(({ name, label, o }) => (
            <span className="pill" key={name + o.value}>
              {label}: <b>{o.label}</b>
              <button type="button" aria-label={`Bỏ ${label} ${o.label}`}
                onClick={() => set(name, (value[name] || []).filter((x) => x !== o.value))}>×</button>
            </span>
          ))}
        </div>
      )}
    </section>
  )
}
