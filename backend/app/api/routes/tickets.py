from typing import Any

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_current_user
from backend.app.data.samples import Tickets


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/samples")
def list_samples(
    _: dict[str, Any] = Depends(get_current_user),
) -> list[dict[int, dict[str, str]]]:
    return Tickets
