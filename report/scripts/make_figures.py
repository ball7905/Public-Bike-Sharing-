"""Sinh các hình số liệu cho báo cáo từ API của kho dữ liệu (cần DB bike_dw đã nạp ETL).

Chạy từ thư mục gốc repo:  python report/scripts/make_figures.py
Kết quả: report/figures/*.pdf (vector, dùng trực tiếp trên Overleaf).
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.getenv("FIG_DIR", ROOT / "report" / "figures"))
FMT = os.getenv("FIG_FMT", "pdf")          # FIG_FMT=png để xem nhanh
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

c = TestClient(app)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": .3, "figure.dpi": 150})
BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#8b5cf6", "#9ca3af"
LV = {"low": GREEN, "medium": ORANGE, "high": RED}


def get(path, **params):
    r = c.get("/api/" + path, params=params)
    r.raise_for_status()
    return r.json()


def save(fig, name):
    fig.tight_layout()
    path = OUT / f"{name}.{FMT}"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("->", path)


def fig_hourly():
    d = get("hourly")
    h = [x["hour"] for x in d]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.plot(h, [x["avg_working"] for x in d], color=BLUE, lw=2, marker="o", ms=3, label="Ngày làm việc")
    ax.plot(h, [x["avg_non_working"] for x in d], color=GREEN, lw=2, marker="o", ms=3, label="Ngày nghỉ (cuối tuần, lễ)")
    ax.set_xticks(range(0, 24, 2)), ax.set_xlabel("Giờ trong ngày"), ax.set_ylabel("Lượt thuê TB / giờ")
    ax.legend(frameon=False)
    save(fig, "hourly_profile")


def fig_monthly():
    p = get("olap/pivot", row="month", col="year", measure="avg_hourly")
    cell = {(x["r"], x["c"]): x["value"] for x in p["cells"]}
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for y, col in zip(p["cols"], [GRAY, BLUE]):
        ax.plot(range(1, 13), [cell[(m, y)] for m in p["rows"]], color=col, lw=2, marker="o", ms=4, label=f"Năm {y}")
    ax.set_xticks(range(1, 13)), ax.set_xlabel("Tháng"), ax.set_ylabel("Lượt thuê TB / giờ")
    ax.legend(frameon=False)
    save(fig, "monthly_trend")


def fig_weather_daytype():
    w, d = get("weather"), get("day-type")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.0))
    a1.bar([x["label"].replace(" rain/snow", "\nrain/snow") for x in w], [x["avg_hourly"] for x in w],
           color=[BLUE, BLUE, BLUE, GRAY])
    a1.tick_params(axis="x", labelsize=8)
    for i, x in enumerate(w):
        a1.text(i, x["avg_hourly"] + 4, f"{x['avg_hourly']:.0f}\n(n={x['n_hours']:,})".replace(",", "."), ha="center", fontsize=7.5)
    a1.set_ylabel("Lượt thuê TB / giờ"), a1.set_title("Theo thời tiết", fontsize=10), a1.set_ylim(0, 260)
    labels = {"Working day": "Làm việc", "Weekend": "Cuối tuần", "Holiday": "Ngày lễ"}
    a2.bar([labels[x["label"]] for x in d], [x["avg_daily"] for x in d], color=PURPLE)
    for i, x in enumerate(d):
        a2.text(i, x["avg_daily"] + 60, f"{x['avg_daily']:,.0f}\n({x['n_days']} ngày)".replace(",", "."), ha="center", fontsize=7.5)
    a2.set_ylabel("Lượt thuê TB / ngày"), a2.set_title("Theo loại ngày", fontsize=10), a2.set_ylim(0, 5600)
    save(fig, "weather_daytype")


def fig_users():
    d = get("users", by="weekday")
    vi = {"Sunday": "CN", "Monday": "T2", "Tuesday": "T3", "Wednesday": "T4", "Thursday": "T5", "Friday": "T6", "Saturday": "T7"}
    x = [vi[r["label"]] for r in d]
    reg, cas = np.array([r["registered"] for r in d]), np.array([r["casual"] for r in d])
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.bar(x, reg / 1000, color=BLUE, label="Đăng ký")
    ax.bar(x, cas / 1000, bottom=reg / 1000, color=ORANGE, label="Vãng lai")
    for i in range(len(x)):
        ax.text(i, (reg[i] + cas[i]) / 1000 + 5, f"{cas[i] / (reg[i] + cas[i]) * 100:.0f}% VL", ha="center", fontsize=8)
    ax.set_ylabel("Tổng lượt thuê (nghìn)"), ax.set_ylim(0, 560), ax.legend(frameon=False, ncol=2, loc="lower right")
    save(fig, "users_weekday")


def fig_climate():
    t, h = get("climate", by="temp"), get("climate", by="humidity")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.2))
    for ax, d, col, title in [(a1, t, "#ef4444", "Nhiệt độ (°C)"), (a2, h, "#0ea5e9", "Độ ẩm (%)")]:
        b = d["bins"]
        ax.bar(range(len(b)), [x["avg_total"] for x in b], color=[col if x["reliable"] else GRAY for x in b])
        ax.set_xticks(range(len(b)), [x["label"].replace("°C", "").replace("%", "") for x in b], rotation=45, fontsize=7.5)
        r = d["correlation"]
        key = "temp" if d["by"] == "temp" else "humidity"
        ax.set_title(f"{title}\nr(giờ) = {r['hourly'][key]:.2f}, r(ngày) = {r['daily'][key]:.2f}", fontsize=9.5)
        ax.set_ylabel("Lượt thuê TB / giờ")
    save(fig, "climate")


def fig_dss_distribution():
    th = get("dss/thresholds")
    import pandas as pd
    cnt = pd.read_csv(ROOT / "data" / "hour.csv")["cnt"]
    lo, hi = th["thresholds"]["low"], th["thresholds"]["high"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    bins = np.arange(0, 1000, 20)
    n, edges, patches = ax.hist(cnt, bins=bins, color=GRAY, edgecolor="white")
    for p, e in zip(patches, edges[:-1]):
        p.set_facecolor(GREEN if e + 10 < lo else RED if e + 10 > hi else ORANGE)
    for v, lab in [(lo, f"P33,3 = {lo:.0f}"), (hi, f"P66,7 = {hi:.0f}")]:
        ax.axvline(v, color="black", ls="--", lw=1)
        ax.text(v + 8, ax.get_ylim()[1] * .9, lab, fontsize=8.5)
    ax.set_xlabel("Lượt thuê trong 1 giờ (total_cnt)"), ax.set_ylabel("Số giờ quan sát")
    save(fig, "dss_distribution")


def fig_dss_plan():
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.1), sharey=True)
    for ax, dg, title in [(axes[0], "working", "Ngày làm việc, Clear"), (axes[1], "non_working", "Ngày nghỉ, Clear")]:
        p = get("dss/plan", day_group=dg, weather=1)
        hs = p["hours"]
        ax.bar([h["hour"] for h in hs], [h["avg_rentals"] for h in hs], color=[LV[h["level"]] for h in hs])
        ax.axhline(p["thresholds"]["low"], color=GREEN, ls="--", lw=1)
        ax.axhline(p["thresholds"]["high"], color=RED, ls="--", lw=1)
        ax.set_title(title, fontsize=10), ax.set_xticks(range(0, 24, 3)), ax.set_xlabel("Giờ")
    axes[0].set_ylabel("Lượt thuê TB / giờ")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=GREEN, label="Thấp"), Patch(color=ORANGE, label="Trung bình"), Patch(color=RED, label="Cao")],
               loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.06))
    save(fig, "dss_plan")


def fig_dss_matrix():
    m = get("dss/matrix")
    cols = [col for col in m["cols"] if col["weather"] != 4]
    code = {"low": 0, "medium": 1, "high": 2}
    grid = np.full((24, len(cols)), np.nan)
    alpha = np.ones((24, len(cols)))
    idx = {(x["hour"], x["day_group"], x["weather"]): x for x in m["cells"]}
    for j, col in enumerate(cols):
        for h in range(24):
            x = idx[(h, col["day_group"], col["weather"])]
            if x["level"]:
                grid[h, j] = code[x["level"]]
                alpha[h, j] = 1 if x["reliable"] else .45
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    ax.imshow(grid, cmap=ListedColormap([GREEN, ORANGE, RED]), vmin=0, vmax=2, aspect="auto", alpha=alpha)
    for j, col in enumerate(cols):
        for h in range(24):
            x = idx[(h, col["day_group"], col["weather"])]
            if x["avg_rentals"] is not None:
                ax.text(j, h, f"{x['avg_rentals']:.0f}", ha="center", va="center", fontsize=7, color="white")
    ax.set_xticks(range(len(cols)), [col["label"].replace(" · ", "\n") for col in cols], fontsize=8)
    ax.set_yticks(range(24), [f"{h:02d}h" for h in range(24)], fontsize=7.5)
    ax.grid(False)
    save(fig, "dss_matrix")


if __name__ == "__main__":
    for f in [fig_hourly, fig_monthly, fig_weather_daytype, fig_users, fig_climate,
              fig_dss_distribution, fig_dss_plan, fig_dss_matrix]:
        f()
