# Báo cáo đối chiếu ETL

| Kiểm tra | Kỳ vọng | Thực tế | Kết quả |
|---|---:|---:|:---:|
| Số dòng fact = số dòng hour.csv | 17,379 | 17,379 | PASS |
| Tổng cnt (fact vs hour.csv) | 3,292,679 | 3,292,679 | PASS |
| Tổng casual (fact vs hour.csv) | 620,017 | 620,017 | PASS |
| Tổng registered (fact vs hour.csv) | 2,672,662 | 2,672,662 | PASS |
| Tổng cnt (fact vs day.csv) | 3,292,679 | 3,292,679 | PASS |
| Số ngày dim_date = số dòng day.csv | 731 | 731 | PASS |
| Số dòng dim_hour | 24 | 24 | PASS |
| Số dòng fact mồ côi (vi phạm FK) | 0 | 0 | PASS |
| Số dòng vi phạm cnt = casual + registered | 0 | 0 | PASS |
| Số ngày có tổng cnt lệch day.csv | 0 | 0 | PASS |
| Tổng hours_recorded (dim_date) = số dòng hour.csv | 17,379 | 17,379 | PASS |
| Số ngày thiếu giờ (is_complete_day = false) | 76 | 76 | PASS |
| Số dòng humidity_pct NULL = số dòng hum = 0 trong nguồn | 22 | 22 | PASS |

## Ghi chú chất lượng dữ liệu

- Số giờ lý thuyết (731 ngày x 24) = 17,544; fact có 17,379 dòng, tức **165 giờ không có bản ghi** trong nguồn. ETL không tự thêm các dòng này; khi tính trung bình theo giờ cần lưu ý chúng bị bỏ qua.
- **76 ngày thiếu giờ** (`dim_date.is_complete_day = false`, số giờ ở `hours_recorded`). Ngày thiếu nhiều nhất: 2012-10-29 (1 giờ), 2011-01-27 (8 giờ), 2012-10-30 (11 giờ), 2011-01-18 (12 giờ). Khi tính trung bình lượt thuê / ngày nên lọc `is_complete_day` để tránh bị kéo xuống.
- **22 dòng có hum = 0** (ngày 2011-03-10): độ ẩm 0% không có thật, coi là lỗi cảm biến -> `humidity_pct = NULL` (giữ `hum_norm` gốc để truy vết). Lượt thuê của các dòng này vẫn giữ.
- **2,180 dòng (12.5%) có windspeed = 0**: tỷ lệ cao bất thường, nhiều khả năng là thiếu dữ liệu chứ không phải lặng gió. ETL giữ nguyên giá trị; cần thận trọng khi phân tích theo tốc độ gió.
- Thuộc tính thời tiết được lưu cả dạng chuẩn hóa gốc (`*_norm`) và dạng quy đổi (temp x 41, atemp x 50, hum x 100, windspeed x 67 theo Readme UCI).
