# Bike Sharing DW & DSS (CO4031 - HK261)

Cấu trúc: `sql/` (schema, view, truy vấn OLAP) · `src/etl/` (ETL Python) · `src/api/` (FastAPI) ·
`src/dashboard/` (React) · `tests/` · `data/` · `docs/`

## 1. Cài đặt (PowerShell)
```powershell
pip install -r requirements.txt
Copy-Item .env.example .env        # mở .env, điền PGPASSWORD (và PGHOST/PGPORT/PGUSER nếu khác mặc định)
# Tạo database bike_dw trong pgAdmin (một lần)
```

## 2. Nạp kho dữ liệu (ETL)
```powershell
python src/etl/run_etl.py          # tạo schema dw, ETL, đối chiếu -> docs/validation_report.md
```
Script idempotent: mỗi lần chạy xóa và tạo lại schema `dw`.

## 3. Chạy API + Dashboard (mở 2 cửa sổ terminal)
```powershell
# Terminal 1 - API (cổng 8000), chạy từ thư mục gốc repo
python -m uvicorn --app-dir src api.main:app --port 8000

# Terminal 2 - Dashboard (cổng 5173)
cd src/dashboard
npm install                         # chỉ lần đầu
npm run dev                         # mở http://localhost:5173
```
Tài liệu API tự sinh: http://localhost:8000/docs

## 4. Kiểm thử
```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q           # cần DB đã nạp ETL
```

## Mô hình dữ liệu (schema `dw`, Star Schema)
- `fact_rentals` — grain: 1 giờ. Measures: `casual_cnt`, `registered_cnt`, `total_cnt`, `temp_c`, `humidity_pct`, `windspeed_kmh` (+ `*_norm`).
- `dim_date` (731 ngày), `dim_hour` (24 giờ, `time_band`), `dim_weather` (4 mức).
- `v_rentals_flat` — view đã join sẵn, dùng cho OLAP/API.

## OLAP & KPI (FR05-FR08)
- `sql/03_olap_queries.sql`: Roll-up (`ROLLUP`), Drill-down, Slice, Dice, Pivot, 8 KPI.
- API: `/api/kpis`, `/api/olap/drill`, `/api/olap/pivot`, `/api/hourly`, `/api/weather`, `/api/day-type`, `/api/users`, `/api/filters`.
- Bộ lọc dùng chung cho mọi endpoint: `year, season, month, weekday, weather, day_type, time_band` (nhiều giá trị cách nhau bởi dấu phẩy).
- Định nghĩa KPI: *Peak/Lowest Hour* = giờ trong ngày có trung bình lượt thuê/giờ cao/thấp nhất;
  *Working/Non-working Day Demand* = trung bình lượt thuê **mỗi ngày**; các tỷ lệ tính trên tổng lượt thuê.

## Lưu ý khi phân tích
- `weekday`: 0 = Chủ nhật (theo nguồn UCI). `season` theo nguồn nên một tháng có thể thuộc 2 mùa.
- Nguồn thiếu 165 giờ (không có bản ghi); trung bình theo giờ chỉ tính trên các giờ có bản ghi.
- Mức thời tiết "Heavy rain/snow" chỉ có 3 giờ quan sát, kết quả không đủ tin cậy.
