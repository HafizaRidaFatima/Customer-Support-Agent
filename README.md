# Support Triage Agent

An AI-powered customer support triage system built with **LangGraph**, **FastAPI**, and **Streamlit**. It reads a customer's message, classifies it, looks up orders, checks refund eligibility, pauses for human approval on large refunds, drafts a reply, quality-checks it, and sends it back, all with per-customer conversation memory.

## Features

- **Classification** of each message by category (`refund`, `product`, `order_status`, `other`) and sentiment (`angry`, `negative`, `neutral`, `positive`), using Claude with a keyword-pattern fallback.
- **Order lookup** and **refund eligibility checks** (order exists, belongs to the customer, not already refunded, within the refund window).
- **Human-in-the-loop approval** for refunds above the threshold. The graph pauses via LangGraph `interrupt()` and resumes when an agent decides.
- **Draft, review, rewrite loop**: replies are quality-checked and rewritten up to a maximum number of times before finalizing.
- **Escalation** to a human for angry or unclear messages.
- **Conversation memory** per customer (a follow-up like "where is it?" works without repeating the order number).
- **JWT authentication** with two roles: `customer` and `agent`.
- **Live progress streaming** (server-sent events) so the UI shows each graph step as it finishes.
- **Works without an API key**: if `GROQ_API_KEY` is missing or a call fails, rule-based fallbacks and templates are used.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Agent orchestration | LangGraph, LangChain Core |
| LLM (optional) | Groq API |
| Backend API | FastAPI, Uvicorn, Pydantic |
| Auth | PyJWT, Passlib (bcrypt) |
| Frontend | Streamlit, Requests |

## Project Structure

```
Agent/
├── README.md
├── requirements.txt
├── .env                       # your local secrets (never commit)
├── .gitignore
│
├── backend/
│   └── app/
│       ├── main.py            # FastAPI app, CORS, router
│       ├── config.py          # All settings and constants
│       ├── schemas/           # Pydantic models (auth, chat, ticket, approval, customer)
│       ├── api/
│       │   ├── router.py      # Combines routes under /api
│       │   ├── deps.py        # get_current_user, require_agent
│       │   └── routes/        # health, auth, chat, approvals, customers, tickets
│       ├── services/          # auth_service.py, ticket_service.py, complaint_service.py
│       ├── agent/             # state.py, nodes.py, routers.py, graph.py
│       ├── tools/             # order_tools.py, refund_tools.py, faq_tools.py
│       ├── llm/               # client.py, classifier.py, drafter.py, reviewer.py
│       └── data/              # customers, orders, faq, samples, users (demo data)
│
└── frontend/
    └── app.py                 # Single-file Streamlit app (UI + backend calls)
```

**Layering rule:** lower layers never import upper layers. Import order is `config`, `schemas`, `data` → `tools`, `llm` → `agent` → `services` → `api` → `main`. A circular import error usually means this rule was broken.

## How It Works

### Agent graph
![alt text](<Activity.drawio (3).png>)
### Memory

The graph's `thread_id` is the `customer_id`. That single choice gives each customer their own persistent conversation state, so follow-up messages reuse the previously mentioned order.

### Runtime flow

Customer message → `frontend/app.py` → `chat` route → `deps.py` (token check) → `ticket_service` → graph. After each node finishes, an event is streamed back and the UI shows a progress line.

If a refund exceeds the threshold, the graph pauses at `human_approval`, the frontend receives an "awaiting approval" event, and the agent's screen shows an approval card. When the agent approves or rejects, `approvals` → `ticket_service.resume_stream` continues the graph from where it stopped.

## Business Rules

Configured in `backend/app/config.py`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `REFUND_APPROVAL_THRESHOLD` | 100 | Refunds above this amount need agent approval |
| `REFUND_WINDOW_DAYS` | 30 | Orders older than this are ineligible |
| `MAX_REWRITES` | 2 | Maximum draft rewrites after a failed quality check |
| `CHECKPOINT_DB` | empty | SQLite path for persistent checkpoints; empty uses in-memory |
| `FORCE_QC_FAIL` | false | Forces quality check failures, for testing the rewrite loop |
| `SECRET_KEY`, `ALGORITHM`, `TOKEN_EXPIRE_MINUTES` | n/a | JWT settings |

