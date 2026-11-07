from typing import Any

from langgraph.types import interrupt

from backend.app.agent.state import TicketState
from backend.app.data.orders import orders
from backend.app.llm.classifier import classify as classify_message
from backend.app.llm.classifier import extract_order_id
from backend.app.llm.client import _ask
from backend.app.llm.reviewer import review as review_reply
from backend.app.tools.faq_tools import search_faq
from backend.app.tools.refund_tools import check_refund_eligibility


def _ticket_text(state: TicketState) -> str:
    ticket = state.get("ticket") or state.get("message")
    if not ticket:
        raise ValueError("TicketState must include a non-empty 'ticket' or 'message'")
    return ticket


def _path(state: TicketState, node: str) -> list[str]:
    return [*state.get("path", []), node]


def _history_text(state: TicketState) -> str:
    return "\n".join(
        f"Customer: {item.get('ticket', '')}\nAgent: {item.get('reply', '')}"
        for item in state.get("history", [])
    )


def intake(state: TicketState) -> dict[str, Any]:
    """Initialize per-ticket workflow data while preserving provided context."""
    return {
        "ticket": _ticket_text(state),
        "category": "other",
        "sentiment": "Neutral",
        "order_id": None,
        "order": None,
        "eligible": False,
        "eligibility_reason": "",
        "refund_amount": 0.0,
        "needs_approval": False,
        "approval": None,
        "refund_processed": False,
        "refund_result": "",
        "faq_answer": "",
        "escalated": False,
        "escalation": "",
        "draft": "",
        "quality_passed": False,
        "quality_feedback": "",
        "review": "",
        "retries": 0,
        "final_reply": "",
        "tools_used": [],
        "path": ["intake"],
    }


def classify(state: TicketState) -> dict[str, Any]:
    """Classify the ticket and extract any order number."""
    result = classify_message(_ticket_text(state), state.get("history"))
    if not result.get("order_id"):
        for previous in reversed(state.get("history", [])):
            previous_ticket = previous.get("ticket", "")
            previous_reply = previous.get("reply", "")
            order_id = extract_order_id(f"{previous_ticket} {previous_reply}")
            if order_id:
                result["order_id"] = order_id
                break
    return {**result, "path": _path(state, "classify")}


def order_status(state: TicketState) -> dict[str, Any]:
    """Load the requested order details for the reply."""
    order_id = state.get("order_id")
    order = orders.get(order_id) if order_id else None
    return {
        "order": order or {"error": "No order was found. Please check the order number."},
        "path": _path(state, "order_status"),
    }


def refund(state: TicketState) -> dict[str, Any]:
    """Check refund eligibility and record the returned decision."""
    order_id = state.get("order_id")
    if not order_id:
        return {
            "eligible": False,
            "eligibility_reason": "No valid order number was provided.",
            "refund_amount": 0.0,
            "needs_approval": False,
            "path": _path(state, "refund"),
        }

    result = check_refund_eligibility.invoke({"order_id": order_id})
    return {
        "order": orders.get(order_id),
        "eligible": result["eligible"],
        "eligibility_reason": result["reason"],
        "refund_amount": result["amount"],
        "needs_approval": result["needs_approval"],
        "tools_used": [*state.get("tools_used", []), "check_refund_eligibility"],
        "path": _path(state, "refund"),
    }


def approval(state: TicketState) -> dict[str, Any]:
    """Pause for and record a human refund decision."""
    decision = interrupt(
        {
            "message": "Human approval is required for this refund.",
            "customer_id": state.get("customer_id"),
            "order_id": state.get("order_id"),
            "amount": state.get("refund_amount"),
            "ticket": _ticket_text(state),
        }
    )
    approved = str(decision).strip().casefold() in {
        "approved",
        "approve",
        "yes",
        "y",
        "true",
    }
    return {
        "approval": "approved" if approved else "rejected",
        "path": _path(state, "approval"),
    }


def do_refund(state: TicketState) -> dict[str, Any]:
    """Process an approved/low-value refund in the in-memory demo order store."""
    order_id = state.get("order_id")
    order = orders.get(order_id) if order_id else None
    if not state.get("eligible") or order is None:
        raise ValueError("Cannot process a refund for an ineligible or missing order")
    if state.get("needs_approval") and state.get("approval") != "approved":
        raise ValueError("Human approval is required before processing this refund")
    if order.get("refunded"):
        raise ValueError(f"Order {order_id} has already been refunded")

    order["refunded"] = True
    return {
        "order": order,
        "refund_processed": True,
        "refund_result": "processed",
        "tools_used": [*state.get("tools_used", []), "process_refund"],
        "path": _path(state, "do_refund"),
    }


