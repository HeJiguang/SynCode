ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
FROM ${HERMES_BASE_IMAGE}

COPY --chown=10000:10000 hermes/skills /opt/syncode/hermes/skills
