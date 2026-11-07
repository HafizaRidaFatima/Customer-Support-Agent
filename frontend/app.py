"""SupportDesk AI - Streamlit complaint and support frontend.

Run:  BACKEND_URL=http://127.0.0.1:8000 streamlit run app.py

Product API contract expected from the backend (all under /api, Bearer token):
  GET    /products                 -> list[Product]  (or {"products": [...]})
  POST   /products                 -> Product        (admin only)
  PUT    /products/{product_id}    -> Product        (admin only)
  DELETE /products/{product_id}    -> {"message": "..."} (admin only)

Product = {id, name, sku, category, price, stock, description, image_url}
"""

import html
import json
import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API_URL = f"{BACKEND_URL}/api"

st.set_page_config(page_title="SupportDesk AI", page_icon="🎧", layout="wide")

# ---------------------------------------------------------------- styling
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

      :root {
        --ink: #1f2a44;
        --muted: #667085;
        --line: rgba(128,128,128,.28);
        --accent: #0f8b8d;
        --warn: #c98a12;
        --danger: #c0392b;
      }
      /* Apply the font everywhere EXCEPT icon glyphs, which use an icon font */
      html, body, .stApp,
      .stApp *:not([data-testid="stIconMaterial"]):not([class*="material"]):not([class*="Icon"]):not(svg):not(path) {
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      }
      [data-testid="stIconMaterial"], [class*="material-symbols"], .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
      }
      .block-container { max-width: 1100px; padding-top: 2rem; padding-bottom: 4rem; }
      h1, h2, h3 { letter-spacing: -0.015em; font-weight: 700; }

      /* page header */
      .page-head { margin-bottom: 1.25rem; }
      .page-head h1 { margin: 0; padding: 0; font-size: 1.9rem; }
      .page-head p  { margin: .25rem 0 0; color: var(--muted); }

      /* stat strip */
      .stat {
        border: 1px solid var(--line); border-radius: 10px;
        padding: .85rem 1rem; height: 100%;
      }
      .stat .v { font-size: 1.55rem; font-weight: 700; line-height: 1.1; }
      .stat .l { color: var(--muted); font-size: .85rem; margin-top: .2rem; }

      /* product card */
      .p-name  { font-weight: 700; font-size: 1.05rem; margin: 0; }
      .p-meta  { color: var(--muted); font-size: .82rem; margin: .1rem 0 .5rem; }
      .p-desc  { font-size: .92rem; margin: .4rem 0 .6rem; }
      .p-price { font-size: 1.25rem; font-weight: 700; }
      .badge {
        display: inline-block; padding: .1rem .55rem; border-radius: 999px;
        font-size: .75rem; font-weight: 600; border: 1px solid var(--line);
      }
      .badge.ok   { color: var(--accent); border-color: var(--accent); }
      .badge.low  { color: var(--warn);   border-color: var(--warn); }
      .badge.out  { color: var(--danger); border-color: var(--danger); }

      /* approval card */
      .pending-card {
        border: 1px solid var(--line); border-left: 4px solid var(--accent);
        border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem;
      }
      .pending-card p { margin: .15rem 0; }

      [data-testid="stSidebar"] .stRadio label { font-weight: 500; }
      a:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULTS = {
    "token": None,
    "role": None,
    "customer_id": None,
    "username": None,
    "result": None,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


# ---------------------------------------------------------------- API layer
def _headers(extra=None):
    headers = dict(extra or {})
    if st.session_state["token"]:
        headers["Authorization"] = f"Bearer {st.session_state['token']}"
    return headers


def _error_detail(exc):
    """Pull a readable message out of a failed requests call."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return str(exc)
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        return resp.text or str(exc)
    if isinstance(detail, list):
        msgs = [d["msg"] for d in detail if isinstance(d, dict) and "msg" in d]
        return "; ".join(msgs) or str(detail)
    return str(detail)


def api(method, path, **kwargs):
    """One-shot JSON call. Raises RuntimeError with a user-friendly message."""
    try:
        resp = requests.request(
            method,
            f"{API_URL}{path}",
            headers=_headers(kwargs.pop("headers", None)),
            timeout=15,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(_error_detail(exc)) from exc
    except ValueError as exc:
        raise RuntimeError("The server sent an invalid response.") from exc


def stream(path, body):
    """Yield JSON events from an NDJSON or SSE endpoint."""
    headers = _headers({"Accept": "application/x-ndjson, text/event-stream"})
    try:
        with requests.post(
            f"{API_URL}{path}", json=body, headers=headers,
            timeout=(15, 120), stream=True,
        ) as resp:
            resp.raise_for_status()
            buf = []
            for line in resp.iter_lines(decode_unicode=True):
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    buf.append(line[5:].strip())
                elif line and not line.startswith(":"):
                    yield json.loads(line)
                elif not line and buf:
                    yield json.loads("\n".join(buf))
                    buf.clear()
            if buf:
                yield json.loads("\n".join(buf))
    except requests.RequestException as exc:
        raise RuntimeError(_error_detail(exc)) from exc
    except ValueError as exc:
        raise RuntimeError("The server sent an invalid stream event.") from exc


# ---------------------------------------------------------------- helpers
def logout():
    st.session_state.clear()
    st.rerun()


def page_header(title, subtitle=""):
    sub = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="page-head"><h1>{html.escape(title)}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def stat(col, value, label):
    col.markdown(
        f'<div class="stat"><div class="v">{html.escape(str(value))}</div>'
        f'<div class="l">{html.escape(label)}</div></div>',
        unsafe_allow_html=True,
    )


def money(value):
    return f"${value:,.2f}" if isinstance(value, (int, float)) else (value or "—")


def run_stream(path, body, label):
    """Show live progress while streaming; store the final result."""
    st.session_state["result"] = None
    with st.status(label, expanded=True) as status:
        try:
            for event in stream(path, body):
                kind = event.get("type")
                if kind == "step":
                    st.write(f"✓ {event.get('node', 'Working')}")
                elif kind == "awaiting_approval":
                    status.update(label="Waiting for an agent to review", state="complete")
                elif kind == "done":
                    st.session_state["result"] = event.get("result")
            else:
                if status.label == label:
                    status.update(label="Done", state="complete")
        except RuntimeError as exc:
            status.update(label="Something went wrong", state="error")
            st.error(str(exc))
    return st.session_state["result"]


def show_result(result):
    if result is None:
        return
    reply = result.get("final_reply") if isinstance(result, dict) else result
    if reply:
        with st.chat_message("assistant"):
            st.write(reply)
    if isinstance(result, dict):
        with st.expander("Details"):
            st.json(result)


# ---------------------------------------------------------------- login
def login_tab():
    kind = st.radio("Log in as", ["Customer", "Admin"], horizontal=True, key="login_kind")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        go = st.form_submit_button("Log in", use_container_width=True, type="primary")
    if not go:
        return
    try:
        token = api("POST", "/auth/log-in", json={"username": username, "password": password}).get("access_token")
        if not token:
            raise RuntimeError("Login did not return an access token.")
        st.session_state["token"] = token
        user = api("GET", "/auth/me")["user"]
    except (RuntimeError, KeyError) as exc:
        st.session_state["token"] = None
        st.error(str(exc))
        return

    role = user.get("role")
    ok = role == "customer" if kind == "Customer" else role in {"admin", "agent"}
    if not ok:
        st.session_state["token"] = None
        st.error(f"This account isn't a {kind.lower()} account.")
        return
    st.session_state.update(
        role=role,
        username=user.get("username"),
        customer_id=user.get("customer_id") or user.get("username"),
    )
    st.rerun()


def register_tab():
    kind = st.radio("Register as", ["Customer", "Admin"], horizontal=True, key="reg_kind")
    with st.form("register"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password (8+ characters)", type="password")
        code = st.text_input("Admin registration code", type="password") if kind == "Admin" else None
        go = st.form_submit_button("Create account", use_container_width=True, type="primary")
    if not go:
        return
    body = {"username": username, "email": email, "password": password}
    if code is not None:
        body["admin_code"] = code
    path = "/auth/register/admin" if kind == "Admin" else "/auth/register/user"
    try:
        st.success(api("POST", path, json=body).get("message", "Account created. You can log in now."))
    except RuntimeError as exc:
        st.error(str(exc))


def render_login():
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        page_header("🎧 SupportDesk AI", "Sign in to get help or review requests.")
        t1, t2 = st.tabs(["Log in", "Register"])
        with t1:
            login_tab()
        with t2:
            register_tab()


# ---------------------------------------------------------------- customer
def render_customer():
    page_header(
        "Submit a complaint",
        "Add the product details and tell us what went wrong. Refund requests over $100 need admin approval.",
    )
    with st.form("customer_complaint_form", clear_on_submit=True):
        product_name = st.text_input("Product name *", max_chars=160)
        order_id = st.text_input("Order ID (optional)", max_chars=100)
        refund_amount = st.number_input(
            "Refund amount requested (optional)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            format="%.2f",
            help="Requests above $100 are held for admin approval.",
        )
        complaint = st.text_area("What happened? *", max_chars=5000, height=160)
        submitted = st.form_submit_button(
            "Submit complaint", type="primary", use_container_width=True
        )

    if submitted:
        if not product_name.strip() or not complaint.strip():
            st.error("Enter both a product name and complaint details.")
        else:
            payload = {
                "product_name": product_name.strip(),
                "order_id": order_id.strip() or None,
                "complaint": complaint.strip(),
                "refund_amount": refund_amount if refund_amount > 0 else None,
            }
            try:
                saved = api("POST", "/complaints", json=payload)
                if saved.get("status") == "pending_approval":
                    st.success(
                        f"Complaint #{saved['id']} submitted. An admin must approve "
                        "the refund request."
                    )
                else:
                    st.success(f"Complaint #{saved['id']} submitted for support review.")
            except RuntimeError as exc:
                st.error(f"Couldn't submit complaint: {exc}")


def render_customer_history():
    page_header("My complaints", "Your submitted complaints and refund request status.")
    try:
        complaints = api("GET", "/complaints/mine")
    except RuntimeError as exc:
        st.error(f"Couldn't load your complaint history: {exc}")
        return
    if not complaints:
        st.info("You haven't submitted any complaints yet.")
        return

    for item in complaints:
        amount = item.get("refund_amount")
        title = f"#{item['id']} · {item['product_name']} · {item['status'].replace('_', ' ').title()}"
        with st.expander(title):
            st.write(f"**Submitted:** {item.get('created_at', '—')}")
            st.write(f"**Order ID:** {item.get('order_id') or '—'}")
            st.write(f"**Refund requested:** {money(amount) if amount is not None else 'No'}")
            st.write("**Complaint:**")
            st.write(item["complaint"])
            if item.get("admin_note"):
                st.write(f"**Admin note:** {item['admin_note']}")


def render_admin_complaints():
    page_header(
        "Customer complaints",
        "Review the complete complaint history. Passwords are stored as hashes and are never shown.",
    )
    try:
        complaints = api("GET", "/complaints")
    except RuntimeError as exc:
        st.error(f"Couldn't load complaints: {exc}")
        return

    pending = sum(item.get("status") == "pending_approval" for item in complaints)
    c1, c2 = st.columns(2)
    stat(c1, len(complaints), "Total complaints")
    stat(c2, pending, "Refunds awaiting approval")
    st.write("")
    if not complaints:
        st.info("No customer complaints have been submitted.")
        return

    for item in complaints:
        amount = item.get("refund_amount")
        title = (
            f"#{item['id']} · {item['username']} · {item['product_name']} · "
            f"{item['status'].replace('_', ' ').title()}"
        )
        with st.expander(title, expanded=item.get("status") == "pending_approval"):
            st.write(f"**Email:** {item.get('email') or '—'}")
            st.write(f"**Submitted:** {item.get('created_at', '—')}")
            st.write(f"**Order ID:** {item.get('order_id') or '—'}")
            st.write(f"**Refund requested:** {money(amount) if amount is not None else 'No'}")
            st.write("**Complaint:**")
            st.write(item["complaint"])

            if item.get("status") == "pending_approval":
                with st.form(f"complaint_decision_{item['id']}"):
                    reviewer = st.text_input("Admin name", key=f"reviewer_{item['id']}")
                    note = st.text_area("Decision note", key=f"note_{item['id']}")
                    approve_col, reject_col = st.columns(2)
                    approve = approve_col.form_submit_button(
                        "Approve refund", type="primary", use_container_width=True
                    )
                    reject = reject_col.form_submit_button(
                        "Reject refund", use_container_width=True
                    )
                if approve or reject:
                    if not reviewer.strip():
                        st.error("Enter your name before deciding.")
                    else:
                        try:
                            api(
                                "POST",
                                f"/complaints/{item['id']}/decision",
                                json={
                                    "approved": bool(approve),
                                    "reviewer": reviewer.strip(),
                                    "note": note.strip(),
                                },
                            )
                            st.success("Refund decision saved.")
                            st.rerun()
                        except RuntimeError as exc:
                            st.error(f"Couldn't save decision: {exc}")
            elif item.get("reviewer"):
                st.write(f"**Reviewed by:** {item['reviewer']}")
                if item.get("admin_note"):
                    st.write(f"**Admin note:** {item['admin_note']}")
            elif amount is not None and amount <= 100:
                st.caption("This refund request does not require admin approval.")


# ---------------------------------------------------------------- agent
def render_ai_approvals():
    page_header("Approvals", "Review refund requests waiting for a decision.")
    try:
        customers = api("GET", "/customers")
    except RuntimeError as exc:
        st.error(str(exc))
        return
    if not customers:
        st.info("No customers yet.")
        return

    labels = {f"{c['name']} ({c['customer_id']})": c["customer_id"] for c in customers}
    cid = labels[st.selectbox("Customer", list(labels))]

    try:
        pending = api("GET", f"/approvals/{cid}").get("pending")
    except RuntimeError as exc:
        st.error(str(exc))
        pending = None

    if not isinstance(pending, dict):
        st.info("Nothing waiting for approval for this customer.")
        show_result(st.session_state["result"])
        return

    st.markdown(
        f"""
        <div class="pending-card">
          <p><strong>{html.escape(str(pending.get('message', 'A refund decision is required.')))}</strong></p>
          <p>Ticket: {html.escape(str(pending.get('ticket_id') or pending.get('ticket', '—')))}</p>
          <p>Order: {html.escape(str(pending.get('order_id', '—')))}</p>
          <p>Amount: {html.escape(money(pending.get('amount')))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("decision"):
        reviewer = st.text_input("Your name")
        note = st.text_area("Decision note")
        c1, c2 = st.columns(2)
        approve = c1.form_submit_button("Approve refund", type="primary", use_container_width=True)
        reject = c2.form_submit_button("Reject refund", use_container_width=True)

    if approve or reject:
        if not reviewer.strip():
            st.error("Enter your name before deciding.")
        else:
            run_stream(
                f"/approvals/{cid}/stream",
                {"approved": bool(approve), "reviewer": reviewer.strip(), "note": note.strip()},
                "Recording your decision…",
            )
            show_result(st.session_state["result"])


# ---------------------------------------------------------------- router
PAGES = {
    "customer": {
        "Submit complaint": render_customer,
        "My complaints": render_customer_history,
    },
    "agent": {"AI approvals": render_ai_approvals},
    "admin": {"Customer complaints": render_admin_complaints},
}

if not st.session_state["token"]:
    render_login()
elif st.session_state["role"] not in PAGES:
    st.error(f"Unsupported role: {st.session_state['role'] or 'unknown'}.")
    if st.button("Log out"):
        logout()
else:
    pages = PAGES[st.session_state["role"]]
    if st.session_state.get("page") not in pages:
        st.session_state["page"] = next(iter(pages))

    with st.sidebar:
        st.markdown("### 🎧 SupportDesk AI")
        st.caption(f"{st.session_state['username'] or st.session_state['customer_id']} · {st.session_state['role']}")
        st.radio("Navigate", list(pages), key="page", label_visibility="collapsed")
        st.divider()
        if st.button("Log out", use_container_width=True):
            logout()

    pages[st.session_state["page"]]()