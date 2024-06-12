FROM python:3-alpine

RUN apk update && apk add gcc musl-dev postgresql-dev python3-dev

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY countdown_bot .

WORKDIR /
CMD ["python", "-m", "app"]
