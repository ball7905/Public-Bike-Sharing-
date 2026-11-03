"""Đối chiếu DW với dữ liệu nguồn -> docs/validation_report.md (dùng trong báo cáo)."""
import logging
import pandas as pd
from config import REPORT_DIR

log = logging.getLogger(__name__)


def q(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])


def validate(conn, hour: pd.DataFrame, day: pd.DataFrame) -> bool:
    checks = []

    def add(name, expected, actual):
        checks.append((name, expected, actual, expected == actual))

    fact = q(conn, "SELECT COUNT(*)::int n, SUM(total_cnt)::bigint t, SUM(casual_cnt)::bigint c, SUM(registered_cnt)::bigint r FROM dw.fact_rentals").iloc[0]
    add("Số dòng fact = số dòng hour.csv", len(hour), int(fact.n))
    add("Tổng cnt (fact vs hour.csv)", int(hour.cnt.sum()), int(fact.t))
    add("Tổng casual (fact vs hour.csv)", int(hour.casual.sum()), int(fact.c))
    add("Tổng registered (fact vs hour.csv)", int(hour.registered.sum()), int(fact.r))
    add("Tổng cnt (fact vs day.csv)", int(day.cnt.sum()), int(fact.t))
    add("Số ngày dim_date = số dòng day.csv", len(day), int(q(conn, "SELECT COUNT(*) n FROM dw.dim_date").n[0]))
    add("Số dòng dim_hour", 24, int(q(conn, "SELECT COUNT(*) n FROM dw.dim_hour").n[0]))

    orphan = q(conn, """SELECT COUNT(*) n FROM dw.fact_rentals f
                        LEFT JOIN dw.dim_date d USING (date_key)
                        LEFT JOIN dw.dim_hour h USING (hour_key)
                        LEFT JOIN dw.dim_weather w USING (weather_key)
                        WHERE d.date_key IS NULL OR h.hour_key IS NULL OR w.weather_key IS NULL""").n[0]
    add("Số dòng fact mồ côi (vi phạm FK)", 0, int(orphan))
    bad = q(conn, "SELECT COUNT(*) n FROM dw.fact_rentals WHERE total_cnt <> casual_cnt + registered_cnt").n[0]
    add("Số dòng vi phạm cnt = casual + registered", 0, int(bad))

    dw_day = q(conn, "SELECT d.full_date::text AS dteday, SUM(f.total_cnt)::bigint AS dw_cnt "
                     "FROM dw.fact_rentals f JOIN dw.dim_date d USING (date_key) GROUP BY 1")
    m = day[["dteday", "cnt"]].merge(dw_day, on="dteday", how="outer")
    add("Số ngày có tổng cnt lệch day.csv", 0, int((m["cnt"] != m["dw_cnt"]).sum()))

    dq = q(conn, """SELECT (SELECT SUM(hours_recorded) FROM dw.dim_date)::int AS hours,
                           (SELECT COUNT(*) FROM dw.dim_date WHERE NOT is_complete_day)::int AS partial_days,
                           (SELECT COUNT(*) FROM dw.fact_rentals WHERE humidity_pct IS NULL)::int AS hum_null""").iloc[0]
    n_partial = int((hour.groupby("dteday").size() < 24).sum())
    add("Tổng hours_recorded (dim_date) = số dòng hour.csv", len(hour), int(dq.hours))
    add("Số ngày thiếu giờ (is_complete_day = false)", n_partial, int(dq.partial_days))
    add("Số dòng humidity_pct NULL = số dòng hum = 0 trong nguồn", int((hour.hum == 0).sum()), int(dq.hum_null))

    n_days = len(day)
    expected_hours = n_days * 24
    missing_hours = expected_hours - len(hour)
    per_day = hour.groupby("dteday").size()
    worst = per_day[per_day <= 12].sort_values()
    hum0_days = sorted(hour.loc[hour.hum == 0, "dteday"].unique())
    n_wind0 = int((hour.windspeed == 0).sum())

    lines = ["# Báo cáo đối chiếu ETL", "",
             "| Kiểm tra | Kỳ vọng | Thực tế | Kết quả |", "|---|---:|---:|:---:|"]
    for name, e, a, ok in checks:
        lines.append(f"| {name} | {e:,} | {a:,} | {'PASS' if ok else 'FAIL'} |")
    lines += ["", "## Ghi chú chất lượng dữ liệu", "",
              f"- Số giờ lý thuyết ({n_days} ngày x 24) = {expected_hours:,}; fact có {len(hour):,} dòng, "
              f"tức **{missing_hours} giờ không có bản ghi** trong nguồn. "
              "ETL không tự thêm các dòng này; khi tính trung bình theo giờ cần lưu ý chúng bị bỏ qua.",
              f"- **{n_partial} ngày thiếu giờ** (`dim_date.is_complete_day = false`, số giờ ở `hours_recorded`). "
              "Ngày thiếu nhiều nhất: " + ", ".join(f"{d} ({n} giờ)" for d, n in worst.items()) + ". "
              "Khi tính trung bình lượt thuê / ngày nên lọc `is_complete_day` để tránh bị kéo xuống.",
              f"- **{int((hour.hum == 0).sum())} dòng có hum = 0** (ngày {', '.join(hum0_days)}): độ ẩm 0% không có thật, "
              "coi là lỗi cảm biến -> `humidity_pct = NULL` (giữ `hum_norm` gốc để truy vết). Lượt thuê của các dòng này vẫn giữ.",
              f"- **{n_wind0:,} dòng ({n_wind0 / len(hour):.1%}) có windspeed = 0**: tỷ lệ cao bất thường, nhiều khả năng là "
              "thiếu dữ liệu chứ không phải lặng gió. ETL giữ nguyên giá trị; cần thận trọng khi phân tích theo tốc độ gió.",
              "- Thuộc tính thời tiết được lưu cả dạng chuẩn hóa gốc (`*_norm`) và dạng quy đổi "
              "(temp x 41, atemp x 50, hum x 100, windspeed x 67 theo Readme UCI)."]
    (REPORT_DIR / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for name, e, a, ok in checks:
        (log.info if ok else log.error)("%s: kỳ vọng=%s, thực tế=%s -> %s", name, e, a, "PASS" if ok else "FAIL")
    return all(c[3] for c in checks)
