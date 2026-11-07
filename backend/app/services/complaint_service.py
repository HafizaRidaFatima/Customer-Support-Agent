from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from backend.app.config import DATABASE_URL, REFUND_APPROVAL_THRESHOLD


_REFUND_APPROVAL_THRESHOLD = Decimal(str(REFUND_APPROVAL_THRESHOLD))


def _connect() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be configured to store complaints.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _initialize_complaint_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS support_complaints (
                id BIGSERIAL PRIMARY KEY,
                username TEXT NOT NULL REFERENCES registered_users(username)
                    ON DELETE CASCADE,
                product_name TEXT NOT NULL,
                order_id TEXT,
                complaint TEXT NOT NULL,
                refund_amount NUMERIC(12, 2),
                status TEXT NOT NULL CHECK (
                    status IN ('open', 'pending_approval', 'approved', 'rejected')
                ),
                reviewer TEXT,
                admin_note TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS support_complaints_username_created_idx
            ON support_complaints (username, created_at DESC)
            """
        )


_initialize_complaint_database()


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if result.get("refund_amount") is not None:
        result["refund_amount"] = float(result["refund_amount"])
    for key in ("created_at", "updated_at"):
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    result["requires_approval"] = (
        result.get("refund_amount") is not None
        and Decimal(str(result["refund_amount"])) > _REFUND_APPROVAL_THRESHOLD
    )
    return result


def create_complaint(username: str, values: dict[str, Any]) -> dict[str, Any]:
    product_name = values["product_name"].strip()
    complaint = values["complaint"].strip()
    order_id = values.get("order_id")
    order_id = order_id.strip() if order_id and order_id.strip() else None
    refund_amount = values.get("refund_amount")
    status = (
        "pending_approval"
        if refund_amount is not None
        and refund_amount > _REFUND_APPROVAL_THRESHOLD
        else "open"
    )

    if not product_name:
        raise ValueError("Product name is required.")
    if not complaint:
        raise ValueError("Complaint details are required.")

    with _connect() as connection:
        row = connection.execute(
            """
            INSERT INTO support_complaints (
                username, product_name, order_id, complaint,
                refund_amount, status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, username, product_name, order_id, complaint,
                      refund_amount, status, reviewer, admin_note,
                      created_at, updated_at
            """,
            (
                username,
                product_name,
                order_id,
                complaint,
                refund_amount,
                status,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("The complaint was not returned after saving.")
    return _serialize(row)


def customer_complaints(username: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, username, product_name, order_id, complaint,
                   refund_amount, status, reviewer, admin_note,
                   created_at, updated_at
            FROM support_complaints
            WHERE username = %s
            ORDER BY created_at DESC, id DESC
            """,
            (username,),
        ).fetchall()
    return [_serialize(row) for row in rows]


def all_complaints() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.username, u.email, c.product_name, c.order_id,
                   c.complaint, c.refund_amount, c.status, c.reviewer,
                   c.admin_note, c.created_at, c.updated_at
            FROM support_complaints AS c
            JOIN registered_users AS u ON u.username = c.username
            ORDER BY c.created_at DESC, c.id DESC
            """
        ).fetchall()
    return [_serialize(row) for row in rows]


def decide_complaint(
    complaint_id: int,
    approved: bool,
    reviewer: str,
    note: str,
) -> dict[str, Any]:
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("Reviewer name is required.")

    with _connect() as connection:
        row = connection.execute(
            """
            UPDATE support_complaints
            SET status = %s, reviewer = %s, admin_note = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND status = 'pending_approval'
              AND refund_amount > %s
            RETURNING id, username, product_name, order_id, complaint,
                      refund_amount, status, reviewer, admin_note,
                      created_at, updated_at
            """,
            (
                "approved" if approved else "rejected",
                reviewer,
                note.strip(),
                complaint_id,
                _REFUND_APPROVAL_THRESHOLD,
            ),
        ).fetchone()
        if row is None:
            exists = connection.execute(
                "SELECT 1 FROM support_complaints WHERE id = %s",
                (complaint_id,),
            ).fetchone()
            if exists is None:
                raise LookupError("Complaint not found.")
            raise ValueError("This complaint is not awaiting refund approval.")
    return _serialize(row)
