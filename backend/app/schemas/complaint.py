from decimal import Decimal

from pydantic import BaseModel, Field


class ComplaintCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=160)
    order_id: str | None = Field(default=None, max_length=100)
    complaint: str = Field(min_length=1, max_length=5000)
    refund_amount: Decimal | None = Field(
        default=None, gt=0, le=9999999.99, decimal_places=2
    )


class ComplaintDecision(BaseModel):
    approved: bool
    reviewer: str = Field(min_length=1, max_length=160)
    note: str = Field(default="", max_length=2000)
