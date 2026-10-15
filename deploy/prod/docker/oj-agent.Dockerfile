FROM python:3.11-slim

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}
ENV PIP_DEFAULT_TIMEOUT=100
ENV FASTEMBED_CACHE_PATH=/opt/fastembed-cache
ENV FASTEMBED_MODEL_PATH=/opt/fastembed-model
ENV HF_HUB_OFFLINE=1

WORKDIR /app

COPY oj-agent/pyproject.toml /app/pyproject.toml
COPY oj-agent/app /app/app
COPY hermes/skills /opt/syncode/hermes/skills
COPY hermes/plugins /opt/syncode/hermes/plugins
COPY .deploy-assets/fastembed-model /opt/fastembed-model

RUN pip install --no-cache-dir . \
    && python -c 'from fastembed import TextEmbedding; model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5", cache_dir="/opt/fastembed-cache", threads=1, local_files_only=True, specific_model_path="/opt/fastembed-model"); assert len(next(iter(model.embed(["生产离线向量验收"])))) == 512' \
    && groupadd --system --gid 10000 syncode \
    && useradd --system --uid 10000 --gid syncode --home-dir /app syncode \
    && mkdir -p /app/runtime-artifacts /var/lib/hermes /opt/syncode/hermes/skills /opt/syncode/hermes/plugins \
    && chown -R syncode:syncode /app/runtime-artifacts /var/lib/hermes /opt/fastembed-cache /opt/fastembed-model /opt/syncode/hermes/skills /opt/syncode/hermes/plugins

USER syncode

EXPOSE 8015

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015"]
