"""Cấu hình: đọc từ file .env hoặc biến môi trường (xem .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# Đọc file .env ở thư mục gốc repo (nếu có). Biến môi trường đã đặt sẵn trong shell vẫn được ưu tiên.
load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
SQL_DIR = ROOT / "sql"
REPORT_DIR = ROOT / "docs"

DB = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "bike_dw"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", ""),
}

# Hệ số quy đổi theo Readme của UCI
TEMP_MAX, ATEMP_MAX, HUM_MAX, WIND_MAX = 41, 50, 100, 67

SEASON_NAMES = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
WEATHER = {
    1: ("Clear", "Clear, Few clouds, Partly cloudy"),
    2: ("Mist", "Mist + Cloudy, Mist + Broken clouds, Mist + Few clouds, Mist"),
    3: ("Light rain/snow", "Light Snow, Light Rain + Thunderstorm + Scattered clouds, Light Rain + Scattered clouds"),
    4: ("Heavy rain/snow", "Heavy Rain + Ice Pallets + Thunderstorm + Mist, Snow + Fog"),
}
