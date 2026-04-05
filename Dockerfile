FROM python:3-alpine

WORKDIR /app

RUN apk add --no-cache chromium shadow su-exec && \
    groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/sh -m appuser

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY craigslist-renew.py docker-entrypoint.sh ./

VOLUME /data

ENTRYPOINT ["/app/docker-entrypoint.sh"]
