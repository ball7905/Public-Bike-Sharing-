"""Các truy vấn OLAP/KPI. Mọi tên cột/biểu thức đi vào SQL đều từ whitelist; giá trị luôn tham số hóa."""

# tham số bộ lọc -> (cột trong v_rentals_flat, kiểu dữ liệu)
FILTERS = {
    "year": ("year", int),
    "season": ("season", int),
    "month": ("month", int),
    "weekday": ("weekday", int),
    "weather": ("weather_key", int),
    "day_type": ("day_type", str),
    "time_band": ("time_band", str),
}

# chiều phân tích cho pivot: tên -> (biểu thức nhãn, cột sắp xếp)
DIMS = {
    "year": ("year::text", "year"),
    "season": ("season_name", "season"),
    "month": ("month_name", "month"),
    "weekday": ("weekday_name", "weekday"),
    "hour": ("hour_label", "hour"),
    "time_band": ("time_band", "hour"),
    "weather": ("weather_name", "weather_key"),
    "day_type": ("day_type", "CASE day_type WHEN 'Working day' THEN 1 WHEN 'Weekend' THEN 2 ELSE 3 END"),
}

LEVELS = ["year", "quarter", "month", "day", "hour"]
V = "dw.v_rentals_flat"


def parse_filters(raw: dict) -> dict:
    """raw: {tên: 'a,b,c' | None} -> {tên: [giá trị đã ép kiểu]}"""
    out = {}
    for name, text in raw.items():
        if not text:
            continue
        _, typ = FILTERS[name]
        try:
            out[name] = [typ(x.strip()) for x in text.split(",") if x.strip()]
        except ValueError:
            raise ValueError(f"Giá trị không hợp lệ cho '{name}': {text}")
    return out


def where(filters: dict, extra=()):
    conds, args = [], []
    for name, vals in filters.items():
        conds.append(f"{FILTERS[name][0]} = ANY(%s)")
        args.append(vals)
    for col, val in extra:               # col do code truyền vào, không phải input người dùng
        conds.append(f"{col} = ANY(%s)" if isinstance(val, (list, tuple)) else f"{col} = %s")
        args.append(list(val) if isinstance(val, (list, tuple)) else val)
    return ("WHERE " + " AND ".join(conds)) if conds else "", args


def q(cur, sql, args=()):
    cur.execute(sql, args)
    return cur.fetchall()


def filter_options(cur):
    return {
        "year": [{"value": r["year"], "label": str(r["year"])} for r in q(cur, "SELECT DISTINCT year FROM dw.dim_date ORDER BY 1")],
        "season": [{"value": r["season"], "label": r["season_name"]} for r in q(cur, "SELECT DISTINCT season, season_name FROM dw.dim_date ORDER BY 1")],
        "weather": [{"value": r["weather_key"], "label": r["weather_name"]} for r in q(cur, "SELECT weather_key, weather_name FROM dw.dim_weather ORDER BY 1")],
        "day_type": [{"value": v, "label": v} for v in ("Working day", "Weekend", "Holiday")],
        "time_band": [{"value": r["time_band"], "label": r["time_band"]} for r in q(cur, "SELECT time_band FROM dw.dim_hour GROUP BY time_band ORDER BY MIN(hour_key)")],
    }


def kpis(cur, filters):
    w, a = where(filters)
    t = q(cur, f"""SELECT COALESCE(SUM(total_cnt),0)::bigint AS total, COALESCE(SUM(casual_cnt),0)::bigint AS casual,
                          COALESCE(SUM(registered_cnt),0)::bigint AS registered,
                          AVG(total_cnt)::float8 AS avg_hourly, COUNT(*)::int AS n_hours,
                          COUNT(DISTINCT full_date)::int AS n_days FROM {V} {w}""", a)[0]
    hours = q(cur, f"SELECT hour, AVG(total_cnt)::float8 AS avg_rentals FROM {V} {w} GROUP BY hour ORDER BY avg_rentals DESC", a)
    days = {r["is_working_day"]: r["avg_daily"] for r in q(
        cur, f"""SELECT is_working_day, (SUM(total_cnt)::float8 / COUNT(DISTINCT full_date)) AS avg_daily
                 FROM {V} {w} GROUP BY is_working_day""", a)}
    tot = t["total"]
    return {
        "total_rentals": tot,
        "avg_hourly_rentals": t["avg_hourly"],
        "peak_hour": {"hour": hours[0]["hour"], "avg_rentals": hours[0]["avg_rentals"]} if hours else None,
        "lowest_hour": {"hour": hours[-1]["hour"], "avg_rentals": hours[-1]["avg_rentals"]} if hours else None,
        "registered_ratio": (t["registered"] / tot) if tot else None,
        "casual_ratio": (t["casual"] / tot) if tot else None,
        "working_day_avg_daily": days.get(True),
        "non_working_day_avg_daily": days.get(False),
        "n_hours": t["n_hours"], "n_days": t["n_days"],
    }


