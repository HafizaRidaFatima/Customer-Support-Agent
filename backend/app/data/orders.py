orders = {
    "1001": {
        "customer_id": "C001",
        "items": [
            {"item_id": "I001", "quantity": 2, "price": 10.0},
            {"item_id": "I002", "quantity": 1, "price": 20.0},
        ],
        "total_amount": 40.0,
        "status": "pending",
        "created_at": "2023-10-01T10:00:00Z",
    },
    "1002": {
        "customer_id": "C002",
        "items": [{"item_id": "I003", "quantity": 3, "price": 15.0}],
        "total_amount": 45.0,
        "status": "pending",
        "created_at": "2023-10-02T14:30:00Z",
    },
    "1003": {
        "customer_id": "C003",
        "items": [
            {"item_id": "I004", "quantity": 1, "price": 50.0},
            {"item_id": "I005", "quantity": 2, "price": 25.0},
        ],
        "total_amount": 100.0,
        "status": "pending",
        "created_at": "2023-10-03T09:15:00Z",
    },
    "1004": {
        "customer_id": "C004",
        "items": [{"item_id": "I006", "quantity": 1, "price": 30.0}],
        "total_amount": 30.0,
        "status": "pending",
        "created_at": "2023-10-04T11:45:00Z",
    },
    "1005": {
        "customer_id": "C005",
        "items": [
            {"item_id": "I007", "quantity": 2, "price": 12.0},
            {"item_id": "I008", "quantity": 1, "price": 18.0},
        ],
        "total_amount": 42.0,
        "status": "pending",
        "created_at": "2023-10-05T16:20:00Z",
    },
    "1006": {
        "customer_id": "C006",
        "items": [{"item_id": "I009", "quantity": 1, "price": 40.0}],
        "total_amount": 40.0,
        "status": "pending",
        "created_at": "2023-10-06T13:10:00Z",
    },
    "1007": {
        "customer_id": "C007",
        "items": [{"item_id": "I010", "quantity": 3, "price": 8.0}],
        "total_amount": 24.0,
        "status": "pending",
        "created_at": "2023-10-07T15:55:00Z",
    },
    "1008": {
        "customer_id": "C008",
        "items": [
            {"item_id": "I011", "quantity": 2, "price": 22.0},
            {"item_id": "I012", "quantity": 1, "price": 28.0},
        ],
        "total_amount": 72.0,
        "status": "pending",
        "created_at": "2023-10-08T12:40:00Z",
    },
    "1009": {
        "customer_id": "C009",
        "items": [{"item_id": "I013", "quantity": 1, "price": 35.0}],
        "total_amount": 35.0,
        "status": "pending",
        "created_at": "2023-10-09T14:05:00Z",
    },
    "1010": {
        "customer_id": "C010",
        "items": [
            {"item_id": "I014", "quantity": 2, "price": 18.0},
            {"item_id": "I015", "quantity": 1, "price": 25.0},
        ],
        "total_amount": 61.0,
        "status": "pending",
        "created_at": "2023-10-10T11:30:00Z",
    },
}

orders["1001"]["status"] = "shipped"
orders["1002"]["status"] = "shipped"
orders["1003"]["status"] = "shipped"
orders["1004"]["status"] = "processing"
orders["1005"]["status"] = "processing"
orders["1006"]["status"] = "processing"
orders["1007"]["status"] = "delivered"
orders["1008"]["status"] = "delivered"
orders["1009"]["status"] = "delivered"
orders["1010"]["status"] = "delivered"

for order_id, order_data in orders.items():
    if order_data["status"] == "shipped":
        order_data["shipped_at"] = "2023-10-11T10:00:00Z"
    elif order_data["status"] == "processing":
        order_data["estimated_delivery"] = "2023-10-15T10:00:00Z"
    elif order_data["status"] == "delivered":
        order_data["delivered_at"] = "2023-10-12T10:00:00Z"