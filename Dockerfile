FROM python:3.11-slim

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

COPY app/crontab.txt /etc/cron.d/birthday-cron
RUN chmod 0644 /etc/cron.d/birthday-cron && crontab /etc/cron.d/birthday-cron

RUN mkdir /data

CMD cron && python3 server.py
