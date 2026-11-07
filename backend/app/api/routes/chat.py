import json
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.api.deps import get_current_user
from backend.app.schemas.chat import ChatRequest
from backend.app.services.ticket_service import collect, history, submit_stream


router = APIRouter(prefix="/chat", tags=["chat"])


def _customer_id(user: dict[str, Any]) -> str:
    customer_id = user.get("customer_id") or user.get("username")
    if not isinstance(customer_id, str) or not customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A customer identity is required to access chat.",
        )
    return customer_id


def _start_stream(customer_id: str, message: str) -> Iterator[dict[str, Any]]:
    try:
        return submit_stream(customer_id, message)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


def _encode_events(events: Iterable[Mapping[str, Any]]) -> Iterator[str]:
    for event in events:
        yield json.dumps(event) + "\n"


@router.post("/send")
def send_message(
    body: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    customer_id = _customer_id(user)
    events = _start_stream(customer_id, body.message)
    return collect(events)


@router.post("/stream")
def stream_message(
    body: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    customer_id = _customer_id(user)
    events = _start_stream(customer_id, body.message)
    return StreamingResponse(
        _encode_events(events),
        media_type="application/x-ndjson",
    )


@router.get("/history")
def get_chat_history(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    customer_id = _customer_id(user)
    return {
        "customer_id": customer_id,
        "messages": history(customer_id),
    }
