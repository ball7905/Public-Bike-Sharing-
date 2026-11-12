# Bike Sharing DW & DSS (CO4031 - HK261)

Cấu trúc: `sql/` (schema, view, truy vấn OLAP) · `src/etl/` (ETL Python) · `src/api/` (FastAPI) ·
`src/dss/` (mô hình DSS) · `src/dashboard/` (React) · `tests/` · `data/` · `docs/`

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
- API: `/api/kpis`, `/api/olap/drill`, `/api/olap/pivot`, `/api/hourly`, `/api/weather`, `/api/day-type`, `/api/users`, `/api/filters` (DSS: xem mục dưới).
- Bộ lọc dùng chung cho mọi endpoint: `year, season, month, weekday, weather, day_type, time_band` (nhiều giá trị cách nhau bởi dấu phẩy).
- Định nghĩa KPI: *Peak/Lowest Hour* = giờ trong ngày có trung bình lượt thuê/giờ cao/thấp nhất;
  *Working/Non-working Day Demand* = trung bình lượt thuê **mỗi ngày**; các tỷ lệ tính trên tổng lượt thuê.
- Nhiệt độ / độ ẩm (FR06, Nhóm 2): `/api/climate?by=temp|humidity` trả về lượt thuê TB / giờ theo khoảng
  (nhiệt độ 5°C, gộp ≥35°C; độ ẩm 10%) và hệ số tương quan Pearson ở **mức giờ** và **mức ngày**.
  Toàn bộ dữ liệu: nhiệt độ r = 0,41 (giờ) / 0,63 (ngày); độ ẩm r = −0,32 (giờ) / −0,10 (ngày):
  phần lớn tương quan âm của độ ẩm theo giờ đến từ giờ trong ngày (đêm ẩm và vắng khách).
  Khoảng có < 30 giờ quan sát bị gắn cờ; 22 giờ có độ ẩm = 0 (ngày 10/03/2011) nhiều khả năng là lỗi đo.

## DSS: phân loại nhu cầu & khuyến nghị (FR09-FR10)
- Mô hình: `src/dss/engine.py` (thuần Python, không cần DB). Truy xuất kho: `src/api/dss_queries.py`. SQL minh họa: `sql/04_dss_queries.sql`.
- Quy trình: (1) chọn kỳ lịch sử bằng bộ lọc `year`/`season`/`month` → (2) truy xuất từ kho → (3) TB lượt thuê theo
  **giờ × loại ngày (làm việc/nghỉ) × thời tiết** → (4) phân loại → (5) khuyến nghị và cảnh báo.
- Ngưỡng: phân vị **P33,3 / P66,7** của lượt thuê theo giờ trong kỳ lịch sử (toàn bộ dữ liệu: 70 / 225 lượt/giờ, mỗi mức ≈ 1/3 số giờ).
  `Thấp` < ngưỡng thấp ≤ `Trung bình` ≤ ngưỡng cao < `Cao`. Có thể đổi bằng `q_low`, `q_high` (vd. 0.25 / 0.75) để phân tích độ nhạy.
- Nhóm có < 30 giờ quan sát bị gắn cờ độ tin cậy thấp; nhóm không có dữ liệu thì không khuyến nghị.
- Các giờ Cao liên tiếp được gộp thành khung cảnh báo, kèm giờ cần chuẩn bị xong (1 giờ trước khung).
- Chỉ khuyến nghị **mức độ** chuẩn bị, không tính số xe cụ thể (nguồn không có số xe sẵn sàng / vị trí trạm).
- API: `/api/dss/thresholds` (khảo sát phân phối + ngưỡng), `/api/dss/plan?day_group=working|non_working&weather=1..4`
  (kế hoạch 24 giờ cho tình huống sắp tới), `/api/dss/matrix` (toàn bộ ma trận phân loại).
- Kiểm định ngoài mẫu: `src/dss/backtest.py` (thuần Python, không cần DB), API `/api/dss/backtest`, panel `BacktestPanel` trên trang DSS.
  Huấn luyện 2011, kiểm thử 2012 (8.734 giờ) cho 3 mô hình × 3 lược đồ (DSS; DSS + nhiệt độ theo khoảng 10°C; chỉ theo giờ). Kết quả chính: mô hình tĩnh đạt 70,4% độ chính xác
  nhưng recall trung bình 3 mức chỉ 75,0% (phát hiện giờ Cao 58,5%; nhu cầu 2012 cao hơn 2011 khoảng 1,63 lần); thêm hiệu chỉnh mức đưa recall trung bình lên 83,4% (phát hiện giờ Cao 58,5% -> 90,0%)
  và độ chính xác lên 85,1%, đổi lại dư chuẩn bị tăng (8,8%). Thêm nhiệt độ nâng mô hình tĩnh lên 75,4% độ chính xác (recall trung bình 78,0%), và mô hình hiệu chỉnh lên 86,6% (recall trung bình 85,6%); độ ẩm thử thêm không cải thiện nên không được đưa vào. Sinh hình và bảng cho báo cáo (không cần DB):
  `python report/scripts/make_backtest_figure.py`.

## Lưu ý khi phân tích
- `weekday`: 0 = Chủ nhật (theo nguồn UCI). `season` theo nguồn nên một tháng có thể thuộc 2 mùa.
- Nguồn thiếu 165 giờ (không có bản ghi); trung bình theo giờ chỉ tính trên các giờ có bản ghi.
- Mức thời tiết "Heavy rain/snow" chỉ có 3 giờ quan sát, kết quả không đủ tin cậy.
