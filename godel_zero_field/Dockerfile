FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY godel_zero_field /app/godel_zero_field
USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "godel_zero_field.server"]
