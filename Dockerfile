FROM python:3.11-slim-bookworm

# System deps
RUN apt-get update && apt-get install -y \
    cron curl gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright + Chromium
RUN playwright install --with-deps chromium

# Source code
COPY . .

# Cron setup
COPY cronjob /etc/cron.d/viral-cron
RUN chmod 0644 /etc/cron.d/viral-cron \
    && crontab /etc/cron.d/viral-cron \
    && touch /var/log/cron.log

# Init DB
RUN python -c "from src.models.base import init_db; init_db()"

# Start cron + tail logs so docker logs work
CMD ["sh", "-c", "cron && tail -f /var/log/cron.log"]