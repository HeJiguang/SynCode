from fastapi import APIRouter, HTTPException, Request, status

from app.api.auth import resolve_request_user_id
from app.api.serializers import to_api_model
from app.conversations import get_conversation_service
from app.domain.conversations import Conversation, ConversationSnapshot
from app.schemas.conversation_api import CreateConversationRequest


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conversation_payload(conversation: Conversation) -> dict:
    payload = conversation.model_dump(mode="json")
    payload["rollover_recommended"] = conversation.rollover_recommended
    payload["hard_limit_reached"] = conversation.hard_limit_reached
    return to_api_model(payload)


def _snapshot_payload(snapshot: ConversationSnapshot) -> dict:
    return {
        "conversation": _conversation_payload(snapshot.conversation),
        "messages": to_api_model([message.model_dump(mode="json") for message in snapshot.messages]),
        "contextMemories": to_api_model(
            [memory.model_dump(mode="json") for memory in snapshot.context_memories]
        ),
    }


@router.get("")
def list_conversations(raw_request: Request) -> list[dict]:
    user_id = resolve_request_user_id(raw_request)
    return [_conversation_payload(item) for item in get_conversation_service().list_conversations(user_id)]


@router.get("/default")
def get_default_conversation(raw_request: Request) -> dict:
    user_id = resolve_request_user_id(raw_request)
    return _snapshot_payload(get_conversation_service().get_default(user_id))


@router.post("")
def create_conversation(request: CreateConversationRequest, raw_request: Request) -> dict:
    user_id = resolve_request_user_id(raw_request)
    try:
        snapshot = get_conversation_service().create_continuation(
            user_id,
            title=request.title.strip() or "新的学习对话",
            continued_from_conversation_id=request.continued_from_conversation_id,
            memory_ids=request.memory_ids,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat 或记忆不存在。") from exc
    return _snapshot_payload(snapshot)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, raw_request: Request) -> dict:
    user_id = resolve_request_user_id(raw_request)
    try:
        return _snapshot_payload(get_conversation_service().get_snapshot(conversation_id, user_id))
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat 不存在。") from exc


@router.get("/{conversation_id}/memory-candidates")
def list_memory_candidates(conversation_id: str, raw_request: Request) -> list[dict]:
    user_id = resolve_request_user_id(raw_request)
    try:
        memories = get_conversation_service().memory_candidates(user_id, conversation_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat 不存在。") from exc
    return to_api_model([memory.model_dump(mode="json") for memory in memories])

