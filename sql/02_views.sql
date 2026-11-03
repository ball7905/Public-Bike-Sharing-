-- View phẳng cho OLAP / Dashboard (thành viên B dùng)
SET search_path = dw;
CREATE OR REPLACE VIEW v_rentals_flat AS
SELECT f.rental_key, f.instant_id,
       d.full_date, d.year, d.quarter, d.month, d.month_name, d.weekday, d.weekday_name,
       d.is_weekend, d.is_holiday, d.is_working_day, d.day_type, d.season, d.season_name,
       d.hours_recorded, d.is_complete_day,
       h.hour_key AS hour, h.hour_label, h.time_band,
       w.weather_key, w.weather_name,
       f.casual_cnt, f.registered_cnt, f.total_cnt,
       f.temp_c, f.atemp_c, f.humidity_pct, f.windspeed_kmh
FROM fact_rentals f
JOIN dim_date d    ON d.date_key = f.date_key
JOIN dim_hour h    ON h.hour_key = f.hour_key
JOIN dim_weather w ON w.weather_key = f.weather_key;