## Getting Started

### 1. Install

```bash
git clone <your-repo-url>
cd Agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
```

Create a `.env` file in the project root (it is git-ignored):

```
GROQ_API_KEY=Add api key here
MODEL_NAME=Add model name here
DATABASE_URL=Add databse url here
JWT_SECRET_KEY=Add your screat key
ADMIN_CODE=Add you admin code here
ALGORITHUM=Add jwt algorithum here
REFUND_APPROVAL_THRESHOLD=Add amount of threshold
REFUND_WINDOW_DAYS=Add refund days
MAX_RETRIES=Add how many retries occur in the system
```

### 3. Run the backend

```bash
cd backend
uvicorn app.main:app --reload
```

The API is at `http://localhost:8000` and interactive docs at `http://localhost:8000/docs`.

### 4. Run the frontend

In a second terminal:

```bash
streamlit run frontend/app.py
```

## Demo Users

Defined in `backend/app/data/users.py`. Passwords are stored in plain text there **for demo purposes only** and are hashed at startup by `auth_service`.

| Role | Username | Password |
| --- | --- | --- |
| Agent | _fill in from users.py_ | _fill in from users.py_ |
| Customer | _fill in from users.py_ | _fill in from users.py_ |

> Do not use this approach in a real project. Store only hashed passwords in a proper database.

## API Overview

All routes are mounted under `/api`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/health` | public | Server health check |
| POST | `/api/auth/login` | public | Returns a JWT with role and customer_id |
| GET | `/api/auth/me` | logged in | Current user |
| POST | `/api/chat/send` | customer | Send a message; 409 if an approval is pending |
| POST | `/api/chat/stream` | customer | Same, streamed as server-sent events |
| GET | `/api/chat/history` | customer | Conversation memory |
| GET | `/api/approvals/{customer_id}` | agent | Pending approval, if any |
| POST | `/api/approvals/{customer_id}` | agent | Approve or reject; 409 if nothing is pending |
| POST | `/api/approvals/{customer_id}/stream` | agent | Same, streamed |
| GET | `/api/customers` | agent | List customers |
| GET | `/api/tickets/samples` | logged in | Sample tickets |

`customer_id` for chat routes always comes from the token, never from the request body.

Streaming endpoints respond with `text/event-stream`. Event types: `step`, `awaiting_approval`, `done`, `error`.

## Sample Tickets

`backend/app/data/samples.py` contains 10 tickets covering the main paths:

| Scenario | Expected behavior |
| --- | --- |
| Order status (T01) | Order lookup, then reply |
| Memory follow-up (T02) | Finds the order without a number in the message |
| Two ineligible refunds | Polite denial with reason (outside window, already refunded) |
| Small refund | Processed automatically |
| Large refund, approved (T06) | Pauses for approval, then refunds |
| Large refund, rejected (T07) | Pauses for approval, then denial reply |
| Product question | FAQ search |
| Angry customer (T09) | Escalated to a human |
| Unclear message (T10) | Escalated to a human |

## Testing the Flow

1. Open `/docs` and try, in order: health, customer login, Authorize with the token, send a message, send a refund above $100 (expect "awaiting approval"), then log in as the agent and approve.
2. Start the frontend and run through: T01 then T02 (memory), a small refund, T06 (approval card on the agent screen), T07 (rejection), and T09 / T10 (escalation).

## Development Notes

- **One file, one check.** Test each file before starting the next.
- **Add new state fields to `agent/state.py` first.** LangGraph silently ignores fields that are not declared in the state.
- **`human_approval` placement:** `interrupt()` must come first in the node and nothing with side effects before it, because the node re-runs from the start on resume.
- **Streamlit reruns on every click.** Keep anything that must persist in `st.session_state`, and ask the backend whether an approval is pending.
- `llm/client.py` is the only module that talks to Claude.
- Every backend package folder needs an empty `__init__.py`; `frontend/` does not.
- `frontend/app.py` is organized top to bottom as: setup, backend-calling functions, UI pieces, action functions, page flow.

