-- ============================================================
-- Truy vấn OLAP mẫu trên Star Schema (schema dw) - FR05, FR06, FR07
-- Chạy trực tiếp trong pgAdmin / psql. Tất cả dùng view dw.v_rentals_flat.
-- ============================================================
SET search_path = dw;

-- ---------- ROLL-UP: năm -> tháng, kèm tổng cấp trên (ROLLUP) ----------
SELECT year, month, SUM(total_cnt) AS total_rentals
FROM v_rentals_flat
GROUP BY ROLLUP (year, month)
ORDER BY year, month;            -- dòng month IS NULL là tổng của năm; dòng cuối là tổng toàn bộ

-- ---------- DRILL-DOWN: Năm 2012 -> Quý -> Tháng 7 -> Ngày -> Giờ ----------
SELECT year, SUM(total_cnt) AS total_rentals FROM v_rentals_flat GROUP BY year ORDER BY year;                    -- cấp năm
SELECT quarter, SUM(total_cnt) FROM v_rentals_flat WHERE year = 2012 GROUP BY quarter ORDER BY quarter;          -- khoan xuống quý
SELECT month_name, SUM(total_cnt) FROM v_rentals_flat WHERE year = 2012 AND quarter = 3
GROUP BY month, month_name ORDER BY month;                                                                       -- khoan xuống tháng
SELECT full_date, SUM(total_cnt) FROM v_rentals_flat WHERE year = 2012 AND month = 7
GROUP BY full_date ORDER BY full_date;                                                                           -- khoan xuống ngày
SELECT hour, total_cnt FROM v_rentals_flat WHERE full_date = '2012-07-06' ORDER BY hour;                         -- khoan xuống giờ

-- ---------- SLICE: cố định MỘT chiều (thời tiết = Clear), xem theo tháng ----------
SELECT month_name, SUM(total_cnt) AS total_rentals, ROUND(AVG(total_cnt), 1) AS avg_hourly
FROM v_rentals_flat
WHERE weather_name = 'Clear'
GROUP BY month, month_name ORDER BY month;

-- ---------- DICE: cố định NHIỀU chiều (2012, mùa hè/thu, ngày làm việc, giờ cao điểm) ----------
SELECT hour, ROUND(AVG(total_cnt), 1) AS avg_hourly, SUM(total_cnt) AS total_rentals
FROM v_rentals_flat
WHERE year = 2012
  AND season IN (2, 3)
  AND day_type = 'Working day'
  AND time_band IN ('Sáng (6-9h)', 'Chiều (16-19h)')
GROUP BY hour ORDER BY hour;

-- ---------- PIVOT: hàng = tháng, cột = thời tiết, giá trị = trung bình lượt thuê / giờ ----------
SELECT month_name,
       ROUND(AVG(total_cnt) FILTER (WHERE weather_key = 1), 1) AS clear,
       ROUND(AVG(total_cnt) FILTER (WHERE weather_key = 2), 1) AS mist,
       ROUND(AVG(total_cnt) FILTER (WHERE weather_key = 3), 1) AS light_rain_snow,
       ROUND(AVG(total_cnt) FILTER (WHERE weather_key = 4), 1) AS heavy_rain_snow
FROM v_rentals_flat
GROUP BY month, month_name ORDER BY month;

-- ---------- FR05: tổng hợp theo giờ / ngày / tháng / năm / mùa ----------
SELECT hour, SUM(total_cnt) AS total, ROUND(AVG(total_cnt),1) AS avg_hourly FROM v_rentals_flat GROUP BY hour ORDER BY hour;
SELECT season_name, SUM(total_cnt) AS total, ROUND(AVG(total_cnt),1) AS avg_hourly FROM v_rentals_flat GROUP BY season, season_name ORDER BY season;

-- ---------- FR06: theo thời tiết, ngày làm việc, nhóm người dùng ----------
SELECT weather_name, COUNT(*) AS hours_observed, ROUND(AVG(total_cnt),1) AS avg_hourly
FROM v_rentals_flat GROUP BY weather_key, weather_name ORDER BY weather_key;

SELECT day_type, COUNT(DISTINCT full_date) AS days,
       ROUND(SUM(total_cnt)::numeric / COUNT(DISTINCT full_date), 1) AS avg_daily,
       ROUND(AVG(total_cnt), 1) AS avg_hourly
FROM v_rentals_flat GROUP BY day_type ORDER BY day_type;

SELECT hour, SUM(casual_cnt) AS casual, SUM(registered_cnt) AS registered
FROM v_rentals_flat GROUP BY hour ORDER BY hour;

-- ---------- FR08: 8 KPI ----------
SELECT SUM(total_cnt) AS total_rentals,
       ROUND(AVG(total_cnt), 2) AS avg_hourly_rentals,
       ROUND(100.0 * SUM(registered_cnt) / SUM(total_cnt), 2) AS registered_ratio_pct,
       ROUND(100.0 * SUM(casual_cnt)     / SUM(total_cnt), 2) AS casual_ratio_pct
FROM v_rentals_flat;

-- Peak Hour / Lowest Demand Hour: giờ trong ngày có trung bình lượt thuê cao nhất / thấp nhất
(SELECT 'peak' AS kind, hour, ROUND(AVG(total_cnt),1) AS avg_rentals FROM v_rentals_flat GROUP BY hour ORDER BY avg_rentals DESC LIMIT 1)
UNION ALL
(SELECT 'lowest', hour, ROUND(AVG(total_cnt),1) FROM v_rentals_flat GROUP BY hour ORDER BY AVG(total_cnt) ASC LIMIT 1);

-- Working Day / Non-working Day Demand: trung bình lượt thuê MỖI NGÀY
SELECT is_working_day,
       ROUND(SUM(total_cnt)::numeric / COUNT(DISTINCT full_date), 1) AS avg_daily_rentals
FROM v_rentals_flat GROUP BY is_working_day;
