"""Smoke test API với DB đã nạp ETL. Chạy: pytest tests -q  (cần DB bike_dw đã có dữ liệu)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))   # giống `uvicorn --app-dir src`
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

c = TestClient(app)
TOTAL, CASUAL, REGISTERED = 3_292_679, 620_017, 2_672_662


def test_kpi_total_matches_source():
    k = c.get("/api/kpis").json()
    assert k["total_rentals"] == TOTAL                     # NFR01: khớp dữ liệu nguồn
    assert abs(k["registered_ratio"] + k["casual_ratio"] - 1) < 1e-9
    assert abs(k["registered_ratio"] - REGISTERED / TOTAL) < 1e-9


def test_rollup_consistency():
    years = c.get("/api/olap/drill", params={"level": "year"}).json()
    assert sum(r["total"] for r in years) == TOTAL
    y = years[1]["key"]
    quarters = c.get("/api/olap/drill", params={"level": "quarter", "d_year": y}).json()
    assert sum(r["total"] for r in quarters) == years[1]["total"]   # drill-down không mất dữ liệu


def test_drill_to_day_and_hour():
    days = c.get("/api/olap/drill", params={"level": "day", "d_year": 2012, "d_month": 7}).json()
    assert len(days) == 31 and days[0]["label"] == "1"
    month_total = c.get("/api/kpis", params={"year": 2012, "month": 7}).json()["total_rentals"]
    assert sum(r["total"] for r in days) == month_total
    hours = c.get("/api/olap/drill", params={"level": "hour", "d_day": "2012-07-06"}).json()
    assert 1 <= len(hours) <= 24 and sum(r["total"] for r in hours) == next(r["total"] for r in days if r["key"] == "2012-07-06")


def test_drill_with_multi_year_global_filter():
    r = c.get("/api/olap/drill", params={"level": "year", "year": "2011,2012"})
    assert r.status_code == 200 and len(r.json()) == 2
    r = c.get("/api/olap/drill", params={"level": "quarter", "d_year": 2012, "year": "2011,2012"})
    assert r.status_code == 200 and len(r.json()) == 4


def test_slice_and_dice():
    full = c.get("/api/kpis").json()["total_rentals"]
    sl = c.get("/api/kpis", params={"year": 2012}).json()["total_rentals"]
    dc = c.get("/api/kpis", params={"year": 2012, "season": "2,3", "day_type": "Working day"}).json()["total_rentals"]
    assert 0 < dc < sl < full


def test_pivot_sums_to_total():
    p = c.get("/api/olap/pivot", params={"row": "month", "col": "weather", "measure": "total"}).json()
    assert round(sum(x["value"] for x in p["cells"])) == TOTAL


def test_validation_errors():
    assert c.get("/api/olap/drill", params={"level": "quarter"}).status_code == 422
    assert c.get("/api/olap/pivot", params={"row": "month", "col": "month"}).status_code == 422
    assert c.get("/api/kpis", params={"year": "abc"}).status_code == 422


def test_sql_injection_is_inert():
    r = c.get("/api/kpis", params={"day_type": "x'; DROP TABLE dw.fact_rentals;--"})
    assert r.status_code == 200 and r.json()["total_rentals"] == 0
    assert c.get("/api/health").json()["fact_rows"] == 17379
