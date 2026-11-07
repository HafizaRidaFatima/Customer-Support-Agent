from typing import Literal, TypedDict


Category = Literal["refund", "order_status", "product", "product_question", "other"]
Sentiment = Literal[
    "Angry",
    "Negative",
    "Positive",
    "Neutral",
    "angry",
    "negative",
    "positive",
    "neutral",
]
Approval = Literal["approved", "rejected"]


class TicketState(TypedDict, total=False):
    ticket_id: str
    customer_id: str
    ticket: str
    message: str
    category: Category
    sentiment: Sentiment
    order_id: str | None
    order: dict[str, object] | None
    eligible: bool
    eligibility_reason: str
    refund_amount: float
    needs_approval: bool
    approval: Approval | None
    refund_processed: bool
    refund_result: str
    faq_answer: str
    escalated: bool
    escalation: str
    draft: str
    quality_passed: bool
    quality_feedback: str
    review: str
    retries: int
    final_reply: str
    tools_used: list[str]
    path: list[str]
    history: list[dict[str, str]]
