"""FR06 / Nhóm 2: ảnh hưởng nhiệt độ, độ ẩm. Cần DB đã nạp ETL. Chạy: pytest tests/test_climate.py -q"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

c = TestClient(app)
H = pd.read_csv(ROOT / "data" / "hour.csv")
H["temp_c"], H["hum_pct"] = (H.temp * 41).round(2), (H.hum * 100).round(2).where(H.hum > 0)  # hum = 0 -> NULL như ETL


def test_temp_bins_match_source():
    r = c.get("/api/climate", params={"by": "temp"}).json()
    src = H.groupby(np.minimum(H.temp_c // 5 * 5, 35)).cnt.agg(["size", "mean"])
    assert [b["lo"] for b in r["bins"]] == [int(x) for x in src.index]
    for b in r["bins"]:
        assert b["n_hours"] == src.loc[b["lo"], "size"]
        assert abs(b["avg_total"] - src.loc[b["lo"], "mean"]) < 1e-6
        assert abs(b["avg_casual"] + b["avg_registered"] - b["avg_total"]) < 1e-6
    assert sum(b["n_hours"] for b in r["bins"]) == len(H)
    assert r["bins"][-1]["label"] == "≥35°C"


def test_humidity_bins_and_reliability():
    r = c.get("/api/climate", params={"by": "humidity"}).json()
    hv = H.dropna(subset=["hum_pct"])
    src = hv.groupby(np.minimum(hv.hum_pct // 10 * 10, 90)).cnt.agg(["size", "mean"])
    assert [b["lo"] for b in r["bins"]] == [int(x) for x in src.index]
    for b in r["bins"]:                                 # dòng humidity NULL không bị dồn vào 90-100%
        assert b["n_hours"] == src.loc[b["lo"], "size"]
        assert abs(b["avg_total"] - src.loc[b["lo"], "mean"]) < 1e-6
    assert sum(b["n_hours"] for b in r["bins"]) == len(H) - 22
    assert all(b["reliable"] == (b["n_hours"] >= r["min_obs"]) for b in r["bins"])
    assert not r["bins"][0]["reliable"]                 # 0-10%: chỉ 1 giờ


def test_correlations_match_pandas():
    corr = c.get("/api/climate").json()["correlation"]
    assert abs(corr["hourly"]["temp"] - H.cnt.corr(H.temp_c)) < 1e-6
    assert abs(corr["hourly"]["humidity"] - H.cnt.corr(H.hum_pct)) < 1e-6
    assert corr["hourly"]["temp"] > 0 > corr["hourly"]["humidity"]
    assert corr["hourly"]["n"] == len(H) and corr["daily"]["n"] == 731


def test_climate_respects_filters_and_validation():
    full = c.get("/api/climate").json()
    y12 = c.get("/api/climate", params={"year": 2012}).json()
    assert sum(b["n_hours"] for b in y12["bins"]) < sum(b["n_hours"] for b in full["bins"])
    assert c.get("/api/climate", params={"by": "wind"}).status_code == 422
