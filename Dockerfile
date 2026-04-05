FROM python:3-alpine

WORKDIR /app

RUN apk add --no-cache chromium

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY craigslist-renew.py .

VOLUME /data

ENTRYPOINT ["python", "craigslist-renew.py", "/data/config.yml"]
