"""Sinh hình kiểm định ngoài mẫu (backtest) và bảng LaTeX cho báo cáo. Không cần CSDL.

Chạy từ thư mục gốc repo:  .venv/bin/python report/scripts/make_backtest_figure.py
Kết quả: report/figures/backtest.pdf (vector). Xem trước PNG:
    FIG_FMT=png FIG_DIR=<thư mục nháp> .venv/bin/python report/scripts/make_backtest_figure.py
Ngoài hình, script in ra bảng LaTeX 9 thí nghiệm và tỷ lệ tổng lượt thuê 2012/2011 để dùng trong văn bản.
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.getenv("FIG_DIR", ROOT / "report" / "figures"))
FMT = os.getenv("FIG_FMT", "pdf")          # FIG_FMT=png để xem nhanh
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
from dss import backtest as B  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": .3, "figure.dpi": 150})
BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#8b5cf6", "#9ca3af"
LEVEL_VI = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}
SCHEME_VI = {"static": "Tĩnh", "expanding": "Mở rộng", "expanding_adjusted": "Mở rộng + hiệu chỉnh"}
SCHEME_COL = {"static": GRAY, "expanding": BLUE, "expanding_adjusted": RED}
MODEL_VI = {"full": "DSS", "full_temp": "DSS + nhiệt độ", "hour_only": "Chỉ theo giờ"}


def vn_pct(x):
    return f"{x * 100:.1f}\\%".replace(".", ",")


def vn_num(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


def mean_demand_ratio(records, test_year):
    """Tỷ lệ lượt thuê TB theo giờ của năm kiểm thử so với năm lịch sử ngay trước đó."""
    def mean(year):
        vals = [r["total_cnt"] for r in records if r["date"].year == year]
        return sum(vals) / len(vals)
    return mean(test_year) / mean(test_year - 1)


def print_latex_table(res):
    print("% ---- bảng LaTeX (tab:backtest) ----")
    for e in res["experiments"]:
        m = e["metrics"]
        model = MODEL_VI[e["model"]]
        scheme = SCHEME_VI[e["scheme"]]
        print(f"{model} & {scheme} & {vn_pct(m['accuracy'])} & {vn_pct(m['macro_f1'])} & "
              f"{vn_pct(m['macro_recall'])} & {vn_pct(m['under_prepared_rate'])} & "
              f"{vn_pct(m['over_prepared_rate'])} & {vn_num(m['mae'])} \\\\")
    print("% ---- hết bảng ----")


def draw_confusion(ax, conf, title):
    levels = ["low", "medium", "high"]
    counts = [[conf[a][p] for p in levels] for a in levels]
    pct = [[counts[i][j] / max(sum(counts[i]), 1) for j in range(3)] for i in range(3)]
    ax.imshow(pct, cmap="Blues", vmin=0, vmax=1, aspect="equal")
    for i in range(3):
        for j in range(3):
            color = "white" if pct[i][j] > 0.55 else "#111827"
            ax.text(j, i, f"{counts[i][j]:,}\n({pct[i][j] * 100:.0f}%)".replace(",", "."),
                    ha="center", va="center", fontsize=8, color=color)
    ax.set_xticks(range(3), [LEVEL_VI[l] for l in levels], fontsize=8.5)
    ax.set_yticks(range(3), [LEVEL_VI[l] for l in levels], fontsize=8.5)
    ax.set_xlabel("Dự báo"), ax.set_ylabel("Thực tế")
    ax.set_title(title, fontsize=9.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def main():
    records = B.load_uci_hour_csv(ROOT / "data" / "hour.csv")
    res = B.run_backtest(records)
    exps = {e["id"]: e for e in res["experiments"]}

    ratio = mean_demand_ratio(records, res["test_year"])
    print(f"Tỷ lệ TB lượt thuê/giờ {res['test_year']} / {res['test_year'] - 1} = {ratio:.2f}")
    print(f"Số giờ huấn luyện (tĩnh) = {res['n_train_static']:,}; số giờ kiểm thử = {res['n_test']:,}".replace(",", "."))
    print_latex_table(res)

    # Hình: (a) ma trận nhầm lẫn full_static, (b) full_expanding_adjusted, (c) recall TB 3 mức theo tháng
    import matplotlib.gridspec as gridspec
    fig = plt.figure(figsize=(7.4, 6.8))
    gs = gridspec.GridSpec(2, 2, figure=fig, height_ratios=[1.0, 0.85], hspace=0.55, wspace=1.15)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    draw_confusion(ax_a, exps["full_static"]["metrics"]["confusion"],
                   "(a) Tĩnh (cố định đến 2011)")
    draw_confusion(ax_b, exps["full_expanding_adjusted"]["metrics"]["confusion"],
                   "(b) Mở rộng + hiệu chỉnh mức")

    months = list(range(1, 13))
    lines = [
        ("full_static", GRAY, "DSS, tĩnh"),
        ("full_expanding", BLUE, "DSS, mở rộng"),
        ("full_expanding_adjusted", RED, "DSS, mở rộng + hiệu chỉnh"),
        ("full_temp_expanding_adjusted", PURPLE, "DSS + nhiệt độ, mở rộng + hiệu chỉnh"),
    ]
    for eid, color, name in lines:
        mon = exps[eid]["monthly"]
        ys = [float("nan") if m["macro_recall"] is None else m["macro_recall"] for m in mon]
        ax_c.plot(months, ys, color=color, lw=2, marker="o", ms=4, label=name)
    ax_c.set_title("(c) Recall (TB 3 mức) theo tháng", fontsize=9.5)
    ax_c.set_xticks(months), ax_c.set_xlabel("Tháng")
    ax_c.set_ylabel("Recall (TB 3 mức)")
    ax_c.set_ylim(0, 1.05)
    ax_c.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax_c.legend(frameon=False, ncol=2, loc="lower left", fontsize=8.5)

    path = OUT / f"backtest.{FMT}"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("->", path)


if __name__ == "__main__":
    main()
