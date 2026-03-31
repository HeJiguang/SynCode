FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY oj-agent /app

RUN pip install --no-cache-dir .

EXPOSE 8015
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015"]
