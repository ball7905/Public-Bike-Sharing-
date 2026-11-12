"""Truy xuất dữ liệu lịch sử từ kho cho DSS (bước 2-3 của quy trình), rồi gọi mô hình trong dss.engine."""
from api.queries import V, q, where
from dss import backtest as B
from dss import engine as E

PERIOD_FILTERS = ("year", "season", "month")      # DSS chỉ lọc theo khoảng thời gian lịch sử


def period_only(filters: dict) -> dict:
    return {k: v for k, v in filters.items() if k in PERIOD_FILTERS}


def _weathers(cur):
    return [{"key": r["weather_key"], "name": r["weather_name"]}
            for r in q(cur, "SELECT weather_key, weather_name FROM dw.dim_weather ORDER BY weather_key")]


def _thresholds(cur, period, q_low, q_high):
    """Khảo sát phân phối lượt thuê theo giờ trong kỳ lịch sử -> ngưỡng phân loại."""
    E.validate_quantiles(q_low, q_high)
    qs = list(E.SURVEY_QUANTILES)
    w, a = where(period)
    s = q(cur, f"""SELECT COUNT(*)::int AS n_obs, AVG(total_cnt)::float8 AS mean,
                          STDDEV_SAMP(total_cnt)::float8 AS std, MIN(total_cnt)::int AS min, MAX(total_cnt)::int AS max,
                          percentile_cont(%s::float8[]) WITHIN GROUP (ORDER BY total_cnt) AS qs,
                          percentile_cont(%s::float8[]) WITHIN GROUP (ORDER BY total_cnt) AS th,
                          (SUM(casual_cnt)::float8 / NULLIF(SUM(total_cnt), 0)) AS casual_share
                   FROM {V} {w}""", [qs, [q_low, q_high], *a])[0]
    if not s["n_obs"]:
        raise ValueError("Không có dữ liệu lịch sử trong khoảng thời gian đã chọn")
    th = E.make_thresholds(s["th"][0], s["th"][1], q_low, q_high)
    return s, th


def thresholds(cur, filters, q_low=E.DEFAULT_Q_LOW, q_high=E.DEFAULT_Q_HIGH):
    period = period_only(filters)
    s, th = _thresholds(cur, period, q_low, q_high)
    w, a = where(period)
    share = q(cur, f"""SELECT AVG((total_cnt < %s)::int)::float8 AS low,
                              AVG((total_cnt BETWEEN %s AND %s)::int)::float8 AS medium,
                              AVG((total_cnt > %s)::int)::float8 AS high
                       FROM {V} {w}""", [th["low"], th["low"], th["high"], th["high"], *a])[0]
    return {
        "period": period,
        "distribution": {"n_obs": s["n_obs"], "mean": s["mean"], "std": s["std"], "min": s["min"], "max": s["max"],
                         "percentiles": [{"q": x, "value": v} for x, v in zip(E.SURVEY_QUANTILES, s["qs"])]},
        "thresholds": th,
        "observation_share": share,            # tỷ lệ giờ quan sát rơi vào từng mức
        "casual_share": s["casual_share"],     # tỷ lệ khách vãng lai chung của kỳ (mốc phân nhóm khách)
        "min_obs": E.MIN_OBS,
        "levels": [{"level": lv, "label": E.LEVEL_LABELS[lv], "recommendation": E.RECOMMENDATIONS[lv]} for lv in E.LEVELS],
    }


def plan(cur, filters, day_group, weather, q_low=E.DEFAULT_Q_LOW, q_high=E.DEFAULT_Q_HIGH, day_of_week=None):
    """Kế hoạch chuẩn bị 24 giờ cho tình huống sắp tới: loại ngày (hoặc một / nhiều thứ cụ thể) + thời tiết dự kiến.
    day_of_week: một thứ hoặc danh sách thứ (0 = Chủ nhật ... 6 = Thứ bảy, như nguồn); lấy các ngày thuộc các thứ đó,
    KHÔNG phải ngày lễ (ngày lễ dùng nhóm 'ngày nghỉ'); khi có thì thay cho day_group."""
    if day_group not in E.DAY_GROUPS:
        raise ValueError("day_group phải là working hoặc non_working")
    day_of_week = E.normalize_weekdays(day_of_week)
    weathers = {w["key"]: w for w in _weathers(cur)}
    if weather not in weathers:
        raise ValueError(f"weather phải thuộc {sorted(weathers)}")
    period = period_only(filters)
    s, th = _thresholds(cur, period, q_low, q_high)
    day_cond = ([("weekday", day_of_week), ("is_holiday", False)] if day_of_week is not None
                else [("is_working_day", day_group == "working")])
    w, a = where(period, [*day_cond, ("weather_key", weather)])
    rows = q(cur, f"""SELECT hour, COUNT(*)::int AS n_obs, AVG(total_cnt)::float8 AS avg_rentals,
                             AVG(casual_cnt)::float8 AS avg_casual, AVG(registered_cnt)::float8 AS avg_registered
                      FROM {V} {w} GROUP BY hour ORDER BY hour""", a)
    out = E.build_plan(rows, th, s["mean"], day_group, weathers[weather], casual_ref=s["casual_share"],
                       day_of_week=day_of_week)
    out["period"] = period
    return out


def matrix(cur, filters, q_low=E.DEFAULT_Q_LOW, q_high=E.DEFAULT_Q_HIGH):
    period = period_only(filters)
    s, th = _thresholds(cur, period, q_low, q_high)
    w, a = where(period)
    rows = q(cur, f"""SELECT hour, CASE WHEN is_working_day THEN 'working' ELSE 'non_working' END AS day_group,
                             weather_key, COUNT(*)::int AS n_obs, AVG(total_cnt)::float8 AS avg_rentals
                      FROM {V} {w} GROUP BY hour, is_working_day, weather_key""", a)
    out = E.build_matrix(rows, th, s["mean"], _weathers(cur))
    out["period"] = period
    return out


BACKTEST_YEAR = 2012      # năm kiểm định ngoài mẫu: huấn luyện trên các năm trước, kiểm tra trên năm này


def backtest(cur, q_low=E.DEFAULT_Q_LOW, q_high=E.DEFAULT_Q_HIGH):
    """Kiểm định ngoài mẫu: dự báo mức nhu cầu từng giờ của BACKTEST_YEAR chỉ dựa trên dữ liệu trước đó."""
    E.validate_quantiles(q_low, q_high)
    rows = q(cur, f"""SELECT full_date AS date, hour,
                             CASE WHEN is_working_day THEN 'working' ELSE 'non_working' END AS day_group,
                             weather_key, temp_c::float8 AS temp_c, total_cnt
                      FROM {V} ORDER BY full_date, hour""")
    records = [dict(r) for r in rows]
    return B.run_backtest(records, BACKTEST_YEAR, q_low, q_high)
