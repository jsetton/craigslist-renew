FROM alpine

WORKDIR /app

RUN apk add --no-cache python3 py3-pip py3-wheel

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY craigslist-renew.py .

VOLUME /data

ENTRYPOINT ["python3", "craigslist-renew.py", "/data/config.yml"]
