from langgraph.graph import END, START, StateGraph

from backend.app.agent.nodes import (
    approval,
    classify,
    do_refund,
    draft_reply,
    escalate,
    finalize,
    intake,
    order_status,
    product_qa,
    quality_check,
    refund,
)
from backend.app.agent.routers import (
    route_approval,
    route_refund,
    route_review,
    route_ticket,
)
from backend.app.agent.state import TicketState


def build_graph(checkpointer: object | None = None):
    builder = StateGraph(TicketState)

    builder.add_node("intake", intake)
    builder.add_node("classify", classify)
    builder.add_node("order_status", order_status)
    builder.add_node("refund_check", refund)
    builder.add_node("human_approval", approval)
    builder.add_node("do_refund", do_refund)
    builder.add_node("product_answer", product_qa)
    builder.add_node("escalate", escalate)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("review", quality_check)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "classify")
    builder.add_conditional_edges(
        "classify",
        route_ticket,
        {
            "escalate": "escalate",
            "refund_check": "refund_check",
            "order_status": "order_status",
            "product_answer": "product_answer",
        },
    )
    builder.add_conditional_edges(
        "refund_check",
        route_refund,
        {
            "draft_reply": "draft_reply",
            "human_approval": "human_approval",
            "do_refund": "do_refund",
        },
    )
    builder.add_conditional_edges(
        "human_approval",
        route_approval,
        {"do_refund": "do_refund", "draft_reply": "draft_reply"},
    )
    builder.add_edge("do_refund", "draft_reply")
    builder.add_edge("order_status", "draft_reply")
    builder.add_edge("product_answer", "draft_reply")
    builder.add_edge("draft_reply", "review")
    builder.add_conditional_edges(
        "review",
        route_review,
        {"draft_reply": "draft_reply", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)
    builder.add_edge("escalate", END)

    return builder.compile(checkpointer=checkpointer)
