ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
FROM ${HERMES_BASE_IMAGE}

COPY deploy/prod/docker/patch-hermes-skills-api.py /tmp/patch-hermes-skills-api.py
RUN python /tmp/patch-hermes-skills-api.py \
      /opt/hermes/gateway/platforms/api_server.py \
      /opt/hermes/tools/skills_tool.py \
    && rm /tmp/patch-hermes-skills-api.py
COPY deploy/prod/docker/hermes-default-env.sh /etc/cont-init.d/014-syncode-default-env
RUN chmod 755 /etc/cont-init.d/014-syncode-default-env
COPY --chown=10000:10000 hermes/skills /opt/syncode/hermes/skills
