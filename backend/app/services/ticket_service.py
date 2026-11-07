from collections.abc import Iterable, Iterator, Mapping
import secrets
import string
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from backend.app.agent.graph import build_graph


_checkpointer = MemorySaver()
graph = build_graph(_checkpointer)


def _cfg(customer_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": customer_id}}


def _snapshot(customer_id: str):
    return graph.get_state(_cfg(customer_id))


def pending_approval(customer_id: str) -> Any | None:
    """Return the active interrupt payload for this customer's graph thread."""
    for task in _snapshot(customer_id).tasks:
        for interruption in task.interrupts:
            return interruption.value
    return None


def _result(customer_id: str) -> dict[str, Any]:
    values = _snapshot(customer_id).values
    selected = {
        key: values.get(key)
        for key in (
            "ticket_id",
            "customer_id",
            "category",
            "sentiment",
            "path",
            "final_reply",
            "refund_result",
            "escalation",
            "review",
            "retries",
        )
    }
    if not selected["refund_result"]:
        if values.get("refund_processed"):
            selected["refund_result"] = "processed"
        elif values.get("category") == "refund":
            selected["refund_result"] = values.get("eligibility_reason", "")
    if not selected["escalation"] and values.get("escalated"):
        selected["escalation"] = values.get("final_reply", "")
    if not selected["review"]:
        if values.get("quality_passed"):
            selected["review"] = "passed"
        else:
            selected["review"] = values.get("quality_feedback", "")
    return selected


def _stream(input: Mapping[str, Any] | Command, customer_id: str) -> Iterator[dict[str, Any]]:
    config = _cfg(customer_id)
    for event in graph.stream(input, config=config, stream_mode="updates"):
        for node, update in event.items():
            if isinstance(update, Mapping):
                clean_update = {key: value for key, value in update.items() if key != "messages"}
            else:
                clean_update = update
            yield {"type": "step", "node": node, "update": clean_update}

    pending = pending_approval(customer_id)
    if pending is not None:
        yield {"type": "awaiting_approval", "payload": pending}
    else:
        yield {"type": "done", "result": _result(customer_id)}


def submit_stream(
    customer_id: str,
    message: str,
    ticket_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Start processing a new ticket in the customer's persistent thread."""
    pending = pending_approval(customer_id)
    if pending is not None:
        raise ValueError("This customer already has a pending approval")

    if ticket_id is None:
        alphabet = string.ascii_uppercase
        ticket_id = "T-" + "".join(secrets.choice(alphabet) for _ in range(6))
    input_state = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "ticket": message,
        "message": message,
    }
    return _stream(input_state, customer_id)


def resume_stream(customer_id: str, decision: Any) -> Iterator[dict[str, Any]]:
    """Resume this customer's interrupted graph after an approval decision."""
    if pending_approval(customer_id) is None:
        raise ValueError("This customer has no pending approval")
    return _stream(Command(resume=decision), customer_id)


def collect(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Consume a stream and return its final completion or approval state."""
    final_event = None
    for event in events:
        final_event = event
    if final_event is None:
        raise ValueError("Cannot collect an empty event stream")
    if final_event.get("type") == "awaiting_approval":
        return {
            "status": "awaiting_approval",
            "pending": final_event.get("payload"),
        }
    if final_event.get("type") == "done":
        return {
            "status": "completed",
            "result": final_event.get("result"),
        }
    raise ValueError("Event stream ended without a completion event")


def history(customer_id: str) -> list[dict[str, str]]:
    """Return saved conversation entries as customer/agent role messages."""
    values = _snapshot(customer_id).values
    messages = values.get("messages")
    if messages:
        result = []
        for message in messages:
            if isinstance(message, Mapping):
                role = message.get("role", "agent")
                content = message.get("content", "")
                is_human = role in {"human", "user", "customer"}
            else:
                role = getattr(message, "type", "")
                content = getattr(message, "content", "")
                is_human = role in {"human", "user"}
            result.append(
                {"role": "customer" if is_human else "agent", "content": str(content)}
            )
        return result

    result = []
    for exchange in values.get("history", []):
        result.append({"role": "customer", "content": exchange.get("ticket", "")})
        result.append({"role": "agent", "content": exchange.get("reply", "")})
    return result
