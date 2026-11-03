-- Star Schema: Bike Sharing DW (PostgreSQL)
DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;
SET search_path = dw;

-- Dim_Date: 1 dòng / ngày (731 ngày: 2011-01-01 .. 2012-12-31)
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,           -- yyyymmdd
    full_date       DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name      VARCHAR(10) NOT NULL,
    day_of_month    SMALLINT NOT NULL,
    weekday         SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0 = Chủ nhật (theo nguồn UCI)
    weekday_name    VARCHAR(10) NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    is_holiday      BOOLEAN NOT NULL,
    is_working_day  BOOLEAN NOT NULL,
    day_type        VARCHAR(12) NOT NULL,          -- Working day / Weekend / Holiday
    season          SMALLINT NOT NULL CHECK (season BETWEEN 1 AND 4),
    season_name     VARCHAR(10) NOT NULL,
    hours_recorded  SMALLINT NOT NULL CHECK (hours_recorded BETWEEN 1 AND 24),  -- số giờ có bản ghi trong nguồn
    is_complete_day BOOLEAN NOT NULL                -- hours_recorded = 24
);

-- Dim_Hour: 24 dòng
CREATE TABLE dim_hour (
    hour_key    SMALLINT PRIMARY KEY CHECK (hour_key BETWEEN 0 AND 23),
    hour_label  VARCHAR(11) NOT NULL,              -- '08:00-08:59'
    time_band   VARCHAR(20) NOT NULL               -- Đêm / Sáng / Trưa / Chiều / Tối
);

-- Dim_Weather: 4 mức thời tiết của nguồn
CREATE TABLE dim_weather (
    weather_key  SMALLINT PRIMARY KEY CHECK (weather_key BETWEEN 1 AND 4),
    weather_name VARCHAR(20) NOT NULL,
    description  VARCHAR(200) NOT NULL
);

-- Fact_Rentals: grain = 1 giờ (ngày x giờ), 17.379 dòng
CREATE TABLE fact_rentals (
    rental_key        SERIAL PRIMARY KEY,
    instant_id        INTEGER NOT NULL UNIQUE,     -- degenerate dimension (khóa dòng nguồn)
    date_key          INTEGER  NOT NULL REFERENCES dim_date(date_key),
    hour_key          SMALLINT NOT NULL REFERENCES dim_hour(hour_key),
    weather_key       SMALLINT NOT NULL REFERENCES dim_weather(weather_key),
    casual_cnt        INTEGER NOT NULL CHECK (casual_cnt >= 0),
    registered_cnt    INTEGER NOT NULL CHECK (registered_cnt >= 0),
    total_cnt         INTEGER NOT NULL CHECK (total_cnt >= 0),
    temp_norm         NUMERIC(6,4) NOT NULL,
    atemp_norm        NUMERIC(6,4) NOT NULL,
    hum_norm          NUMERIC(6,4) NOT NULL,
    windspeed_norm    NUMERIC(6,4) NOT NULL,
    temp_c            NUMERIC(5,2) NOT NULL,       -- temp * 41
    atemp_c           NUMERIC(5,2) NOT NULL,       -- atemp * 50
    humidity_pct      NUMERIC(5,2),                -- hum * 100; NULL khi hum = 0 (lỗi cảm biến)
    windspeed_kmh     NUMERIC(5,2) NOT NULL,       -- windspeed * 67
    CONSTRAINT chk_total CHECK (total_cnt = casual_cnt + registered_cnt),
    UNIQUE (date_key, hour_key)
);

CREATE INDEX idx_fact_date    ON fact_rentals(date_key);
CREATE INDEX idx_fact_hour    ON fact_rentals(hour_key);
CREATE INDEX idx_fact_weather ON fact_rentals(weather_key);
