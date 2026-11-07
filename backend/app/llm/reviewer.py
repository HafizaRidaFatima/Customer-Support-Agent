from collections.abc import Mapping
import json

from .client import _ask, _json
from .classifier import extract_order_id


def _fallback_issues(state: Mapping[str, object], text: str) -> list[str]:
    issues = []
    reply = text.strip()

    if len(reply) < 40:
        issues.append("Reply must be at least 40 characters long.")
    if not reply.startswith("Hi"):
        issues.append("Reply must start with 'Hi'.")
    if "best regards" in reply.casefold():
        issues.append("Reply must not contain 'Best regards'.")
    if "{" in reply or "}" in reply or "todo" in reply.casefold():
        issues.append("Reply must not contain braces or TODO.")

    category = state.get("category")
    if category in {"order", "order_status", "refund"} and extract_order_id(reply) is None:
        issues.append("Order and refund replies must include an order number.")

    return issues


def review(state: Mapping[str, object], text: str) -> dict[str, object]:
    """Review a support reply with Claude, falling back to required format checks."""
    prompt = (
        "Review this customer-support reply. Check that it has at least 40 "
        "characters, starts with 'Hi', does not contain 'Best regards', "
        "contains no braces or TODO, and includes an order number when the "
        "category is order_status or refund. Return only JSON with a boolean "
        "'passed' and a list of string 'issues'.\n"
        f"{json.dumps({'state': state, 'text': text}, ensure_ascii=False, default=str)}"
    )
    parsed = _json(_ask("You are a customer-support reply reviewer.", prompt))

    if (
        isinstance(parsed, dict)
        and isinstance(parsed.get("passed"), bool)
        and isinstance(parsed.get("issues"), list)
        and all(isinstance(issue, str) for issue in parsed["issues"])
    ):
        issues = [issue.strip() for issue in parsed["issues"] if issue.strip()]
    else:
        issues = _fallback_issues(state, text)

    return {"passed": not issues, "issues": issues}
