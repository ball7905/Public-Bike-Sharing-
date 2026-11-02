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

## Ghi chú chất lượng dữ liệu

- Số giờ lý thuyết (731 ngày x 24) = 17,544; fact có 17,379 dòng, tức **165 giờ không có bản ghi** trong nguồn. ETL không tự thêm các dòng này; khi tính trung bình theo giờ cần lưu ý chúng bị bỏ qua.
- Thuộc tính thời tiết được lưu cả dạng chuẩn hóa gốc (`*_norm`) và dạng quy đổi (temp x 41, atemp x 50, hum x 100, windspeed x 67 theo Readme UCI).
