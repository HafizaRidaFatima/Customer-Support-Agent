from datetime import datetime, timezone

from langchain_core.tools import tool

from backend.app.config import REFUND_APPROVAL_THRESHOLD, REFUND_WINDOW_DAYS
from backend.app.data.orders import orders


@tool
def check_refund_eligibility(order_id: str) -> dict:
    """Check whether an order is eligible for a refund.
    Rules: the order must be within the configured refund window and must not already be refunded.
    """
    order = orders.get(order_id)
    if order is None:
        return {
            "eligible": False,
            "reason": f"Order {order_id} not found",
            "amount": 0.0,
            "needs_approval": False,
        }

    if order.get("refunded", False):
        eligible, reason = False, "This order has already been refunded."
    else:
        try:
            created_at = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            days_since_purchase = (datetime.now(timezone.utc) - created_at).days
        except (TypeError, ValueError):
            days_since_purchase = 0

        refund_window = int(REFUND_WINDOW_DAYS or 30)
        if days_since_purchase > refund_window:
            eligible = False
            reason = (
                f"Order is {days_since_purchase} days old. "
                f"Refunds are allowed only within {refund_window} days."
            )
        else:
            eligible, reason = True, "Order is eligible for a refund."

    amount = float(order.get("total_amount", 0.0))
    return {
        "eligible": eligible,
        "reason": reason,
        "amount": amount,
        "needs_approval": eligible and amount > REFUND_APPROVAL_THRESHOLD,
    }