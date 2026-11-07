from langchain_core.tools import tool
from backend.app.data.orders import orders


@tool
def get_order(order_id: str) -> dict:
    """Return the details of an order (product, amount, status, date) by order ID."""
    order = orders.get(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}
    return order
