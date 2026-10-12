FROM python:3.11-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apk add --no-cache su-exec && mkdir -p /data
WORKDIR /app
COPY cosmic_love/closure_worker.py /app/closure_worker.py
CMD ["sh","-c","chown 65532:65532 /data && exec su-exec 65532:65532 python -u /app/closure_worker.py --ledger /data/cosmic-love.jsonl --interval 60 --max-states 32"]
