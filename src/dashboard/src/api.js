// Gọi API; bỏ qua tham số rỗng, mảng nối bằng dấu phẩy
export async function get(path, params = {}) {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '' || (Array.isArray(v) && v.length === 0)) continue
    u.set(k, Array.isArray(v) ? v.join(',') : v)
  }
  const qs = u.toString()
  const res = await fetch(`/api/${path}${qs ? '?' + qs : ''}`)
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`)
  return res.json()
}

export const fmt = (n, d = 0) =>
  n === null || n === undefined ? '—' : Number(n).toLocaleString('vi-VN', { maximumFractionDigits: d, minimumFractionDigits: d })
export const pct = (x) => (x === null || x === undefined ? '—' : (x * 100).toFixed(1) + '%')
