import logging
import pandas as pd
from config import (TEMP_MAX, ATEMP_MAX, HUM_MAX, WIND_MAX, SEASON_NAMES, WEATHER)

log = logging.getLogger(__name__)

EXPECTED_COLS = ["instant", "dteday", "season", "yr", "mnth", "hr", "holiday", "weekday",
                 "workingday", "weathersit", "temp", "atemp", "hum", "windspeed",
                 "casual", "registered", "cnt"]


def time_band(h: int) -> str:
    if h <= 5:
        return "Đêm (0-5h)"
    if h <= 9:
        return "Sáng (6-9h)"
    if h <= 15:
        return "Trưa (10-15h)"
    if h <= 19:
        return "Chiều (16-19h)"
    return "Tối (20-23h)"


def clean(hour: pd.DataFrame) -> pd.DataFrame:
    missing = set(EXPECTED_COLS) - set(hour.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {missing}")
    df = hour[EXPECTED_COLS].copy()
    df["dteday"] = pd.to_datetime(df["dteday"], format="%Y-%m-%d")

    n_null = int(df.isna().sum().sum())
    n_dup = int(df.duplicated().sum())
    n_dup_id = int(df["instant"].duplicated().sum())
    if n_null or n_dup or n_dup_id:
        log.warning("Phát hiện null=%d, trùng dòng=%d, trùng instant=%d -> loại bỏ", n_null, n_dup, n_dup_id)
        df = df.dropna().drop_duplicates().drop_duplicates(subset="instant")

    bad_sum = df["cnt"] != df["casual"] + df["registered"]
    if bad_sum.any():
        log.warning("%d dòng vi phạm cnt = casual + registered -> loại bỏ", int(bad_sum.sum()))
        df = df[~bad_sum]

    ranges = {"season": (1, 4), "hr": (0, 23), "weekday": (0, 6), "weathersit": (1, 4),
              "holiday": (0, 1), "workingday": (0, 1), "mnth": (1, 12), "yr": (0, 1)}
    for col, (lo, hi) in ranges.items():
        out = ~df[col].between(lo, hi)
        if out.any():
            raise ValueError(f"{col} ngoài miền [{lo},{hi}]: {int(out.sum())} dòng")
    for col in ["temp", "atemp", "hum", "windspeed"]:
        if not df[col].between(0, 1).all():
            raise ValueError(f"{col} ngoài miền [0,1]")
    return df.reset_index(drop=True)


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    per_day = df.groupby("dteday").agg(season=("season", "first"), holiday=("holiday", "first"),
                                       workingday=("workingday", "first")).reset_index()
    cal = pd.DataFrame({"full_date": pd.date_range(df["dteday"].min(), df["dteday"].max())})
    d = cal.merge(per_day.rename(columns={"dteday": "full_date"}), on="full_date", how="left")
    if d[["season", "holiday", "workingday"]].isna().any().any():
        raise ValueError("Có ngày trong lịch không có dữ liệu nguồn")
    out = pd.DataFrame({
        "date_key": d["full_date"].dt.strftime("%Y%m%d").astype(int),
        "full_date": d["full_date"].dt.date,
        "year": d["full_date"].dt.year,
        "quarter": d["full_date"].dt.quarter,
        "month": d["full_date"].dt.month,
        "month_name": d["full_date"].dt.month_name(),
        "day_of_month": d["full_date"].dt.day,
        "weekday": (d["full_date"].dt.dayofweek + 1) % 7,   # 0 = Chủ nhật như nguồn
        "weekday_name": d["full_date"].dt.day_name(),
        "is_weekend": d["full_date"].dt.dayofweek >= 5,
        "is_holiday": d["holiday"].astype(bool),
        "is_working_day": d["workingday"].astype(bool),
        "season": d["season"].astype(int),
    })
    out["season_name"] = out["season"].map(SEASON_NAMES)
    out["day_type"] = "Working day"
    out.loc[out["is_weekend"], "day_type"] = "Weekend"
    out.loc[out["is_holiday"], "day_type"] = "Holiday"
    return out


def build_dim_hour() -> pd.DataFrame:
    h = pd.DataFrame({"hour_key": range(24)})
    h["hour_label"] = h["hour_key"].map(lambda x: f"{x:02d}:00-{x:02d}:59")
    h["time_band"] = h["hour_key"].map(time_band)
    return h


def build_dim_weather() -> pd.DataFrame:
    return pd.DataFrame([(k, v[0], v[1]) for k, v in WEATHER.items()],
                        columns=["weather_key", "weather_name", "description"])


def build_fact(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "instant_id": df["instant"],
        "date_key": df["dteday"].dt.strftime("%Y%m%d").astype(int),
        "hour_key": df["hr"],
        "weather_key": df["weathersit"],
        "casual_cnt": df["casual"],
        "registered_cnt": df["registered"],
        "total_cnt": df["cnt"],
        "temp_norm": df["temp"],
        "atemp_norm": df["atemp"],
        "hum_norm": df["hum"],
        "windspeed_norm": df["windspeed"],
        "temp_c": (df["temp"] * TEMP_MAX).round(2),
        "atemp_c": (df["atemp"] * ATEMP_MAX).round(2),
        "humidity_pct": (df["hum"] * HUM_MAX).round(2),
        "windspeed_kmh": (df["windspeed"] * WIND_MAX).round(2),
    })


def transform(hour: pd.DataFrame):
    df = clean(hour)
    tables = {
        "dim_date": build_dim_date(df),
        "dim_hour": build_dim_hour(),
        "dim_weather": build_dim_weather(),
        "fact_rentals": build_fact(df),
    }
    for k, v in tables.items():
        log.info("Transform: %s = %d dòng", k, len(v))
    return tables
