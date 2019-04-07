FROM alpine

WORKDIR /app

RUN apk add --no-cache python3

COPY requirements.txt .
RUN pip3 install -r requirements.txt --no-cache-dir

COPY craigslist-renew.py .

VOLUME /data

ENTRYPOINT ["python3", "craigslist-renew.py", "/data/config.yml"]
