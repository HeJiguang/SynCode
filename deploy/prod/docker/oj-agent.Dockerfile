FROM python:3.11-slim

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

COPY oj-agent/pyproject.toml /app/pyproject.toml
COPY oj-agent/app /app/app

RUN pip install --no-cache-dir . \
    && groupadd --system --gid 10000 syncode \
    && useradd --system --uid 10000 --gid syncode --home-dir /app syncode \
    && mkdir -p /app/runtime-artifacts /var/lib/hermes /var/lib/syncode-runtime \
    && chown -R syncode:syncode /app/runtime-artifacts /var/lib/hermes /var/lib/syncode-runtime

USER syncode

EXPOSE 8015 8016 8017 8018

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015"]
