FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "psycopg[binary]==3.2.9" "PyYAML==6.0.2"
# Repository is bind-mounted at runtime.
CMD ["python", "-m", "engineering_os.analytics.api"]
