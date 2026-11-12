"""Backtest mô hình DSS trên dữ liệu lịch sử - thuần Python, không phụ thuộc CSDL.

Mục tiêu: đánh giá mô hình ngoài mẫu (out-of-sample). Mô hình được huấn luyện trên lịch sử,
dự báo MỨC ĐỘ nhu cầu (Thấp / Trung bình / Cao) cho từng giờ của năm kiểm thử, rồi so với mức thực tế.

Hai mô hình:
  - "full"      : nhóm theo giờ x loại ngày x thời tiết (giống engine.build_matrix)
  - "hour_only" : nhóm theo giờ
Ba lược đồ huấn luyện:
  - "static"             : huấn luyện một lần trên mọi năm trước năm kiểm thử
  - "expanding"          : huấn luyện lại đầu mỗi tháng, chỉ dùng dữ liệu trước ngày 1 của tháng đó
  - "expanding_adjusted" : như "expanding", thêm hệ số hiệu chỉnh mức f = tổng thực tế / tổng dự báo
                           trong 30 ngày trước đó, kẹp trong [0.5, 2.0]; ngưỡng phân loại không đổi
"""
import csv
import math
from datetime import date, timedelta

from . import engine

MODELS = ("full", "hour_only")
SCHEMES = ("static", "expanding", "expanding_adjusted")
MODEL_LABELS = {"full": "Mô hình DSS (giờ × loại ngày × thời tiết)", "hour_only": "Mô hình chỉ theo giờ"}
SCHEME_LABELS = {
    "static": "cố định đến {y}",
    "expanding": "mở rộng theo tháng",
    "expanding_adjusted": "mở rộng theo tháng + hiệu chỉnh mức",
}
FACTOR_MIN, FACTOR_MAX = 0.5, 2.0
ADJUST_WINDOW = timedelta(days=30)
RANK = {"low": 0, "medium": 1, "high": 2}


def quantile(sorted_values, q):
    """Phân vị nội suy tuyến tính, trùng với percentile_cont của PostgreSQL và mặc định của pandas.
    sorted_values phải đã sắp tăng dần. pos = q*(n-1), nội suy giữa phần tử sàn và phần tử trần.
    Trả về None nếu danh sách rỗng."""
    n = len(sorted_values)
    if n == 0:
        return None
    pos = q * (n - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return float(sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo))


def _key(rec, model):
    return (rec["hour"], rec["day_group"], rec["weather_key"]) if model == "full" else rec["hour"]


def _means(pairs):
    """pairs: iterable (khóa, giá trị) -> {khóa: trung bình}."""
    acc = {}
    for k, v in pairs:
        s, c = acc.get(k, (0, 0))
        acc[k] = (s + v, c + 1)
    return {k: s / c for k, (s, c) in acc.items()}


def fit(train, model, q_low=engine.DEFAULT_Q_LOW, q_high=engine.DEFAULT_Q_HIGH):
    """Huấn luyện: ngưỡng từ phân vị total_cnt của train; TB theo nhóm, TB theo giờ, TB toàn bộ."""
    if model not in MODELS:
        raise ValueError(f"Mô hình không hợp lệ: {model}")
    if not train:
        raise ValueError("Không có dữ liệu lịch sử để huấn luyện")
    totals = sorted(r["total_cnt"] for r in train)
    th = engine.make_thresholds(quantile(totals, q_low), quantile(totals, q_high), q_low, q_high)
    return {
        "model": model,
        "th": th,
        "group_means": _means((_key(r, model), r["total_cnt"]) for r in train),
        "hour_means": _means((r["hour"], r["total_cnt"]) for r in train),
        "overall_mean": sum(totals) / len(totals),
    }


def predict(fitted, rec):
    """Trả về (giá trị dự báo, có dùng phương án dự phòng không).
    Thứ tự: TB nhóm -> TB theo giờ -> TB toàn bộ."""
    g = fitted["group_means"].get(_key(rec, fitted["model"]))
    if g is not None:
        return g, False
    h = fitted["hour_means"].get(rec["hour"])
    if h is not None:
        return h, True
    return fitted["overall_mean"], True


def metrics(pairs, abs_errors=()):
    """pairs: [(mức thực tế, mức dự báo)]; abs_errors: [|dự báo đã hiệu chỉnh - thực tế|].
    Chỉ số không xác định (mẫu số 0) được tính là 0.0."""
    pairs = list(pairs)
    n = len(pairs)
    conf = {a: {p: 0 for p in engine.LEVELS} for a in engine.LEVELS}
    for a, p in pairs:
        conf[a][p] += 1

    per_level = {}
    for lv in engine.LEVELS:
        tp = conf[lv][lv]
        support = sum(conf[lv].values())
        predicted = sum(conf[a][lv] for a in engine.LEVELS)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_level[lv] = {"precision": precision, "recall": recall, "f1": f1, "support": support}

    correct = sum(conf[lv][lv] for lv in engine.LEVELS)
    under = sum(1 for a, p in pairs if RANK[a] > RANK[p])
    over = sum(1 for a, p in pairs if RANK[p] > RANK[a])
    abs_errors = list(abs_errors)
    return {
        "n": n,
        "accuracy": correct / n if n else 0.0,
        "macro_f1": sum(per_level[lv]["f1"] for lv in engine.LEVELS) / len(engine.LEVELS),
        "macro_recall": sum(per_level[lv]["recall"] for lv in engine.LEVELS) / len(engine.LEVELS),
        "per_level": per_level,
        "confusion": conf,
        "under_prepared_rate": under / n if n else 0.0,
        "over_prepared_rate": over / n if n else 0.0,
        "missed_high": sum(1 for a, p in pairs if a == "high" and p != "high"),   # số giờ CAO bị dự báo thấp hơn
        "mae": sum(abs_errors) / len(abs_errors) if abs_errors else 0.0,
    }


