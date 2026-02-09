FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create log directory
RUN mkdir -p /var/log/linkkeeper

# Install crontab
COPY crontab /etc/cron.d/linkkeeper
RUN chmod 0644 /etc/cron.d/linkkeeper \
    && crontab /etc/cron.d/linkkeeper

# Healthcheck: verify Python and DB connectivity
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "from config import load_config; from lib.db import get_connection; get_connection(load_config()).ping()" || exit 1

# Run cron in foreground, piping env vars so cron jobs can access them
CMD printenv > /etc/environment && cron -f
