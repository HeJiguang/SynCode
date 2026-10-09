from __future__ import annotations

import asyncio
import json

import httpx

from app.profile_scheduler.service import LearningProfileScheduler, SchedulerSettings


class FakeRepository:
    def __init__(self) -> None:
        self.closed = False

    def list_learning_profile_sources(self, limit: int):
        assert limit == 10
        return [
            {"user_id": "7", "source_watermark": "10:3:new"},
            {"user_id": "8", "source_watermark": "20:4:new"},
        ]

    def close(self) -> None:
        self.closed = True


def test_scheduler_only_sends_server_derived_identity_and_counts_results():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        return httpx.Response(202 if payload["user_id"] == "7" else 200, json={
            "scheduled": payload["user_id"] == "7"
        })

    repository = FakeRepository()
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scheduler = LearningProfileScheduler(
        SchedulerSettings("http://gateway", "gateway-secret", batch_size=10),
        repository,  # type: ignore[arg-type]
        client,
    )
    result = asyncio.run(scheduler.sweep())

    assert result == {"sources": 2, "scheduled": 1, "unchanged": 1, "failed": 0}
    assert [json.loads(request.content)["user_id"] for request in requests] == ["7", "8"]
    assert all(request.headers["authorization"] == "Bearer gateway-secret" for request in requests)
    assert all("X-SynCode-User-ID" not in request.headers for request in requests)
    asyncio.run(client.aclose())


def test_scheduler_caps_new_profile_runs_per_sweep():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, json={"scheduled": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    scheduler = LearningProfileScheduler(
        SchedulerSettings(
            "http://gateway",
            "gateway-secret",
            batch_size=10,
            max_runs_per_sweep=1,
        ),
        FakeRepository(),  # type: ignore[arg-type]
        client,
    )
    result = asyncio.run(scheduler.sweep())

    assert result == {"sources": 2, "scheduled": 1, "unchanged": 0, "failed": 0}
    assert len(requests) == 1
    asyncio.run(client.aclose())
