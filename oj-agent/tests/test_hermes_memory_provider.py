from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


def _load_provider(monkeypatch):
    agent_module = ModuleType("agent")
    memory_module = ModuleType("agent.memory_provider")

    class MemoryProvider:
        pass

    @dataclass(frozen=True)
    class RecallStatus:
        provider_label: str
        count: int
        glyph: str = "memory"

    memory_module.MemoryProvider = MemoryProvider
    memory_module.RecallStatus = RecallStatus
    monkeypatch.setitem(sys.modules, "agent", agent_module)
    monkeypatch.setitem(sys.modules, "agent.memory_provider", memory_module)
    source = Path(__file__).parents[2] / "hermes" / "plugins" / "syncode-learning-memory" / "__init__.py"
    spec = importlib.util.spec_from_file_location("syncode_learning_memory_provider_test", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provider_prefetch_injects_both_memory_domains(monkeypatch):
    module = _load_provider(monkeypatch)
    monkeypatch.setattr(
        module,
        "_load_config",
        lambda: {
            "endpoint": "http://memory.test/internal/learning-memory/recall",
            "service_key": "service-key",
        },
    )
    requests = []

    def transport(endpoint, headers, payload, timeout):
        requests.append((endpoint, headers, payload, timeout))
        return {
            "problem_solving": {
                "patterns": [],
                "episodes": [
                    {
                        "memory_id": "a" * 64,
                        "memory_level": "episode",
                        "title": "二分边界错误",
                        "summary": "两次尝试后通过",
                        "knowledge_tags": ["binary-search"],
                        "memory_status": "improving",
                        "confidence": 0.8,
                    }
                ],
                "events": [],
            },
            "learning_state": {
                "states": [
                    {
                        "state_id": "b" * 64,
                        "knowledge_tag": "binary-search",
                        "summary": "边界处理正在改善",
                        "mastery_score": 68,
                        "confidence": 0.7,
                        "trend": "improving",
                        "priority_score": 52,
                    }
                ]
            },
        }

    provider = module.SynCodeLearningMemoryProvider(transport=transport)
    provider.initialize("session-1", agent_identity="syncode-u7", hermes_home="/profiles/syncode-u7")
    context = provider.prefetch("这道二分题为什么错了", session_id="session-1")

    assert "二分边界错误" in context
    assert "Knowledge state" in context
    assert provider.get_tool_schemas() == []
    assert provider.recall_status().count == 2
    assert requests[0][1]["X-SynCode-Hermes-Profile"] == "syncode-u7"
    assert requests[0][2] == {"query": "这道二分题为什么错了"}


def test_provider_rejects_unscoped_profile(monkeypatch):
    module = _load_provider(monkeypatch)
    monkeypatch.setattr(module, "_load_config", lambda: {"service_key": "service-key"})
    provider = module.SynCodeLearningMemoryProvider(transport=lambda *_args: {})
    with pytest.raises(ValueError, match="scoped"):
        provider.initialize("session-1", agent_identity="admin", hermes_home="/profiles/admin")


def test_provider_returns_empty_context_when_backend_has_no_memory(monkeypatch):
    module = _load_provider(monkeypatch)
    monkeypatch.setattr(module, "_load_config", lambda: {"service_key": "service-key"})
    provider = module.SynCodeLearningMemoryProvider(
        transport=lambda *_args: {"problem_solving": {}, "learning_state": {}}
    )
    provider.initialize("session-1", agent_identity="syncode-u8", hermes_home="/profiles/syncode-u8")
    assert provider.prefetch("解释这个题目", session_id="session-1") == ""
    assert provider.recall_status() is None
