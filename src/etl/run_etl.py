"""Chạy: python src/etl/run_etl.py   (tạo schema, ETL, đối chiếu)"""
import logging
import sys
from extract import extract
from transform import transform
from load import connect, create_schema, create_views, load
from validate import validate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("etl")


def main() -> int:
    hour, day = extract()
    tables = transform(hour)
    conn = connect()
    try:
        create_schema(conn)
        load(conn, tables)
        create_views(conn)
        ok = validate(conn, hour, day)
    finally:
        conn.close()
    log.info("ETL %s", "THÀNH CÔNG" if ok else "CÓ LỖI ĐỐI CHIẾU - xem docs/validation_report.md")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
