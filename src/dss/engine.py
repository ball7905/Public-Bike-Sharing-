"""Mô hình ra quyết định của DSS - thuần Python, không phụ thuộc CSDL (kiểm thử độc lập, NFR07).

Quy trình (mục 2.5 của đề tài):
  1. Người dùng chọn khoảng thời gian lịch sử (năm / mùa / tháng).
  2. Truy xuất dữ liệu lịch sử từ kho (api/dss_queries.py).
  3. Tính số lượt thuê trung bình theo nhóm: giờ x loại ngày (làm việc / nghỉ) x thời tiết.
  4. Phân loại nhóm thành Thấp / Trung bình / Cao bằng ngưỡng lấy từ phân phối dữ liệu.
  5. Sinh khuyến nghị và cảnh báo tương ứng.

Ngưỡng phân loại: phân vị của lượt thuê theo giờ (total_cnt của từng bản ghi giờ) trong kỳ lịch sử
được chọn. Mặc định P33,3 và P66,7 (tam phân vị) => mỗi mức chiếm ~1/3 số giờ quan sát.
  Thấp       : TB nhóm <  ngưỡng thấp
  Trung bình : ngưỡng thấp <= TB nhóm <= ngưỡng cao
  Cao        : TB nhóm >  ngưỡng cao
Hệ thống chỉ đưa ra MỨC ĐỘ chuẩn bị, không tính số xe cụ thể (nguồn không có số xe sẵn sàng / trạm).

Nhóm khách (bổ sung): xe dùng chung cho cả hai nhóm nên MỨC chuẩn bị vẫn dựa trên tổng lượt thuê;
thành phần khách quyết định LOẠI hỗ trợ. Tỷ lệ vãng lai của một giờ / khung giờ được so với tỷ lệ
vãng lai chung của kỳ lịch sử (s, ~18,8% trên toàn bộ dữ liệu):
  Nhiều khách vãng lai   : tỷ lệ >= 1,5 x s
  Chủ yếu khách đăng ký  : tỷ lệ <= 0,75 x s
  Hỗn hợp                : còn lại
"""

DEFAULT_Q_LOW = 1 / 3
DEFAULT_Q_HIGH = 2 / 3
MIN_OBS = 30          # nhóm có ít hơn số giờ quan sát này bị gắn cờ "độ tin cậy thấp"
SURVEY_QUANTILES = (0.10, 0.25, DEFAULT_Q_LOW, 0.50, DEFAULT_Q_HIGH, 0.75, 0.90)

LEVELS = ("low", "medium", "high")
LEVEL_LABELS = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}
RECOMMENDATIONS = {
    "low": "Duy trì mức chuẩn bị cơ bản. Có thể tận dụng khung giờ này để bảo trì, sửa chữa xe.",
    "medium": "Theo dõi nhu cầu và duy trì nguồn lực phù hợp, sẵn sàng bổ sung nếu nhu cầu tăng.",
    "high": "Ưu tiên chuẩn bị thêm xe và nguồn lực phục vụ (nhân sự điều phối, hỗ trợ) trước khung giờ này.",
}
NO_DATA_RECOMMENDATION = "Không có dữ liệu lịch sử cho tình huống này - không đủ căn cứ để khuyến nghị."

DAY_GROUPS = {"working": "Ngày làm việc", "non_working": "Ngày nghỉ (cuối tuần / lễ)"}
# Thứ trong tuần theo mã nguồn UCI (0 = Chủ nhật). Chọn một thứ = các ngày cùng thứ, không phải ngày lễ.
WEEKDAY_LABELS = {0: "Chủ nhật", 1: "Thứ hai", 2: "Thứ ba", 3: "Thứ tư", 4: "Thứ năm", 5: "Thứ sáu", 6: "Thứ bảy"}
WEEK_ORDER = (1, 2, 3, 4, 5, 6, 0)          # hiển thị thứ hai -> chủ nhật


def normalize_weekdays(day_of_week):
    """None | int | list[int] -> None hoặc danh sách thứ không trùng, theo thứ tự T2 -> CN."""
    if day_of_week is None:
        return None
    vals = {day_of_week} if isinstance(day_of_week, int) else set(day_of_week)
    if not vals or not vals <= set(WEEKDAY_LABELS):
        raise ValueError("day_of_week phải gồm các giá trị từ 0 (Chủ nhật) đến 6 (Thứ bảy)")
    return [d for d in WEEK_ORDER if d in vals]


def weekdays_label(days: list) -> str:
    return " + ".join(WEEKDAY_LABELS[d] for d in days)

