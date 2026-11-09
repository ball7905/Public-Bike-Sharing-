"""Unit test mô hình DSS (không cần CSDL). Chạy: pytest tests/test_dss_engine.py -q"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dss import engine as E  # noqa: E402

TH = E.make_thresholds(70, 225, 1 / 3, 2 / 3)
CLEAR = {"key": 1, "name": "Clear"}


def test_classify_boundaries():
    assert E.classify(69.9, TH) == "low"
    assert E.classify(70, TH) == "medium"          # bằng ngưỡng thấp -> Trung bình
    assert E.classify(225, TH) == "medium"         # bằng ngưỡng cao -> Trung bình
    assert E.classify(225.1, TH) == "high"
    assert E.classify(None, TH) is None


def test_invalid_thresholds():
    with pytest.raises(ValueError):
        E.make_thresholds(300, 100, 1 / 3, 2 / 3)
    with pytest.raises(ValueError):
        E.make_thresholds(None, None, 1 / 3, 2 / 3)
    for lo, hi in [(0.5, 0.5), (0.8, 0.2), (0, 0.5), (0.5, 1)]:
        with pytest.raises(ValueError):
            E.validate_quantiles(lo, hi)


def test_every_level_has_recommendation():
    assert set(E.RECOMMENDATIONS) == set(E.LEVELS) == set(E.LEVEL_LABELS)


def rows(values, n=100):
    return [{"hour": h, "n_obs": n, "avg_rentals": v, "avg_casual": v * 0.2, "avg_registered": v * 0.8}
            for h, v in enumerate(values) if v is not None]


def test_plan_covers_24_hours_with_one_level_each():
    vals = [10] * 7 + [300, 500, 250] + [150] * 6 + [300, 600, 550, 400] + [100] * 4
    p = E.build_plan(rows(vals), TH, 190, "working", CLEAR)
    assert [h["hour"] for h in p["hours"]] == list(range(24))
    c = p["summary"]["counts"]
    assert c["low"] + c["medium"] + c["high"] + c["no_data"] == 24
    for h in p["hours"]:
        assert h["level"] == E.classify(h["avg_rentals"], TH)
        assert h["recommendation"] == E.RECOMMENDATIONS[h["level"]]
    assert p["summary"]["peak"]["hour"] == 17 and p["summary"]["lowest"]["avg_rentals"] == 10
    assert [x["hour"] for x in p["summary"]["priority_hours"]] == [17, 18, 8, 19, 7, 16, 9]   # giảm dần


def test_alert_windows_merge_consecutive_high_hours():
    vals = [10] * 7 + [300, 500, 250] + [150] * 6 + [300, 600, 550, 400] + [100] * 4
    alerts = E.build_plan(rows(vals), TH, 190, "working", CLEAR)["alerts"]
    assert [(a["start_hour"], a["end_hour"], a["peak_hour"]) for a in alerts] == [(7, 9, 8), (16, 19, 17)]
    assert alerts[0]["prepare_before"] == "06:00"
    assert E.build_plan(rows([300] + [10] * 23), TH, 190, "working", CLEAR)["alerts"][0]["prepare_before"] == "23:00"


def test_missing_and_sparse_groups_are_flagged():
    vals = [None] * 12 + [300] * 12
    p = E.build_plan(rows(vals, n=5), TH, 190, "non_working", CLEAR)
    assert p["summary"]["counts"]["no_data"] == 12
    assert p["hours"][0]["level"] is None and p["hours"][0]["recommendation"] == E.NO_DATA_RECOMMENDATION
    assert not p["hours"][12]["reliable"] and p["alerts"][0]["low_reliability"]
    assert len(p["notes"]) == 2


def test_matrix_shape():
    r = [{"hour": h, "day_group": "working", "weather_key": 1, "n_obs": 50, "avg_rentals": 100} for h in range(24)]
    m = E.build_matrix(r, TH, 190, [CLEAR, {"key": 2, "name": "Mist"}])
    assert len(m["cols"]) == 4 and len(m["cells"]) == 24 * 4
    assert sum(1 for c in m["cells"] if c["level"] == "medium") == 24