def product_qa(state: TicketState) -> dict[str, Any]:
    """Look up an answer to a product or policy question."""
    answer = search_faq.invoke({"question": _ticket_text(state)})
    return {
        "faq_answer": "" if answer == "NO_MATCH" else answer,
        "tools_used": [*state.get("tools_used", []), "search_faq"],
        "path": _path(state, "product_qa"),
    }


def escalate(state: TicketState) -> dict[str, Any]:
    """Mark the ticket escalated and provide a clear customer response."""
    reply = (
        "Thank you for contacting us, and I am sorry for the trouble. "
        "I have passed your ticket to a senior support agent who will "
        "personally follow up with you shortly."
    )
    history = [*state.get("history", []), {"ticket": _ticket_text(state), "reply": reply}]
    return {
        "escalated": True,
        "escalation": reply,
        "final_reply": reply,
        "history": history,
        "path": _path(state, "escalate"),
    }


def _facts(state: TicketState) -> str:
    keys = (
        "category",
        "order_id",
        "order",
        "eligible",
        "eligibility_reason",
        "refund_amount",
        "refund_processed",
        "faq_answer",
        "escalated",
    )
    return "\n".join(f"{key}: {state[key]}" for key in keys if state.get(key) is not None)


def _fallback_reply(state: TicketState) -> str:
    category = state.get("category")
    order_id = state.get("order_id")
    order = state.get("order") or {}

    if category == "refund":
        if state.get("refund_processed"):
            body = f"Your refund of ${state.get('refund_amount', 0):.2f} for order {order_id} has been processed."
        else:
            reason = state.get("eligibility_reason") or "the refund could not be processed"
            body = f"We could not process a refund for order {order_id or 'provided'} because {reason}."
    elif category == "order_status":
        if order.get("error"):
            body = f"I could not find order {order_id or ''}. Please check the order number and contact us again."
        else:
            body = f"Order {order_id} is currently {order.get('status', 'in progress')}."
    elif category in {"product", "product_question"}:
        body = state.get("faq_answer") or "I could not find a confirmed answer to your question, but our support team can follow up."
    else:
        body = "Thank you for contacting us. Our support team will be happy to help."

    return f"Hi,\n\n{body}"


def draft_reply(state: TicketState) -> dict[str, Any]:
    """Draft a concise, fact-grounded response, with a local fallback."""
    sentiment = str(state.get("sentiment", "")).casefold()
    tone = ""
    if sentiment in {"angry", "negative"}:
        tone = "Use an empathetic tone and begin with a sincere apology.\n"
    elif sentiment == "positive":
        tone = "Use a warm, friendly tone.\n"

    prompt = (
        "You are a customer-support agent. Write a concise, polite response using "
        "only the supplied facts. Do not invent order details, policies, or dates. "
        "If the refund is rejected or ineligible, explain the reason kindly.\n"
        f"{tone}\nPrevious conversation:\n{_history_text(state)}\n\n"
        f"Customer ticket:\n{_ticket_text(state)}\n\nFacts:\n{_facts(state)}"
    )
    if state.get("quality_feedback"):
        prompt += (
            f"\n\nRewrite the previous draft to address this review feedback: "
            f"{state['quality_feedback']}\nPrevious draft:\n{state.get('draft', '')}"
        )
    draft = _ask("You write accurate customer-support replies.", prompt)
    if not isinstance(draft, str) or not draft.strip():
        draft = _fallback_reply(state)

    return {"draft": draft.strip(), "path": _path(state, "draft_reply")}


def quality_check(state: TicketState) -> dict[str, Any]:
    """Review the draft and count failed rewrite attempts."""
    result = review_reply(state, state.get("draft", ""))
    passed = result["passed"]
    issues = result["issues"]
    update: dict[str, Any] = {
        "quality_passed": passed,
        "quality_feedback": "\n".join(issues),
        "review": "passed" if passed else "\n".join(issues),
        "path": _path(state, "quality_check"),
    }
    if not passed:
        update["retries"] = state.get("retries", 0) + 1
    return update


def review(state: TicketState) -> dict[str, Any]:
    """Compatibility alias for the graph's review node."""
    return quality_check(state)


def finalize(state: TicketState) -> dict[str, Any]:
    """Publish the reviewed draft and append it to conversation history."""
    reply = state.get("draft", "")
    history = [*state.get("history", []), {"ticket": _ticket_text(state), "reply": reply}]
    return {
        "final_reply": reply,
        "history": history,
        "path": _path(state, "finalize"),
    }