def drill(cur, filters, level, year=None, quarter=None, month=None, day=None):
    """Roll-up/Drill-down: year -> quarter -> month -> day -> hour."""
    if level not in LEVELS:
        raise ValueError("level không hợp lệ")
    extra = []
    need = {"year": [], "quarter": ["year"], "month": ["year"], "day": ["year", "month"], "hour": ["day"]}[level]
    given = {"year": year, "quarter": quarter, "month": month, "day": day}
    for n in need:
        if given[n] is None:
            raise ValueError(f"level={level} cần tham số {n}")
    if year is not None and level != "hour":
        extra.append(("year", year))
    if quarter is not None and level in ("month", "day"):
        extra.append(("quarter", quarter))
    if month is not None and level in ("day",):
        extra.append(("month", month))
    if level == "hour":
        extra.append(("full_date", day))
    select, group, order = {
        "year": ("year AS key, year::text AS label", "year", "year"),
        "quarter": ("quarter AS key, 'Q' || quarter AS label", "quarter", "quarter"),
        "month": ("month AS key, month_name AS label", "month, month_name", "month"),
        "day": ("full_date::text AS key, EXTRACT(day FROM full_date)::int::text AS label", "full_date", "full_date"),
        "hour": ("hour AS key, lpad(hour::text, 2, '0') || 'h' AS label", "hour", "hour"),
    }[level]
    w, a = where(filters, extra)
    return q(cur, f"""SELECT {select}, SUM(total_cnt)::bigint AS total, SUM(casual_cnt)::bigint AS casual,
                             SUM(registered_cnt)::bigint AS registered, AVG(total_cnt)::float8 AS avg_hourly
                      FROM {V} {w} GROUP BY {group} ORDER BY {order}""", a)


def hourly_profile(cur, filters):
    w, a = where(filters)
    return q(cur, f"""SELECT hour,
                             AVG(total_cnt)::float8 AS avg_all,
                             AVG(total_cnt) FILTER (WHERE is_working_day)::float8 AS avg_working,
                             AVG(total_cnt) FILTER (WHERE NOT is_working_day)::float8 AS avg_non_working
                      FROM {V} {w} GROUP BY hour ORDER BY hour""", a)


def by_weather(cur, filters):
    w, a = where(filters)
    return q(cur, f"""SELECT weather_key AS key, weather_name AS label, COUNT(*)::int AS n_hours,
                             SUM(total_cnt)::bigint AS total, AVG(total_cnt)::float8 AS avg_hourly
                      FROM {V} {w} GROUP BY weather_key, weather_name ORDER BY weather_key""", a)


def by_day_type(cur, filters):
    w, a = where(filters)
    return q(cur, f"""SELECT day_type AS label, COUNT(DISTINCT full_date)::int AS n_days,
                             SUM(total_cnt)::bigint AS total,
                             (SUM(total_cnt)::float8 / COUNT(DISTINCT full_date)) AS avg_daily,
                             AVG(total_cnt)::float8 AS avg_hourly
                      FROM {V} {w} GROUP BY day_type
                      ORDER BY CASE day_type WHEN 'Working day' THEN 1 WHEN 'Weekend' THEN 2 ELSE 3 END""", a)


def users(cur, filters, by):
    expr = {"hour": ("hour", "lpad(hour::text,2,'0') || 'h'"),
            "month": ("year, month", "to_char(full_date, 'YYYY-MM')"),
            "weekday": ("weekday", "weekday_name")}[by]
    order, label = expr
    w, a = where(filters)
    group = {"hour": "hour", "month": "year, month, to_char(full_date, 'YYYY-MM')", "weekday": "weekday, weekday_name"}[by]
    return q(cur, f"""SELECT {label} AS label, SUM(casual_cnt)::bigint AS casual, SUM(registered_cnt)::bigint AS registered
                      FROM {V} {w} GROUP BY {group} ORDER BY {order}""", a)


