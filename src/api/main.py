"""API cho Dashboard.  Chạy: uvicorn --app-dir src api.main:app --port 8000"""
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api import queries as Q
from api.db import cursor

app = FastAPI(title="Bike Sharing DW API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET"], allow_headers=["*"])


def get_filters(year: Optional[str] = None, season: Optional[str] = None, month: Optional[str] = None,
                weekday: Optional[str] = None, weather: Optional[str] = None,
                day_type: Optional[str] = None, time_band: Optional[str] = None) -> dict:
    try:
        return Q.parse_filters({"year": year, "season": season, "month": month, "weekday": weekday,
                                "weather": weather, "day_type": day_type, "time_band": time_band})
    except ValueError as e:
        raise HTTPException(422, str(e))


def run(fn, *args, **kwargs):
    try:
        with cursor() as cur:
            return fn(cur, *args, **kwargs)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/health")
def health():
    return run(lambda cur: Q.q(cur, "SELECT COUNT(*)::int AS fact_rows FROM dw.fact_rentals")[0])


@app.get("/api/filters")
def filters_options():
    return run(Q.filter_options)


@app.get("/api/kpis")
def kpis(f: dict = Depends(get_filters)):
    return run(Q.kpis, f)


@app.get("/api/olap/drill")
def olap_drill(level: str = "year", d_year: Optional[int] = None, d_quarter: Optional[int] = None,
               d_month: Optional[int] = None, d_day: Optional[str] = None, f: dict = Depends(get_filters)):
    # d_* là vị trí hiện tại trên đường drill-down; tách khỏi bộ lọc toàn cục (year, month, ...)
    return run(Q.drill, f, level, d_year, d_quarter, d_month, d_day)


@app.get("/api/hourly")
def hourly(f: dict = Depends(get_filters)):
    return run(Q.hourly_profile, f)


@app.get("/api/weather")
def weather(f: dict = Depends(get_filters)):
    return run(Q.by_weather, f)


@app.get("/api/day-type")
def day_type(f: dict = Depends(get_filters)):
    return run(Q.by_day_type, f)


@app.get("/api/users")
def users(by: str = Query("hour", pattern="^(hour|month|weekday)$"), f: dict = Depends(get_filters)):
    return run(Q.users, f, by)


@app.get("/api/olap/pivot")
def olap_pivot(row: str = "month", col: str = "weather", measure: str = "avg_hourly", f: dict = Depends(get_filters)):
    return run(Q.pivot, f, row, col, measure)
