ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
FROM ${HERMES_BASE_IMAGE}

COPY --chmod=755 deploy/prod/docker/hermes-default-env.sh /etc/cont-init.d/014-syncode-default-env
COPY --chown=10000:10000 hermes/skills /opt/syncode/hermes/skills
