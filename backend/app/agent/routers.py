from typing import Literal, Mapping

from backend.app.config import MAX_REWRITES, REFUND_APPROVAL_THRESHOLD


Route = Literal[
    "escalate",
    "refund_check",
    "order_status",
    "product_answer",
    "draft_reply",
    "human_approval",
    "do_refund",
    "finalize",
]


def route_ticket(state: Mapping[str, object]) -> Route:
    """Choose the next ticket-handling node from its category and sentiment."""
    category = state.get("category")
    sentiment = state.get("sentiment")

    if (isinstance(sentiment, str) and sentiment.casefold() == "angry") or category == "other":
        return "escalate"

    routes: dict[str, Route] = {
        "refund": "refund_check",
        "order_status": "order_status",
        "product": "product_answer",
    }
    return routes.get(category, "escalate") if isinstance(category, str) else "escalate"


def route_refund(state: Mapping[str, object]) -> Route:
    """Choose the next step after checking refund eligibility."""
    if not state.get("eligible"):
        return "draft_reply"

    amount = state.get("refund_amount", 0.0)
    if not isinstance(amount, (int, float)):
        raise TypeError("refund_amount must be a number")

    if amount > REFUND_APPROVAL_THRESHOLD:
        return "human_approval"
    return "do_refund"


def route_approval(state: Mapping[str, object]) -> Route:
    """Send approved refunds for processing and rejected ones for a reply."""
    approval = state.get("approval")
    if approval is True or (
        isinstance(approval, str) and approval.casefold() == "approved"
    ):
        return "do_refund"
    return "draft_reply"


def route_review(state: Mapping[str, object]) -> Route:
    """Finish when review passes or rewrite attempts exceed the configured limit."""
    if state.get("quality_passed"):
        return "finalize"

    retries = state.get("retries", 0)
    if not isinstance(retries, int):
        raise TypeError("retries must be an integer")
    if retries > int(MAX_REWRITES):
        return "finalize"
    return "draft_reply"