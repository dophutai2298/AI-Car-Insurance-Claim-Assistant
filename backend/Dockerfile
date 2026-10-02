FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY AI/requirements.txt AI/requirements.txt
COPY backend/requirements.txt backend/requirements.txt
COPY backend/package backend/package
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

COPY AI AI
COPY backend backend

WORKDIR /workspace/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
