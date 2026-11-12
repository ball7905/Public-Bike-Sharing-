// Kiểu hiển thị chung khi di chuột vào biểu đồ (theo màu nền sáng/tối qua biến CSS)
const tooltipBase = {
  contentStyle: {
    background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8,
    boxShadow: '0 6px 20px rgba(0,0,0,.35)', padding: '8px 12px',
  },
  labelStyle: { color: 'var(--text)', fontWeight: 700, marginBottom: 4 },
  itemStyle: { padding: '2px 0', fontWeight: 600 },
  wrapperStyle: { outline: 'none', zIndex: 10 },
  animationDuration: 150,
}

// Biểu đồ cột: cột đang trỏ được tô nền mờ thay vì khối xám đặc
export const barTooltip = { ...tooltipBase, cursor: { fill: 'var(--text)', fillOpacity: 0.08 } }

// Biểu đồ đường: đường dọc nét đứt chỉ vị trí đang trỏ
export const lineTooltip = { ...tooltipBase, cursor: { stroke: 'var(--muted)', strokeWidth: 1, strokeDasharray: '4 4' } }

// Cột đang trỏ: sáng hơn + viền để nổi bật
export const activeBar = { fillOpacity: 1, stroke: 'var(--text)', strokeWidth: 1.5 }
export const barProps = { fillOpacity: 0.85, activeBar }

// Điểm đang trỏ trên đường: chấm lớn có viền
export const activeDot = { r: 6, strokeWidth: 2, stroke: 'var(--card)' }
