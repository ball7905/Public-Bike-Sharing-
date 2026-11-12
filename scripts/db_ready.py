"""Kiểm tra DB cho scripts/start.sh.  Exit: 0 = kết nối được và kho đã có dữ liệu,
1 = chưa kết nối được, 2 = kết nối được nhưng kho trống hoặc chưa có schema (cần chạy ETL)."""
import sys
from pathlib import Path

# Dùng chung cấu hình DB (DATABASE_URL hoặc PG*) với ETL
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "etl"))

import psycopg2  # noqa: E402
from config import DB, DB_DSN  # noqa: E402


def main() -> int:
    try:
        conn = psycopg2.connect(DB_DSN) if DB_DSN else psycopg2.connect(**DB)
    except psycopg2.OperationalError as e:
        print(f"Chưa kết nối được DB: {e}", file=sys.stderr)
        return 1
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('dw.fact_rentals')")
            if cur.fetchone()[0] is None:
                return 2
            cur.execute("SELECT COUNT(*) FROM dw.fact_rentals")
            return 0 if cur.fetchone()[0] > 0 else 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
