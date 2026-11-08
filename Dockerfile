FROM node:22-bookworm-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

WORKDIR /app/backend

COPY AI/requirements.txt /app/AI/requirements.txt
COPY AI/car_damage_detector.py /app/AI/car_damage_detector.py
COPY AI/models/ /app/AI/models/
COPY backend/requirements.txt ./requirements.txt
COPY backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl ./package/deepdoc_vietocr-0.1.0-py3-none-any.whl
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/
COPY --from=frontend-build /frontend/dist/ /app/frontend/dist/

RUN mkdir -p /app/uploads /app/backend/outputs/car_damage_detector /tmp/ultralytics \
    && chown -R app:app /app/uploads /app/backend/outputs /tmp/ultralytics

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
