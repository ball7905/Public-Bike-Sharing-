#!/bin/sh
# Khởi động container: chờ DB, nạp ETL nếu kho trống (hoặc RUN_ETL=always), rồi chạy API.
set -e
cd /app

# 1) Chờ DB sẵn sàng: tối đa 30 lần, mỗi lần cách 2 giây
i=0
while :; do
  rc=0
  python scripts/db_ready.py || rc=$?
  [ "$rc" -ne 1 ] && break
  i=$((i + 1))
  if [ "$i" -ge 30 ]; then
    echo "Không kết nối được DB sau 30 lần thử" >&2
    exit 1
  fi
  echo "Chờ DB... ($i/30)"
  sleep 2
done

# 2) Nạp ETL nếu kho trống (rc=2) hoặc người dùng yêu cầu luôn chạy (RUN_ETL=always)
if [ "$rc" -eq 2 ] || [ "${RUN_ETL:-}" = "always" ]; then
  echo "Chạy ETL (nạp kho dữ liệu)..."
  python src/etl/run_etl.py
else
  echo "Kho dữ liệu đã có sẵn, bỏ qua ETL"
fi

# 3) Chạy API (và dashboard) ở cổng PORT (Render cấp biến này)
exec uvicorn --app-dir src api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
