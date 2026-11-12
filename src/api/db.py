"""Kết nối PostgreSQL (chỉ đọc) cho API. Cấu hình lấy từ .env / biến môi trường."""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DB = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "bike_dw"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", ""),
}
# DATABASE_URL (vd. Render) có ưu tiên hơn các biến PG* ở trên; để trống thì dùng PG*.
DB_DSN = os.getenv("DATABASE_URL")


@contextmanager
def cursor():
    conn = psycopg2.connect(DB_DSN) if DB_DSN else psycopg2.connect(**DB)
    conn.set_session(readonly=True, autocommit=True)   # API chỉ được đọc DW
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
    finally:
        conn.close()
