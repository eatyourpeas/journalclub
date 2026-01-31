FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng ffmpeg libsndfile1 ca-certificates wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/espeak/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY docker/espeak/app.py /app/app.py

EXPOSE 5003

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5003"]
