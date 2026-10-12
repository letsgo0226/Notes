FROM python:3.11-alpine
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY cosmic_zero_field/model.py /app/cosmic_zero_field/model.py
COPY cosmic_zero_field/worker.py /app/cosmic_zero_field/worker.py
USER 65532:65532
CMD ["python","-u","-m","cosmic_zero_field.worker","--interval","300"]
