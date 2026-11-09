-- DSS: phân loại nhu cầu (FR09) và khuyến nghị (FR10) bằng SQL thuần, dùng cho báo cáo / đối chiếu.
-- Logic tương đương src/dss/engine.py + src/api/dss_queries.py (API là nơi hệ thống thực sự dùng).
SET search_path = dw;

-- (1) Khảo sát phân phối lượt thuê theo giờ để chọn ngưỡng
SELECT COUNT(*) AS n_obs, ROUND(AVG(total_cnt), 1) AS mean, ROUND(STDDEV_SAMP(total_cnt), 1) AS std,
       percentile_cont(ARRAY[0.10, 0.25, 1/3.0, 0.50, 2/3.0, 0.75, 0.90]) WITHIN GROUP (ORDER BY total_cnt) AS p10_25_33_50_67_75_90
FROM v_rentals_flat;

-- (2) Phân loại nhóm giờ x loại ngày x thời tiết theo ngưỡng P33,3 / P66,7 và gán khuyến nghị
WITH th AS (
    SELECT percentile_cont(1/3.0) WITHIN GROUP (ORDER BY total_cnt) AS low,
           percentile_cont(2/3.0) WITHIN GROUP (ORDER BY total_cnt) AS high
    FROM v_rentals_flat
), g AS (
    SELECT hour,
           CASE WHEN is_working_day THEN 'Ngày làm việc' ELSE 'Ngày nghỉ' END AS day_group,
           weather_name, COUNT(*) AS n_obs, AVG(total_cnt) AS avg_rentals
    FROM v_rentals_flat
    GROUP BY hour, is_working_day, weather_key, weather_name
)
SELECT g.hour, g.day_group, g.weather_name, g.n_obs, ROUND(g.avg_rentals, 1) AS avg_rentals,
       CASE WHEN g.avg_rentals < th.low THEN 'Thấp'
            WHEN g.avg_rentals > th.high THEN 'Cao'
            ELSE 'Trung bình' END AS demand_level,
       CASE WHEN g.avg_rentals < th.low THEN 'Duy trì mức chuẩn bị cơ bản'
            WHEN g.avg_rentals > th.high THEN 'Ưu tiên chuẩn bị thêm xe và nguồn lực phục vụ'
            ELSE 'Theo dõi nhu cầu và duy trì nguồn lực phù hợp' END AS recommendation,
       g.n_obs < 30 AS low_reliability
FROM g CROSS JOIN th
ORDER BY g.day_group, g.weather_name, g.hour;

-- (3) Các giờ cần ưu tiên chuẩn bị xe: ngày làm việc, trời quang (Clear)
WITH th AS (SELECT percentile_cont(2/3.0) WITHIN GROUP (ORDER BY total_cnt) AS high FROM v_rentals_flat)
SELECT hour, ROUND(AVG(total_cnt), 1) AS avg_rentals
FROM v_rentals_flat
WHERE is_working_day AND weather_key = 1
GROUP BY hour
HAVING AVG(total_cnt) > (SELECT high FROM th)
ORDER BY avg_rentals DESC;
