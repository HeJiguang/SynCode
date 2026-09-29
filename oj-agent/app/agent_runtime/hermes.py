import hashlib
from pathlib import Path
import time
from typing import Any

import httpx

from app.agent_runtime.base import AgentRunRequest, AgentRunResult, AgentRuntime, AgentRuntimeError
from app.agent_runtime.session_store import HermesSessionStore
from app.core.config import AgentSettings
from app.domain.tool_permissions import ToolActionRequest, ToolPolicyDecision, evaluate_tool_request
from app.llm.base import CHAT_CAPABILITY, TRAINING_CAPABILITY


_TERMINAL_FAILURE_STATUSES = {"failed", "cancelled", "interrupted"}


class HermesAgentRuntime(AgentRuntime):
    """HTTP adapter for the Hermes Agent runs API."""

    def __init__(
        self,
        settings: AgentSettings,
        *,
        http_client: httpx.Client | None = None,
        session_store: HermesSessionStore | None = None,
    ) -> None:
        self.settings = settings
        self._http_client = http_client
        self.session_store = session_store or HermesSessionStore(Path(settings.runtime_data_dir))

    @property
    def name(self) -> str:
        return "hermes"

    def is_available(self) -> bool:
        return bool(
            self.settings.hermes_base_url
            and self.settings.hermes_api_key
            and (self.settings.hermes_chat_model or self.settings.hermes_training_model)
        )

    def model_name(self, capability: str) -> str:
        if capability == TRAINING_CAPABILITY and self.settings.hermes_training_model:
            return self.settings.hermes_training_model
        if capability == CHAT_CAPABILITY and self.settings.hermes_chat_model:
            return self.settings.hermes_chat_model
        return self.settings.hermes_chat_model or self.settings.hermes_training_model or "unknown-model"

    def generate(self, request: AgentRunRequest) -> AgentRunResult:
        if not self.is_available():
            raise AgentRuntimeError("Hermes Agent Runtime 配置不完整。")

        if self._http_client is not None:
            return self._generate_with_client(self._http_client, request)

        with httpx.Client(
            base_url=self._api_base_url(),
            timeout=self.settings.hermes_request_timeout_seconds,
        ) as client:
            return self._generate_with_client(client, request)

    def _generate_with_client(self, client: httpx.Client, request: AgentRunRequest) -> AgentRunResult:
        session_key = self._session_key(request)
        headers = {
            "Authorization": f"Bearer {self.settings.hermes_api_key}",
            "X-Hermes-Session-Key": session_key,
            "Idempotency-Key": self._idempotency_key(request.trace_id),
        }
        body: dict[str, Any] = {
            "input": request.user_prompt,
            "instructions": request.system_prompt,
            "provider": self.settings.hermes_provider,
            "model": self.model_name(request.capability),
        }
        if request.conversation_id:
            stored_session_id = self.session_store.get(request.user_id, request.conversation_id)
            if stored_session_id:
                body["session_id"] = stored_session_id

        created = self._request_json(client, "POST", "/runs", headers=headers, json=body)
        run_id = created.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise AgentRuntimeError("Hermes 没有返回有效的 run_id。")

        deadline = time.monotonic() + max(self.settings.hermes_run_timeout_seconds, 0.0)
        denied_approval_ids: set[str] = set()
        tool_decisions: list[dict[str, Any]] = []
        while True:
            status_payload = self._request_json(client, "GET", f"/runs/{run_id}", headers=headers)
            status = str(status_payload.get("status") or "").lower()
            session_id = status_payload.get("session_id")
            if request.conversation_id and isinstance(session_id, str) and session_id:
                self.session_store.bind(request.user_id, request.conversation_id, session_id)

            if status == "completed":
                output = status_payload.get("output")
                if not isinstance(output, str) or not output.strip():
                    raise AgentRuntimeError("Hermes 运行完成，但没有返回有效内容。")
                runtime = status_payload.get("runtime")
                runtime = runtime if isinstance(runtime, dict) else {}
                return AgentRunResult(
                    text=output,
                    runtime_name=self.name,
                    provider=str(runtime.get("provider") or self.settings.hermes_provider),
                    model_name=str(runtime.get("model") or status_payload.get("model") or self.model_name(request.capability)),
                    session_id=session_id if isinstance(session_id, str) else None,
                    remote_run_id=run_id,
                    tool_decisions=tuple(tool_decisions),
                )

            if status in _TERMINAL_FAILURE_STATUSES:
                error = status_payload.get("error")
                raise AgentRuntimeError(f"Hermes 运行失败（{status}）：{error or '未提供错误信息'}")

            if status == "waiting_for_approval":
                approval = status_payload.get("approval")
                approval = approval if isinstance(approval, dict) else {}
                request_id = approval.get("request_id")
                if not isinstance(request_id, str) or not request_id.strip():
                    self._stop_run(client, run_id, headers)
                    raise AgentRuntimeError("Hermes 工具审批缺少 request_id，运行已停止。")
                request_id = request_id.strip()
                if request_id not in denied_approval_ids:
                    decision = evaluate_tool_request(
                        ToolActionRequest(
                            tool_name="host.shell",
                            action="execute",
                            resource=str(approval.get("command") or "")[:1000] or None,
                            arguments={
                                "description": str(approval.get("description") or "")[:500],
                                "pattern_key": str(approval.get("pattern_key") or "")[:256],
                            },
                        )
                    )
                    if decision.decision is not ToolPolicyDecision.BLOCK:
                        self._stop_run(client, run_id, headers)
                        raise AgentRuntimeError("Hermes 宿主机工具没有被 SynCode 权限策略拒绝，运行已停止。")
                    self._request_json(
                        client,
                        "POST",
                        f"/runs/{run_id}/approval",
                        headers=headers,
                        json={"choice": "deny", "request_id": request_id},
                    )
                    denied_approval_ids.add(request_id)
                    tool_decisions.append(
                        {
                            "hermes_run_id": run_id,
                            "hermes_request_id": request_id,
                            "tool_name": "host.shell",
                            "action": "execute",
                            "resource": str(approval.get("command") or "")[:1000] or None,
                            "arguments": {
                                "description": str(approval.get("description") or "")[:500],
                                "pattern_key": str(approval.get("pattern_key") or "")[:256],
                            },
                            "risk_level": decision.risk_level.value,
                            "decision": decision.decision.value,
                            "status": "DENIED",
                            "reason": decision.reason,
                        }
                    )
                time.sleep(max(self.settings.hermes_poll_interval_seconds, 0.01))
                continue

            if time.monotonic() >= deadline:
                self._stop_run(client, run_id, headers)
                raise AgentRuntimeError(f"Hermes 运行超时（run_id={run_id}）。")

            time.sleep(max(self.settings.hermes_poll_interval_seconds, 0.01))

    def _request_json(self, client: httpx.Client, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentRuntimeError(f"Hermes API 调用失败：{exc}") from exc
        if not isinstance(payload, dict):
            raise AgentRuntimeError("Hermes API 返回了无效响应。")
        return payload

    def _stop_run(self, client: httpx.Client, run_id: str, headers: dict[str, str]) -> None:
        try:
            client.post(f"/runs/{run_id}/stop", headers=headers)
        except httpx.HTTPError:
            pass

    def _api_base_url(self) -> str:
        base_url = str(self.settings.hermes_base_url or "").rstrip("/")
        return base_url if base_url.endswith("/v1") else f"{base_url}/v1"

    @staticmethod
    def _idempotency_key(trace_id: str) -> str:
        digest = hashlib.sha256(trace_id.encode("utf-8")).hexdigest()
        return f"syncode-{digest}"

    @staticmethod
    def _session_key(request: AgentRunRequest) -> str:
        conversation_id = request.conversation_id or request.trace_id
        digest = HermesSessionStore.conversation_key(request.user_id, conversation_id)
        return f"syncode:{digest}"
