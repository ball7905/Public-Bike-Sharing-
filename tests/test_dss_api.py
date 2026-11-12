"""Test API DSS với DB đã nạp ETL. Chạy: pytest tests/test_dss_api.py -q"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

c = TestClient(app)
HOUR = pd.read_csv(ROOT / "data" / "hour.csv")


def test_thresholds_match_source_distribution():
    t = c.get("/api/dss/thresholds").json()
    lo, hi = HOUR["cnt"].quantile([1 / 3, 2 / 3])       # cùng phương pháp nội suy tuyến tính
    assert abs(t["thresholds"]["low"] - lo) < 1e-6 and abs(t["thresholds"]["high"] - hi) < 1e-6
    assert t["distribution"]["n_obs"] == len(HOUR)
    vals = [p["value"] for p in t["distribution"]["percentiles"]]
    assert vals == sorted(vals)                          # phân vị đơn điệu
    share = t["observation_share"]
    assert abs(sum(share.values()) - 1) < 1e-9
    assert all(0.30 < v < 0.37 for v in share.values())  # tam phân vị -> mỗi mức ~1/3


def test_plan_matches_source_group_means():
    p = c.get("/api/dss/plan", params={"day_group": "working", "weather": 1}).json()
    src = HOUR[(HOUR.workingday == 1) & (HOUR.weathersit == 1)].groupby("hr")["cnt"].agg(["mean", "size"])
    assert len(p["hours"]) == 24
    for h in p["hours"]:
        assert abs(h["avg_rentals"] - src.loc[h["hour"], "mean"]) < 1e-6
        assert h["n_obs"] == src.loc[h["hour"], "size"]
        assert h["level"] in ("low", "medium", "high")
    # giờ cao điểm đi làm của ngày làm việc phải được cảnh báo
    assert any(a["start_hour"] <= 8 <= a["end_hour"] for a in p["alerts"])
    assert any(a["start_hour"] <= 17 <= a["end_hour"] for a in p["alerts"])


def test_period_filter_changes_thresholds():
    all_ = c.get("/api/dss/thresholds").json()["thresholds"]
    y11 = c.get("/api/dss/thresholds", params={"year": 2011}).json()
    assert y11["period"] == {"year": [2011]}
    assert y11["thresholds"]["high"] < all_["high"]    # 2011 có nhu cầu thấp hơn
    # bộ lọc ngoài kỳ lịch sử (day_type) không ảnh hưởng DSS
    assert c.get("/api/dss/thresholds", params={"day_type": "Weekend"}).json()["thresholds"] == all_


def test_matrix_and_sparse_weather():
    m = c.get("/api/dss/matrix").json()
    assert len(m["cells"]) == 24 * len(m["cols"]) == 24 * 8
    heavy = [x for x in m["cells"] if x["weather"] == 4]
    assert sum(x["n_obs"] for x in heavy) == 3 and not any(x["reliable"] for x in heavy)
    p = c.get("/api/dss/plan", params={"day_group": "non_working", "weather": 4}).json()
    assert p["summary"]["counts"]["no_data"] == 23 and p["notes"]


def test_dss_validation_errors():
    assert c.get("/api/dss/plan", params={"weather": 9}).status_code == 422
    assert c.get("/api/dss/plan", params={"day_group": "holiday"}).status_code == 422
    assert c.get("/api/dss/thresholds", params={"q_low": 0.8, "q_high": 0.5}).status_code == 422
    assert c.get("/api/dss/thresholds", params={"year": 1999}).status_code == 422


def test_backtest_out_of_sample():
    b = c.get("/api/dss/backtest").json()
    assert len(b["experiments"]) == 6                    # 2 mô hình x 3 cách huấn luyện
    assert b["experiments"][0]["id"] == "full_static"
    assert b["test_year"] == 2012
    assert b["n_test"] == int((HOUR["dteday"].str.startswith("2012")).sum())   # số giờ 2012 trong hour.csv
    full_static = b["experiments"][0]
    assert 0.68 < full_static["metrics"]["accuracy"] < 0.72
    assert len(full_static["monthly"]) == 12
    assert c.get("/api/dss/backtest", params={"q_low": 0.8, "q_high": 0.5}).status_code == 422
