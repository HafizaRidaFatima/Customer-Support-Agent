# Support Triage Agent

An AI-powered customer support triage system built with **LangGraph**, **FastAPI**, and **Streamlit**. It reads a customer's message, classifies it, looks up orders, checks refund eligibility, pauses for human approval on large refunds, drafts a reply, quality-checks it, and sends it back, all with per-customer conversation memory.

## Features

- **Classification** of each message by category (`refund`, `product`, `order_status`, `other`) and sentiment (`angry`, `negative`, `neutral`, `positive`), using an LLM with a keyword-pattern fallback.
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

![Agent graph](<Activity.drawio (3).png>)

### Memory

The graph's `thread_id` is the `customer_id`. That single choice gives each customer their own persistent conversation state, so follow-up messages reuse the previously mentioned order.

### Runtime flow

Customer message → `frontend/app.py` → `chat` route → `deps.py` (token check) → `ticket_service` → graph. After each node finishes, an event is streamed back and the UI shows a progress line.

If a refund exceeds the threshold, the graph pauses at `human_approval`, the frontend receives an "awaiting approval" event, and the agent's screen shows an approval card. When the agent approves or rejects, `approvals` → `ticket_service.resume_stream` continues the graph from where it stopped.

## Business Rules

Configured in `.env` and loaded by `backend/app/config.py`:

| Setting | Meaning |
| --- | --- |
| `REFUND_APPROVAL_THRESHOLD` | Refunds above this amount need agent approval |
| `REFUND_WINDOW_DAYS` | Orders older than this many days are ineligible for a refund |
| `MAX_RETRIES` | Maximum draft rewrites after a failed quality check |
| `JWT_SECRET_KEY`, `ALGORITHUM` | JWT signing key and algorithm |

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

Create a `.env` file in the project root (it is git-ignored):

```
GROQ_API_KEY=your-groq-api-key
MODEL_NAME=your-model-name
DATABASE_URL=your-database-url
JWT_SECRET_KEY=your-secret-key
ADMIN_CODE=your-admin-code
ALGORITHUM=your-jwt-algorithm
REFUND_APPROVAL_THRESHOLD=100
REFUND_WINDOW_DAYS=30
MAX_RETRIES=2
```

| Variable | Description |
| --- | --- |
| `GROQ_API_KEY` | Groq API key. Optional: fallbacks are used if empty |
| `MODEL_NAME` | Groq model to use |
| `DATABASE_URL` | Database connection URL |
| `JWT_SECRET_KEY` | Secret used to sign login tokens |
| `ADMIN_CODE` | Admin code for agent access |
| `ALGORITHUM` | JWT algorithm, for example `HS256` |
| `REFUND_APPROVAL_THRESHOLD` | Refund amount above which approval is needed |
| `REFUND_WINDOW_DAYS` | Number of days an order stays refundable |
| `MAX_RETRIES` | Number of reply rewrites allowed |

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
| GET | `/api/auth/me` | logged in | Current