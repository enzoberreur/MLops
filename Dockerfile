FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \ 
    && apt-get install --no-install-recommends -y build-essential libgl1 libglib2.0-0 \ 
    && pip install --upgrade pip \ 
    && pip install -r requirements.txt \ 
    && apt-get purge -y build-essential \ 
    && apt-get autoremove -y \ 
    && rm -rf /var/lib/apt/lists/*

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
