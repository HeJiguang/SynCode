from fastapi import HTTPException, Request, status
import httpx

from app.core.config import load_settings


def resolve_request_user_id(request: Request, requested_user_id: str | None = None) -> str:
    settings = load_settings()
    trusted_user_id = (request.headers.get(settings.gateway_user_id_header) or "").strip()
    if trusted_user_id:
        return trusted_user_id

    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization and settings.auth_base_url:
        return _resolve_user_from_backend(settings.auth_base_url, authorization)

    if settings.allow_insecure_user_id_body and requested_user_id:
        return requested_user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="缺少经过网关验证的用户身份。",
    )


def assert_owned_user(actual_user_id: str, request_user_id: str) -> None:
    if actual_user_id != request_user_id:
        # Return not-found so callers cannot enumerate another user's resources.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在。")


def _resolve_user_from_backend(base_url: str, authorization: str) -> str:
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/friend/user/detail",
            headers={"Authorization": authorization},
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证当前登录状态。",
        ) from exc

    data = payload.get("data") if isinstance(payload, dict) and payload.get("code") == 1000 else None
    user_id = data.get("userId") if isinstance(data, dict) else None
    if user_id is None or not str(user_id).strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="当前登录状态无效。")
    return str(user_id)

