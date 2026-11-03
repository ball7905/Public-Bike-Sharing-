"""Kiểm thử bước Transform trên dữ liệu nguồn thật, không cần DB. Chạy: pytest tests/test_etl.py -q"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "etl"))
from extract import extract  # noqa: E402
from transform import clean, transform  # noqa: E402

HOUR, DAY = extract()
T = transform(HOUR)


def test_row_counts():
    assert len(T["fact_rentals"]) == len(HOUR) == 17_379
    assert len(T["dim_date"]) == len(DAY) == 731
    assert len(T["dim_hour"]) == 24 and len(T["dim_weather"]) == 4


def test_totals_preserved():
    f = T["fact_rentals"]
    assert f["total_cnt"].sum() == HOUR["cnt"].sum() == DAY["cnt"].sum()
    assert (f["total_cnt"] == f["casual_cnt"] + f["registered_cnt"]).all()


def test_fact_keys_exist_in_dims():
    f = T["fact_rentals"]
    assert f["date_key"].isin(T["dim_date"]["date_key"]).all()
    assert f["hour_key"].isin(T["dim_hour"]["hour_key"]).all()
    assert f["weather_key"].isin(T["dim_weather"]["weather_key"]).all()
    assert not f.duplicated(["date_key", "hour_key"]).any()     # grain = ngày x giờ


def test_hours_recorded():
    d = T["dim_date"]
    assert d["hours_recorded"].sum() == len(HOUR)
    assert (d["is_complete_day"] == (d["hours_recorded"] == 24)).all()
    sandy = d.loc[d["full_date"].astype(str) == "2012-10-29", "hours_recorded"].item()
    assert sandy == 1                                           # bão Sandy: nguồn chỉ có 1 giờ


def test_zero_humidity_becomes_null():
    f = T["fact_rentals"]
    n_zero = int((HOUR["hum"] == 0).sum())
    assert n_zero == 22
    assert f["humidity_pct"].isna().sum() == n_zero
    assert (f.loc[f["humidity_pct"].isna(), "hum_norm"] == 0).all()   # giá trị gốc vẫn giữ


def test_weekday_matches_source():
    d = T["dim_date"].set_index("full_date")["weekday"]
    src = DAY.assign(dteday=DAY["dteday"].astype("datetime64[ns]").dt.date).set_index("dteday")["weekday"]
    assert (d == src).all()


def test_reject_out_of_range():
    bad = HOUR.copy()
    bad.loc[0, "hr"] = 24
    with pytest.raises(ValueError, match="hr"):
        clean(bad)


def test_reject_inconsistent_calendar():
    bad = HOUR.copy()
    bad.loc[0, "weekday"] = (bad.loc[0, "weekday"] + 1) % 7
    with pytest.raises(ValueError, match="weekday"):
        clean(bad)


def test_drop_rows_violating_sum():
    bad = HOUR.copy()
    bad.loc[5, "cnt"] += 1
    assert len(clean(bad)) == len(HOUR) - 1
