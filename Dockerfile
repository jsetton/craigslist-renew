FROM python:3-alpine

ARG LOCAL_WEBDRIVER=yes

WORKDIR /app

RUN if [[ "$LOCAL_WEBDRIVER" = "yes" ]]; then \
  apk add --no-cache chromium chromium-chromedriver; fi

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY craigslist-renew.py .

VOLUME /data

ENTRYPOINT ["python3", "craigslist-renew.py", "/data/config.yml"]
