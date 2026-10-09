ARG HERMES_BASE_IMAGE=nousresearch/hermes-agent:latest
FROM ${HERMES_BASE_IMAGE}

COPY deploy/prod/docker/patch-hermes-skills-api.py /tmp/patch-hermes-skills-api.py
COPY deploy/prod/docker/patch-hermes-governance-api.py /tmp/patch-hermes-governance-api.py
COPY hermes/extensions/api_server_syncode_governance.py /opt/hermes/gateway/platforms/api_server_syncode_governance.py
COPY hermes/context_engine/syncode_reviewed /opt/hermes/plugins/context_engine/syncode_reviewed
RUN python /tmp/patch-hermes-skills-api.py \
      /opt/hermes/gateway/platforms/api_server.py \
      /opt/hermes/tools/skills_tool.py \
    && python /tmp/patch-hermes-governance-api.py \
      /opt/hermes/gateway/platforms/api_server.py \
      /opt/hermes/tools/write_approval.py \
      /opt/hermes/tools/memory_tool.py \
      /opt/hermes/tools/approval.py \
      /opt/hermes/agent/context_compressor.py \
      /opt/hermes/tools/approval_context.py \
      /opt/hermes/tools/approval_gateway_wait.py \
      /opt/hermes/hermes_state_messages.py \
    && python -m py_compile \
      /opt/hermes/gateway/platforms/api_server.py \
      /opt/hermes/gateway/platforms/api_server_syncode_governance.py \
      /opt/hermes/plugins/context_engine/syncode_reviewed/__init__.py \
    && rm /tmp/patch-hermes-skills-api.py /tmp/patch-hermes-governance-api.py
COPY deploy/prod/docker/hermes-default-env.sh /etc/cont-init.d/014-syncode-default-env
RUN chmod 755 /etc/cont-init.d/014-syncode-default-env
COPY --chown=10000:10000 hermes/skills /opt/syncode/hermes/skills