def _evaluate(fitted, test_recs, factor):
    """Dự báo các bản ghi kiểm thử. Trả về (pairs, sai số tuyệt đối, số lần dùng phương án dự phòng)."""
    pairs, errs, n_fb = [], [], 0
    th = fitted["th"]
    for r in test_recs:
        base, fb = predict(fitted, r)
        pv = base * factor
        n_fb += fb
        pairs.append((engine.classify(r["total_cnt"], th), engine.classify(pv, th)))
        errs.append(abs(pv - r["total_cnt"]))
    return pairs, errs, n_fb


def _level_factor(fitted, records, start):
    """Hệ số hiệu chỉnh mức của tháng bắt đầu từ `start`, tính trên 30 ngày trước start."""
    win = [r for r in records if start - ADJUST_WINDOW <= r["date"] < start]
    if not win:
        return 1.0
    pred_sum = sum(predict(fitted, r)[0] for r in win)
    if pred_sum == 0:
        return 1.0
    act_sum = sum(r["total_cnt"] for r in win)
    return min(max(act_sum / pred_sum, FACTOR_MIN), FACTOR_MAX)


def _run_experiment(records, test, train_static, test_year, model, scheme, q_low, q_high):
    static_fit = fit(train_static, model, q_low, q_high) if scheme == "static" else None
    all_pairs, all_errs, n_fb, monthly = [], [], 0, []
    for m in range(1, 13):
        start = date(test_year, m, 1)
        test_m = [r for r in test if r["date"].month == m]
        if scheme == "static":
            fitted = static_fit
        else:
            fitted = fit([r for r in records if r["date"] < start], model, q_low, q_high)
        factor = _level_factor(fitted, records, start) if scheme == "expanding_adjusted" else 1.0
        pairs, errs, fb = _evaluate(fitted, test_m, factor)
        mm = metrics(pairs, errs)
        present = [lv for lv in engine.LEVELS if mm["per_level"][lv]["support"]]
        macro_recall = (sum(mm["per_level"][lv]["recall"] for lv in present) / len(present)) if present else None
        monthly.append({
            "month": m, "n": mm["n"], "accuracy": mm["accuracy"],
            "macro_recall": macro_recall,
            "factor": factor, "th_low": fitted["th"]["low"], "th_high": fitted["th"]["high"],
        })
        all_pairs += pairs
        all_errs += errs
        n_fb += fb
    return {
        "id": f"{model}_{scheme}", "model": model, "scheme": scheme,
        "label": f"{MODEL_LABELS[model]} · {SCHEME_LABELS[scheme].format(y=test_year - 1)}",
        "metrics": metrics(all_pairs, all_errs), "n_fallback": n_fb, "monthly": monthly,
    }


def run_backtest(records, test_year=2012, q_low=engine.DEFAULT_Q_LOW, q_high=engine.DEFAULT_Q_HIGH):
    """Chạy 6 thí nghiệm: mô hình (full, hour_only) x lược đồ (static, expanding, expanding_adjusted)."""
    engine.validate_quantiles(q_low, q_high)
    train_static = [r for r in records if r["date"].year < test_year]
    if not train_static:
        raise ValueError(f"Không có dữ liệu lịch sử trước năm {test_year} để huấn luyện")
    test = [r for r in records if r["date"].year == test_year]
    if not test:
        raise ValueError(f"Không có dữ liệu kiểm thử trong năm {test_year}")
    experiments = [
        _run_experiment(records, test, train_static, test_year, model, scheme, q_low, q_high)
        for model in MODELS for scheme in SCHEMES
    ]
    return {"test_year": test_year, "n_train_static": len(train_static), "n_test": len(test),
            "q_low": q_low, "q_high": q_high, "experiments": experiments}


def load_uci_hour_csv(path):
    """Đọc data/hour.csv (UCI Bike Sharing) thành bản ghi chuẩn của backtest."""
    records = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append({
                "date": date.fromisoformat(row["dteday"]),
                "hour": int(row["hr"]),
                "day_group": "working" if int(row["workingday"]) == 1 else "non_working",
                "weather_key": int(row["weathersit"]),
                "total_cnt": int(row["cnt"]),
            })
    return records
