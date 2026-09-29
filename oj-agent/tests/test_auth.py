from dataclasses import replace

from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.main import app


client = TestClient(app)


def test_authorization_token_is_resolved_through_backend(monkeypatch):
    import app.api.auth as auth_module  # noqa: WPS433

    settings = replace(load_settings(), auth_base_url="http://friend.test")
    monkeypatch.setattr(auth_module, "load_settings", lambda: settings)
    calls: list[tuple[str, str, float]] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"code": 1000, "data": {"userId": "token-user"}}

    def fake_get(url, *, headers, timeout):
        calls.append((url, headers["Authorization"], timeout))
        return FakeResponse()

    monkeypatch.setattr(auth_module.httpx, "get", fake_get)

    response = client.get(
        "/api/conversations/default",
        headers={"Authorization": "Bearer signed-token"},
    )

    assert response.status_code == 200
    assert response.json()["conversation"]["userId"] == "token-user"
    assert calls == [("http://friend.test/friend/user/detail", "Bearer signed-token", 5.0)]