CASUAL_HEAVY_FACTOR = 1.5       # tỷ lệ vãng lai >= 1,5 x tỷ lệ chung -> nhiều khách vãng lai
REGISTERED_HEAVY_FACTOR = 0.75  # tỷ lệ vãng lai <= 0,75 x tỷ lệ chung -> chủ yếu khách đăng ký
SEGMENTS = ("registered", "mixed", "casual")
SEGMENT_LABELS = {"registered": "Chủ yếu khách đăng ký", "mixed": "Khách hỗn hợp", "casual": "Nhiều khách vãng lai"}
SEGMENT_ADVICE = {
    "registered": "Khách chủ yếu là người đăng ký (đi làm, đi học): ưu tiên có đủ xe sẵn sàng đúng giờ, điều phối xe kịp thời.",
    "mixed": "Khách hỗn hợp: vừa đảm bảo đủ xe vừa bố trí người hỗ trợ khách mới khi cần.",
    "casual": "Nhiều khách vãng lai (đi chơi, tham quan): bố trí nhân sự hướng dẫn thuê xe, hỗ trợ thanh toán và giải đáp cho khách mới.",
}


def segment(casual_share, reference):
    """Phân nhóm khách theo tỷ lệ vãng lai so với tỷ lệ chung của kỳ lịch sử. None khi thiếu dữ liệu."""
    if casual_share is None or not reference:
        return None
    if casual_share >= CASUAL_HEAVY_FACTOR * reference:
        return "casual"
    if casual_share <= REGISTERED_HEAVY_FACTOR * reference:
        return "registered"
    return "mixed"


def validate_quantiles(q_low: float, q_high: float):
    if not (0 < q_low < q_high < 1):
        raise ValueError("Phân vị ngưỡng phải thỏa 0 < q_low < q_high < 1")


def make_thresholds(low: float, high: float, q_low: float, q_high: float) -> dict:
    if low is None or high is None:
        raise ValueError("Không có dữ liệu lịch sử trong khoảng thời gian đã chọn")
    if low > high:
        raise ValueError("Ngưỡng thấp lớn hơn ngưỡng cao")
    return {"low": float(low), "high": float(high), "q_low": q_low, "q_high": q_high,
            "method": f"Phân vị P{q_low * 100:.1f} / P{q_high * 100:.1f} của lượt thuê theo giờ trong kỳ lịch sử"}


def classify(value, th: dict):
    """Trả về 'low' | 'medium' | 'high', hoặc None khi không có dữ liệu."""
    if value is None:
        return None
    if value < th["low"]:
        return "low"
    if value > th["high"]:
        return "high"
    return "medium"


def assess(avg, n_obs: int, th: dict, overall_mean: float) -> dict:
    """Đánh giá 1 nhóm (giờ x loại ngày x thời tiết)."""
    level = classify(avg if n_obs else None, th)
    return {
        "avg_rentals": avg if n_obs else None,
        "n_obs": n_obs,
        "level": level,
        "level_label": LEVEL_LABELS.get(level, "Không có dữ liệu"),
        "recommendation": RECOMMENDATIONS.get(level, NO_DATA_RECOMMENDATION),
        "reliable": n_obs >= MIN_OBS,
        "ratio_to_mean": (avg / overall_mean) if (n_obs and overall_mean) else None,
    }


def high_windows(hours: list, casual_ref=None) -> list:
    """Gộp các giờ liên tiếp ở mức Cao thành khung cảnh báo. hours: 24 phần tử đã sắp theo giờ."""
    windows, cur = [], None
    for h in hours:
        if h["level"] == "high":
            if cur and h["hour"] == cur["end_hour"] + 1:
                cur["end_hour"] = h["hour"]
                cur["hours"].append(h)
            else:
                cur = {"start_hour": h["hour"], "end_hour": h["hour"], "hours": [h]}
                windows.append(cur)
        else:
            cur = None
    out = []
    for w in windows:
        peak = max(w["hours"], key=lambda x: x["avg_rentals"])
        # tỷ lệ vãng lai của cả khung = tổng lượt vãng lai TB / tổng lượt TB (trọng số theo lượt thuê)
        cas = sum(x.get("avg_casual") or 0 for x in w["hours"])
        tot = sum(x["avg_rentals"] or 0 for x in w["hours"])
        share = cas / tot if tot else None
        seg = segment(share, casual_ref)
        out.append({
            "casual_share": share,
            "segment": seg,
            "segment_label": SEGMENT_LABELS.get(seg),
            "segment_advice": SEGMENT_ADVICE.get(seg),
            "start_hour": w["start_hour"],
            "end_hour": w["end_hour"],
            "label": f"{w['start_hour']:02d}:00-{w['end_hour']:02d}:59",
            "peak_hour": peak["hour"],
            "peak_avg": peak["avg_rentals"],
            "prepare_before": f"{(w['start_hour'] - 1) % 24:02d}:00",
            "low_reliability": any(not x["reliable"] for x in w["hours"]),
            "message": (f"Nhu cầu dự kiến CAO trong khung {w['start_hour']:02d}:00-{w['end_hour']:02d}:59 "
                        f"(đỉnh {peak['hour']:02d}h, TB {peak['avg_rentals']:.0f} lượt/giờ). "
                        f"Hoàn tất chuẩn bị thêm xe và nhân sự trước {(w['start_hour'] - 1) % 24:02d}:00."
                        + (f" {SEGMENT_ADVICE[seg]}" if seg else "")),
        })
    return out


