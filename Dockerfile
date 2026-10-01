FROM python:3.11-slim

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

COPY app/crontab.txt /etc/cron.d/birthday-cron
RUN chmod 0644 /etc/cron.d/birthday-cron && crontab /etc/cron.d/birthday-cron

RUN mkdir /data

CMD cron && python3 /app/generate.py && exec python3 /app/server.py

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8080/birthdays.ics', method='HEAD'), timeout=4)"
