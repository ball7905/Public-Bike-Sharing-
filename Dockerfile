# Build dashboard (React) bằng Node, rồi đóng gói API + dashboard + ETL vào image Python nhỏ.

# ---- Stage 1: build dashboard
FROM node:22-alpine AS web
WORKDIR /app/src/dashboard
COPY src/dashboard/package.json src/dashboard/package-lock.json ./
RUN npm ci
COPY src/dashboard/ ./
RUN npm run build

# ---- Stage 2: runtime
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Chạy bằng user không phải root
RUN groupadd -r app && useradd -r -g app -m app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Chỉ copy những gì API và ETL cần (không có report/, tests/, node_modules)
COPY data/ ./data/
COPY sql/ ./sql/
# ETL ghi docs/validation_report.md nên thư mục docs phải thuộc user app
COPY --chown=app:app docs/ ./docs/
COPY src/api/ ./src/api/
COPY src/etl/ ./src/etl/
COPY src/dss/ ./src/dss/
COPY --from=web /app/src/dashboard/dist ./src/dashboard/dist
COPY scripts/ ./scripts/

USER app
EXPOSE 8000
CMD ["sh", "scripts/start.sh"]
