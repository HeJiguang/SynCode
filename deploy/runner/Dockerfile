FROM ghcr.io/actions/actions-runner:latest

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gnupg \
    jq \
    lsb-release \
    maven \
    openssh-client \
    python3 \
    rsync \
    unzip \
  && install -m 0755 -d /etc/apt/keyrings \
  && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc \
  && chmod a+r /etc/apt/keyrings/docker.asc \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME}) stable" > /etc/apt/sources.list.d/docker.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    docker-buildx-plugin \
    docker-ce-cli \
    docker-compose-plugin \
  && rm -rf /var/lib/apt/lists/*

COPY deploy/runner/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENV RUNNER_ALLOW_RUNASROOT=1 \
    RUNNER_HOME=/runner \
    RUNNER_LABELS=syncode-prod \
    RUNNER_WORKDIR=_work

ENTRYPOINT ["/entrypoint.sh"]