# FR06 / Nhóm 2: ảnh hưởng nhiệt độ, độ ẩm. Tên -> (biểu thức khoảng, độ rộng, khoảng cuối gộp, đơn vị)
CLIMATE = {
    "temp": ("LEAST(FLOOR(temp_c / 5) * 5, 35)", 5, 35, "°C"),
    "humidity": ("LEAST(FLOOR(humidity_pct / 10) * 10, 90)", 10, 90, "%"),
}
CLIMATE_MIN_OBS = 30
CORR_VARS = {"temp": "temp_c", "atemp": "atemp_c", "humidity": "humidity_pct", "windspeed": "windspeed_kmh"}


def climate(cur, filters, by):
    """Lượt thuê TB theo khoảng nhiệt độ / độ ẩm + hệ số tương quan Pearson (mức giờ và mức ngày)."""
    if by not in CLIMATE:
        raise ValueError("by phải là temp hoặc humidity")
    expr, width, last, unit = CLIMATE[by]
    w, a = where(filters)
    # humidity_pct = NULL (lỗi cảm biến hum = 0) phải loại ra: LEAST(NULL, 90) trả về 90 trong PostgreSQL
    col = CORR_VARS["temp" if by == "temp" else "humidity"]
    wb = f"{w} AND {col} IS NOT NULL" if w else f"WHERE {col} IS NOT NULL"
    rows = q(cur, f"""SELECT {expr}::int AS lo, COUNT(*)::int AS n_hours,
                             AVG(total_cnt)::float8 AS avg_total, AVG(casual_cnt)::float8 AS avg_casual,
                             AVG(registered_cnt)::float8 AS avg_registered
                      FROM {V} {wb} GROUP BY 1 ORDER BY 1""", a)
    for r in rows:
        r["label"] = f"≥{r['lo']}{unit}" if (by == "temp" and r["lo"] == last) else f"{r['lo']}–{r['lo'] + width}{unit}"
        r["reliable"] = r["n_hours"] >= CLIMATE_MIN_OBS
    hourly = ", ".join(f"corr(total_cnt, {c})::float8 AS {k}" for k, c in CORR_VARS.items())
    daily_avg = ", ".join(f"AVG({c}) AS {c}" for c in CORR_VARS.values())
    daily = ", ".join(f"corr(total, {c})::float8 AS {k}" for k, c in CORR_VARS.items())
    corr_h = q(cur, f"SELECT {hourly}, COUNT(*)::int AS n FROM {V} {w}", a)[0]
    corr_d = q(cur, f"""SELECT {daily}, COUNT(*)::int AS n FROM (
                            SELECT full_date, SUM(total_cnt) AS total, {daily_avg} FROM {V} {w} GROUP BY full_date) d""", a)[0]
    return {"by": by, "unit": unit, "min_obs": CLIMATE_MIN_OBS, "bins": rows,
            "correlation": {"hourly": corr_h, "daily": corr_d}}


def pivot(cur, filters, row, col, measure):
    if row not in DIMS or col not in DIMS or row == col:
        raise ValueError("row/col không hợp lệ hoặc trùng nhau")
    if measure not in ("total", "avg_hourly"):
        raise ValueError("measure phải là total hoặc avg_hourly")
    rl, rs = DIMS[row]
    cl, cs = DIMS[col]
    agg = "SUM(total_cnt)::float8" if measure == "total" else "AVG(total_cnt)::float8"
    w, a = where(filters)
    rows = q(cur, f"""SELECT {rl} AS r, MIN({rs}) AS r_ord, {cl} AS c, MIN({cs}) AS c_ord, {agg} AS value
                      FROM {V} {w} GROUP BY {rl}, {cl}""", a)
    r_order, c_order = {}, {}
    for x in rows:
        r_order[x["r"]] = min(r_order.get(x["r"], x["r_ord"]), x["r_ord"])
        c_order[x["c"]] = min(c_order.get(x["c"], x["c_ord"]), x["c_ord"])
    return {
        "rows": sorted(r_order, key=r_order.get),
        "cols": sorted(c_order, key=c_order.get),
        "cells": [{"r": x["r"], "c": x["c"], "value": x["value"]} for x in rows],
    }
