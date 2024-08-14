FROM alpine:3.19 AS builder

RUN apk update && apk add wget
RUN wget https://raw.githubusercontent.com/thoth-station/micropipenv/master/micropipenv.py

FROM python:3.12-slim-bookworm

WORKDIR /app

COPY pyproject.toml /app
COPY poetry.lock /app

COPY --from=builder /micropipenv.py micropipenv.py
RUN python micropipenv.py install && rm micropipenv.py

COPY . /app
COPY docker/run.sh run.sh

CMD ["/app/run.sh"]