def build_plan(rows: list, th: dict, overall_mean: float, day_group: str, weather: dict, casual_ref=None,
               day_of_week=None) -> dict:
    """rows: [{hour, n_obs, avg_rentals, avg_casual, avg_registered}] của tình huống đã chọn (có thể thiếu giờ).
    casual_ref: tỷ lệ khách vãng lai chung của kỳ lịch sử (để phân nhóm khách); None thì bỏ qua phân nhóm.
    day_of_week: None, một thứ hoặc danh sách thứ (0 = Chủ nhật) khi người dùng chọn thứ cụ thể."""
    days = normalize_weekdays(day_of_week)
    by_hour = {r["hour"]: r for r in rows}
    hours = []
    for h in range(24):
        r = by_hour.get(h, {})
        n = int(r.get("n_obs") or 0)
        item = {"hour": h, "label": f"{h:02d}:00-{h:02d}:59", **assess(r.get("avg_rentals"), n, th, overall_mean)}
        tot = (r.get("avg_casual") or 0) + (r.get("avg_registered") or 0)
        item["avg_casual"] = r.get("avg_casual") if n else None
        item["avg_registered"] = r.get("avg_registered") if n else None
        item["registered_share"] = (r["avg_registered"] / tot) if n and tot else None
        item["casual_share"] = (r["avg_casual"] / tot) if n and tot else None
        seg = segment(item["casual_share"], casual_ref)
        item["segment"], item["segment_label"] = seg, SEGMENT_LABELS.get(seg)
        hours.append(item)
    # thành phần khách của cả tình huống (trọng số theo lượt thuê)
    cas_all = sum(x["avg_casual"] or 0 for x in hours)
    tot_all = sum(x["avg_rentals"] or 0 for x in hours)
    scen_share = cas_all / tot_all if tot_all else None

    counts = {lv: sum(1 for x in hours if x["level"] == lv) for lv in LEVELS}
    counts["no_data"] = sum(1 for x in hours if x["level"] is None)
    priority = sorted((x for x in hours if x["level"] == "high"), key=lambda x: -x["avg_rentals"])
    has_data = [x for x in hours if x["level"] is not None]
    notes = []
    if any(x["level"] and not x["reliable"] for x in hours):
        notes.append(f"Một số giờ có ít hơn {MIN_OBS} giờ quan sát lịch sử - kết quả chỉ mang tính tham khảo.")
    if counts["no_data"]:
        notes.append(f"{counts['no_data']} giờ không có dữ liệu lịch sử cho tình huống này.")
    return {
        "scenario": {
            # khi chọn thứ cụ thể: day_group suy ra từ các thứ (T7, CN = ngày nghỉ; lẫn cả hai -> None) để tham khảo
            "day_group": day_group if days is None else (
                "non_working" if set(days) <= {0, 6} else "working" if not set(days) & {0, 6} else None),
            "day_of_week": days,
            "day_group_label": DAY_GROUPS[day_group] if days is None else weekdays_label(days),
            "weather": weather["key"], "weather_label": weather["name"]},
        "thresholds": th,
        "overall_mean": overall_mean,
        "hours": hours,
        "summary": {
            "counts": counts,
            "priority_hours": [{"hour": x["hour"], "avg_rentals": x["avg_rentals"]} for x in priority],
            "peak": max(has_data, key=lambda x: x["avg_rentals"], default=None),
            "lowest": min(has_data, key=lambda x: x["avg_rentals"], default=None),
        },
        "alerts": high_windows(hours, casual_ref),
        "notes": notes,
        "user_mix": {
            "reference_casual_share": casual_ref,
            "scenario_casual_share": scen_share,
            "scenario_segment": segment(scen_share, casual_ref),
            "casual_heavy_at": CASUAL_HEAVY_FACTOR * casual_ref if casual_ref else None,
            "registered_heavy_at": REGISTERED_HEAVY_FACTOR * casual_ref if casual_ref else None,
            "segments": [{"segment": s, "label": SEGMENT_LABELS[s], "advice": SEGMENT_ADVICE[s]} for s in SEGMENTS],
        },
    }


def build_matrix(rows: list, th: dict, overall_mean: float, weathers: list) -> dict:
    """Phân loại toàn bộ nhóm giờ x loại ngày x thời tiết. rows: [{hour, day_group, weather_key, n_obs, avg_rentals}]."""
    idx = {(r["hour"], r["day_group"], r["weather_key"]): r for r in rows}
    cols = [{"day_group": g, "weather": w["key"], "label": f"{DAY_GROUPS[g].split(' (')[0]} · {w['name']}"}
            for g in DAY_GROUPS for w in weathers]
    cells = []
    for h in range(24):
        for c in cols:
            r = idx.get((h, c["day_group"], c["weather"]), {})
            a = assess(r.get("avg_rentals"), int(r.get("n_obs") or 0), th, overall_mean)
            cells.append({"hour": h, "day_group": c["day_group"], "weather": c["weather"],
                          "avg_rentals": a["avg_rentals"], "n_obs": a["n_obs"],
                          "level": a["level"], "reliable": a["reliable"]})
    return {"thresholds": th, "cols": cols, "cells": cells}
