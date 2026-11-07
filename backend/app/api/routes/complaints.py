from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_current_user, require_admin
from backend.app.schemas.complaint import ComplaintCreate, ComplaintDecision
from backend.app.services.complaint_service import (
    all_complaints,
    create_complaint,
    customer_complaints,
    decide_complaint,
)


router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_complaint(
    body: ComplaintCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if user.get("role") != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access is required to submit a complaint.",
        )
    if not body.product_name.strip() or not body.complaint.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product name and complaint details are required.",
        )
    try:
        return create_complaint(user["username"], body.dict())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/mine")
def get_my_complaints(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    if user.get("role") != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access is required to view complaint history.",
        )
    return customer_complaints(user["username"])


@router.get("")
def get_all_complaints(
    _: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    return all_complaints()


@router.post("/{complaint_id}/decision")
def review_complaint(
    complaint_id: int,
    body: ComplaintDecision,
    _: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return decide_complaint(
            complaint_id,
            body.approved,
            body.reviewer,
            body.note,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
