"""Unit test backtest mô hình DSS (không cần CSDL). Chạy: pytest tests/test_dss_backtest.py -q"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dss import backtest as B  # noqa: E402

HOUR_CSV = Path(__file__).resolve().parents[1] / "data" / "hour.csv"
EXP_IDS = ["full_static", "full_expanding", "full_expanding_adjusted",
           "hour_only_static", "hour_only_expanding", "hour_only_expanding_adjusted"]


def rec(d, hour=0, group="working", w=1, cnt=0):
    return {"date": d, "hour": hour, "day_group": group, "weather_key": w, "total_cnt": cnt}


def synth(value_fn, hours=(0, 12)):
    """Bản ghi tổng hợp cho 2 năm 2011-2012, mỗi ngày 2 giờ (0h và 12h)."""
    recs, d = [], date(2011, 1, 1)
    while d.year <= 2012:
        for h in hours:
            group = "non_working" if d.weekday() >= 5 else "working"
            recs.append(rec(d, h, group, 1, value_fn(d, h)))
        d += timedelta(days=1)
    return recs


def exp_by_id(result):
    return {e["id"]: e for e in result["experiments"]}


# ---------- quantile ----------

def test_quantile_matches_linear_interpolation():
    assert B.quantile([1, 2, 3, 4], 1 / 3) == pytest.approx(2.0)
    assert B.quantile([1, 2, 3, 4], 0.5) == pytest.approx(2.5)
    assert B.quantile([1, 2, 3, 4], 0) == 1
    assert B.quantile([1, 2, 3, 4], 1) == 4
    assert B.quantile([], 0.5) is None


# ---------- metrics ----------

PAIRS = [("low", "low"), ("low", "medium"), ("medium", "low"), ("medium", "medium"),
         ("high", "high"), ("high", "medium"), ("high", "low"), ("medium", "high")]


def test_metrics_accuracy_and_confusion():
    m = B.metrics(PAIRS)
    assert m["n"] == 8
    assert m["accuracy"] == pytest.approx(3 / 8)
    assert m["confusion"] == {
        "low": {"low": 1, "medium": 1, "high": 0},
        "medium": {"low": 1, "medium": 1, "high": 1},
        "high": {"low": 1, "medium": 1, "high": 1},
    }


def test_metrics_per_level_and_macro_f1():
    m = B.metrics(PAIRS)
    # high: thực tế 3 giờ, dự báo high 2 giờ, đúng 1 giờ
    assert m["per_level"]["high"] == pytest.approx({"precision": 0.5, "recall": 1 / 3, "f1": 0.4, "support": 3})
    assert m["per_level"]["low"]["precision"] == pytest.approx(1 / 3)
    assert m["per_level"]["low"]["recall"] == pytest.approx(0.5)
    assert m["per_level"]["medium"]["recall"] == pytest.approx(1 / 3)
    assert m["macro_f1"] == pytest.approx((0.4 + 1 / 3 + 0.4) / 3)


def test_metrics_prepared_rates_and_missed_high():
    m = B.metrics(PAIRS)
    # chuẩn bị thiếu: thực tế cao hơn dự báo -> (medium,low), (high,medium), (high,low)
    assert m["under_prepared_rate"] == pytest.approx(3 / 8)
    # chuẩn bị thừa: dự báo cao hơn thực tế -> (low,medium), (medium,high)
    assert m["over_prepared_rate"] == pytest.approx(2 / 8)
    # giờ CAO thực tế bị dự báo không phải CAO: (high,medium), (high,low)
    assert m["missed_high"] == 2


def test_metrics_mae_and_empty_input():
    assert B.metrics(PAIRS, [1, 2, 3])["mae"] == pytest.approx(2.0)
    e = B.metrics([])
    assert e["n"] == 0 and e["accuracy"] == 0.0 and e["macro_f1"] == 0.0
    assert e["under_prepared_rate"] == 0.0 and e["per_level"]["high"]["recall"] == 0.0


# ---------- fit / predict ----------

def test_predict_fallback_chain_hour_then_overall():
    train = [rec(date(2011, 1, 1), 5, "working", 1, 100),
             rec(date(2011, 1, 2), 5, "working", 1, 200),
             rec(date(2011, 1, 1), 6, "non_working", 1, 50)]
    f = B.fit(train, "full")
    assert B.predict(f, rec(date(2012, 1, 1), 5, "working", 1)) == (150.0, False)   # nhóm đã biết
    assert B.predict(f, rec(date(2012, 1, 1), 5, "working", 3)) == (150.0, True)    # thời tiết lạ -> TB theo giờ
    assert B.predict(f, rec(date(2012, 1, 1), 9, "working", 1))[1] is True          # giờ lạ -> TB toàn bộ
    assert B.predict(f, rec(date(2012, 1, 1), 9, "working", 1))[0] == pytest.approx(350 / 3)
    h = B.fit(train, "hour_only")
    assert B.predict(h, rec(date(2012, 1, 1), 5, "non_working", 4)) == (150.0, False)


def test_fit_thresholds_use_quantiles_and_engine_levels():
    train = [rec(date(2011, 1, 1), 0, cnt=c) for c in [1, 2, 3, 4]]
    f = B.fit(train, "hour_only")
    assert f["th"]["low"] == pytest.approx(2.0) and f["th"]["high"] == pytest.approx(3.0)


def test_fit_and_run_reject_empty_input():
    with pytest.raises(ValueError):
        B.fit([], "full")
    with pytest.raises(ValueError):
        B.run_backtest(synth(lambda d, h: 10), 2030)          # không có năm kiểm thử
    with pytest.raises(ValueError):
        B.run_backtest([r for r in synth(lambda d, h: 10) if r["date"].year == 2012], 2012)  # không có train
    with pytest.raises(ValueError):
        B.run_backtest(synth(lambda d, h: 10), 2012, 0.8, 0.2)


# ---------- synthetic end-to-end checks ----------

def test_static_trains_only_on_prior_year():
    recs = synth(lambda d, h: 100 if d.year == 2011 else 1000)
    res = B.run_backtest(recs, 2012)
    assert res["n_train_static"] == sum(1 for r in recs if r["date"].year == 2011)
    st = exp_by_id(res)["full_static"]
    # ngưỡng chỉ lấy từ 2011 (toàn bộ 100) -> mọi tháng cùng ngưỡng 100/100
    assert all(m["th_low"] == 100 and m["th_high"] == 100 for m in st["monthly"])
    # 2012 toàn 1000 > ngưỡng -> thực tế CAO, dự báo TB
    assert st["metrics"]["confusion"]["high"] == {"low": 0, "medium": res["n_test"], "high": 0}


def test_expanding_month_never_uses_current_or_later_months():
    def base(d, h):
        return 10 + (d.day % 7) * 3 + h + (50 if d.year == 2012 else 0)

    orig = exp_by_id(B.run_backtest(synth(base), 2012))["full_expanding"]["monthly"]
    for m in range(2, 13):
        poisoned = synth(lambda d, h, m=m: 10 ** 6 if (d.year == 2012 and d.month >= m) else base(d, h))
        pois = exp_by_id(B.run_backtest(poisoned, 2012))["full_expanding"]["monthly"]
        assert pois[m - 1]["th_low"] == orig[m - 1]["th_low"]
        assert pois[m - 1]["th_high"] == orig[m - 1]["th_high"]


def test_unseen_group_counted_as_fallback_in_run():
    recs = synth(lambda d, h: 10)
    recs += [rec(date(2012, 3, 1), 0, "working", 3, 10)]    # thời tiết 3 chưa từng có trong train
    res = B.run_backtest(recs, 2012)
    fb = exp_by_id(res)["full_static"]["n_fallback"]
    assert fb == 1
    assert exp_by_id(res)["hour_only_static"]["n_fallback"] == 0


def test_expanding_adjusted_factor_clamped_to_max_and_min():
    def with_jan(value):
        return synth(lambda d, h: value if (d.year == 2012 and d.month == 1) else 10)

    hi = exp_by_id(B.run_backtest(with_jan(1000), 2012))["full_expanding_adjusted"]["monthly"]
    assert hi[0]["factor"] == 1.0          # tháng 1: cửa sổ tháng 12/2011 khớp mô hình -> không hiệu chỉnh
    assert hi[1]["factor"] == 2.0          # tháng 2: thực tế >> dự báo -> kẹp ở 2.0

    lo = exp_by_id(B.run_backtest(with_jan(0), 2012))["full_expanding_adjusted"]["monthly"]
    assert lo[1]["factor"] == 0.5          # thực tế = 0 -> kẹp ở 0.5
    assert all(0.5 <= m["factor"] <= 2.0 for m in hi + lo)


def test_static_and_expanding_use_factor_one():
    res = B.run_backtest(synth(lambda d, h: 10 if d.year == 2011 else 1000), 2012)
    for eid in ["full_static", "full_expanding", "hour_only_static", "hour_only_expanding"]:
        assert all(m["factor"] == 1.0 for m in exp_by_id(res)[eid]["monthly"])


# ---------- real data (data/hour.csv) ----------

@pytest.fixture(scope="module")
def real():
    recs = B.load_uci_hour_csv(HOUR_CSV)
    return recs, B.run_backtest(recs)


def test_load_csv_maps_columns():
    recs = B.load_uci_hour_csv(HOUR_CSV)
    assert len(recs) == 17379
    first = recs[0]
    assert first == {"date": date(2011, 1, 1), "hour": 0, "day_group": "non_working",
                     "weather_key": 1, "total_cnt": 16}
    assert {r["day_group"] for r in recs} == {"working", "non_working"}


def test_real_data_experiment_order(real):
    _, res = real
    assert [e["id"] for e in res["experiments"]] == EXP_IDS
    assert res["test_year"] == 2012 and res["n_test"] == 8734


def test_real_data_confusion_totals_match_test_rows(real):
    recs, res = real
    n_2012 = sum(1 for r in recs if r["date"].year == 2012)
    assert n_2012 == res["n_test"] == 8734
    for e in res["experiments"]:
        conf = e["metrics"]["confusion"]
        assert sum(sum(row.values()) for row in conf.values()) == n_2012
        assert e["metrics"]["n"] == n_2012


def test_real_data_full_static_accuracy_and_thresholds(real):
    _, res = real
    st = exp_by_id(res)["full_static"]
    assert 0.68 <= st["metrics"]["accuracy"] <= 0.72
    assert st["monthly"][0]["th_low"] == 55 and st["monthly"][0]["th_high"] == 174


def test_real_data_adjusted_expanding_improves_high_recall(real):
    _, res = real
    e = exp_by_id(res)
    assert e["full_expanding_adjusted"]["metrics"]["per_level"]["high"]["recall"] > \
        e["full_static"]["metrics"]["per_level"]["high"]["recall"]
