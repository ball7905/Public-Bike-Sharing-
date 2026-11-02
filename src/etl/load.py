import io
import logging
import psycopg2
from config import DB, SQL_DIR

log = logging.getLogger(__name__)

LOAD_ORDER = ["dim_date", "dim_hour", "dim_weather", "fact_rentals"]


def connect():
    return psycopg2.connect(**DB)


def create_schema(conn):
    with conn.cursor() as cur:
        cur.execute((SQL_DIR / "01_schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    log.info("Đã tạo schema dw (drop + create)")


def create_views(conn):
    with conn.cursor() as cur:
        cur.execute((SQL_DIR / "02_views.sql").read_text(encoding="utf-8"))
    conn.commit()


def copy_df(conn, table, df):
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cols = ", ".join(df.columns)
    with conn.cursor() as cur:
        cur.copy_expert(f"COPY dw.{table} ({cols}) FROM STDIN WITH (FORMAT csv)", buf)
    log.info("Load: %s <- %d dòng", table, len(df))


def load(conn, tables):
    # Nạp trong 1 transaction: lỗi thì rollback, không để DW nửa vời
    try:
        for name in LOAD_ORDER:
            copy_df(conn, name, tables[name])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    with conn.cursor() as cur:
        cur.execute("ANALYZE")
    conn.commit()
