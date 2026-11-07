import json
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.api.deps import require_agent
from backend.app.schemas.approval import Approval_Decision
from backend.app.services.ticket_service import pending_approval, resume_stream


router = APIRouter(prefix="/approvals", tags=["approvals"])


def _encode_events(events: Iterable[Mapping[str, Any]]) -> Iterator[str]:
    for event in events:
        yield json.dumps(event) + "\n"


@router.get("/{customer_id}")
def get_pending_approval(
    customer_id: str,
    _: dict[str, Any] = Depends(require_agent),
) -> dict[str, Any]:
    return {
        "customer_id": customer_id,
        "pending": pending_approval(customer_id),
    }


@router.post("/{customer_id}/stream")
def resume_ticket_stream(
    customer_id: str,
    decision: Approval_Decision,
    _: dict[str, Any] = Depends(require_agent),
) -> StreamingResponse:
    try:
        events = resume_stream(
            customer_id,
            "approved" if decision.approved else "rejected",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return StreamingResponse(
        _encode_events(events),
        media_type="application/x-ndjson",
    )
