ARG HERMES_BASE_IMAGE
FROM ${HERMES_BASE_IMAGE}

COPY --chown=10000:10000 hermes/skills /opt/syncode/hermes/skills
COPY --chown=10000:10000 hermes/plugins /opt/syncode/hermes/plugins
