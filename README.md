# DodgeAI — Business Data Intelligence Platform

> A hybrid Graph + SQL system with an LLM-powered conversational interface for querying, tracing, and visualising business data.

---

## 📋 Problem Statement

Business data is inherently **relational and interconnected** — orders link to customers, deliveries, invoices, and payments. Traditional SQL databases store this data efficiently but make it hard to:

- **Trace end-to-end flows** (e.g., "What happened to Order #42?" requires joining 5+ tables)
- **Ask questions in natural language** without knowing SQL
- **Visualise entity relationships** and spot patterns

DodgeAI solves this by combining a **relational database** for structured queries with a **graph layer** for flow tracing, all accessible through a **natural language chat interface** backed by LLM guardrails.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)             │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │   Graph Panel        │  │   Chat Panel             │  │
│  │   (react-force-graph)│  │   • Input box            │  │
│  │   • Color-coded nodes│  │   • Message bubbles      │  │
│  │   • Glow highlighting│  │   • SQL display          │  │
│  │   • Legend            │  │   • Trace chain viz      │  │
│  └──────────────────────┘  └──────────────────────────┘  │
└────────────────────────────────┬─────────────────────────┘
                                 │  POST /api/v1/chat
                                 ▼
┌──────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                        │
│                                                          │
│  ┌─────────────┐                                         │
│  │ Guardrails  │◄── Layer 1: Pre-LLM regex filter        │
│  │ (guardrails │    Blocks jokes, coding, general         │
│  │  .py)       │    knowledge BEFORE any API call         │
│  └──────┬──────┘                                         │
│         ▼                                                │
│  ┌─────────────┐                                         │
│  │   Intent    │  Regex-based classification:             │
│  │  Detector   │  • TRACE → graph traversal               │
│  │             │  • QUERY → NL-to-SQL pipeline            │
│  └──────┬──────┘                                         │
│         │                                                │
│    ┌────┴─────┐                                          │
│    ▼          ▼                                          │
│  TRACE      QUERY                                        │
│    │          │                                          │
│    ▼          ▼                                          │
│  ┌──────┐  ┌─────────┐  ┌───────────┐  ┌────────────┐   │
│  │Graph │  │NL→SQL   │─▶│  Query    │─▶│  Answer    │   │
│  │BFS   │  │(LLM)    │  │ Executor  │  │ Generator  │   │
│  │Trace │  │         │  │ (safe SQL) │  │  (LLM)     │   │
│  └──┬───┘  └────┬────┘  └─────┬─────┘  └─────┬──────┘   │
│     │           │             │               │          │
│     │      Layer 2: LLM     Layer 3: Post-    │          │
│     │      prompt guards    execution SQL     │          │
│     │                       validation        │          │
│     ▼           ▼             ▼               ▼          │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SQLite Database (app.db)             │    │
│  │  customers · products · orders · order_items      │    │
│  │  addresses · deliveries · invoices · payments     │    │
│  └──────────────────────────────────────────────────┘    │
│                         │                                │
│  ┌──────────────────────┴───────────────────────────┐    │
│  │          NetworkX Directed Graph                  │    │
│  │  Order ──PLACED_BY──▶ Customer                    │    │
│  │  Order ──CONTAINS───▶ Product                     │    │
│  │  Order ──FULFILLED_BY▶ Delivery                   │    │
│  │  Delivery ─BILLED_BY─▶ Invoice                    │    │
│  │  Invoice ──PAID_BY───▶ Payment                    │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 🤔 Why a Graph + SQL Hybrid?

| Dimension | SQL Alone | Graph Alone | **Hybrid (DodgeAI)** |
|---|---|---|---|
| Aggregation queries | ✅ Native `SUM`, `COUNT`, `GROUP BY` | ❌ Awkward | ✅ SQL handles these |
| Flow tracing | ❌ Requires 4-5 JOINs | ✅ Single BFS traversal | ✅ Graph handles these |
| Schema enforcement | ✅ Strong typing + FK constraints | ❌ Schema-free | ✅ SQL stores, graph reads |
| Relationship exploration | ❌ Must know FK paths | ✅ Traverse any direction | ✅ Natural graph traversal |
| Storage footprint | ✅ Minimal (single DB) | ❌ Separate store | ✅ Graph built on-the-fly from DB |

**Key insight:** SQL excels at *"how much?"* questions, graphs excel at *"what's connected?"* questions. The intent detector routes each query to the right engine automatically.

---

## 🤖 LLM Prompting Strategy

The system uses an LLM (Groq or Gemini) for two tasks:

### 1. Natural Language → SQL (`nl_to_sql.py`)
- **Schema injection** — the full DDL is embedded in the system prompt so the LLM knows exactly what columns and tables exist
- **Zero-temperature** — deterministic output for repeatable SQL generation
- **Few-shot examples** — 5 positive examples + 5 rejection examples baked into the prompt
- **Explicit table whitelist** — `"You may ONLY reference these tables: addresses, customers, deliveries, invoices, order_items, orders, payments, products"`
- **`THIS_IS_IRRELEVANT` sentinel** — LLM outputs this exact string for off-topic queries, which the backend detects and converts to a user-friendly rejection

### 2. SQL Result → Natural Language (`answer_generator.py`)
- **Data-only grounding** — prompt forbids the LLM from adding information not present in the query results
- **No SQL leakage** — the answer must never mention tables, columns, or SQL syntax to the end user
- **Format-aware** — handles empty results, single-row counts, and multi-row tabular data with appropriate formatting

---

## 🛡️ Guardrails Design

Three layers of defence, each catching what the previous layer might miss:

```
User query
    │
    ▼
┌─────────────────────────────────────────┐
│  Layer 1: Pre-LLM Regex Filter          │  ← No API call needed
│  (guardrails.py)                        │
│                                         │
│  Blocks: jokes, coding, general         │
│  knowledge, math, weather, personal     │
│  questions                              │
│                                         │
│  Allows: any query mentioning domain    │
│  keywords (order, customer, invoice...) │
└──────────────┬──────────────────────────┘
               │ (passed)
               ▼
┌─────────────────────────────────────────┐
│  Layer 2: LLM Prompt Constraints        │  ← LLM returns THIS_IS_IRRELEVANT
│  (nl_to_sql.py)                         │
│                                         │
│  • Schema-only column references        │
│  • Explicit rejection categories in     │
│    system prompt with examples           │
│  • SELECT-only enforcement              │
└──────────────┬──────────────────────────┘
               │ (generated SQL)
               ▼
┌─────────────────────────────────────────┐
│  Layer 3: Post-LLM SQL Validation       │  ← Code-level enforcement
│  (query_executor.py)                    │
│                                         │
│  • Regex blocks DELETE/DROP/UPDATE/etc. │
│  • Table whitelist check                │
│  • Must start with SELECT               │
└─────────────────────────────────────────┘
```

**Why three layers?**
- **Layer 1** saves cost — rejects obvious garbage without burning an API call
- **Layer 2** leverages LLM understanding for borderline cases
- **Layer 3** is the hard safety net — even if the LLM hallucinates, dangerous SQL never executes

---

## ⚖️ Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| **SQLite** instead of Postgres | Zero setup, single-file DB, perfect for demos | No concurrent writes, limited scale |
| **On-the-fly graph construction** | Always in sync with DB, no separate store | Rebuilds graph per trace request (acceptable for demo-scale data) |
| **Regex intent detection** instead of LLM classification | Fast, deterministic, no API call | Limited to predefined patterns (adding new intents requires code) |
| **Pre-LLM keyword guardrails** | Saves API cost on obvious off-topic queries | Regex can't catch all edge cases (Layer 2 + 3 compensate) |
| **LLM for NL→SQL** instead of a DSL | Handles arbitrary natural language phrasing | Depends on external API, latency per query |
| **2D force graph** instead of 3D | Simpler, better performance, clearer labels | Less immersive for very large graphs |

---

## 🚀 How to Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- An LLM API key — **one** of:
  - `GROQ_API_KEY` (recommended — fast + free tier)
  - `GEMINI_API_KEY`

### 1. Backend Setup

```bash
# Clone and navigate
cd DodgeAI

# Install Python dependencies
pip install -r requirements.txt

# Set your API key
export GROQ_API_KEY="your-key-here"
# or: export GEMINI_API_KEY="your-key-here"

# Parse the SAP dataset and load it into SQLite
python convert_sap.py
python load_data.py

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api to backend)
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 💬 Example Queries

### Data Queries (SQL path)
| Query | What it does |
|---|---|
| `Show all customers` | Lists all customer records |
| `Top 3 products by price` | Ranks products by unit price |
| `Total revenue by customer` | Aggregates order totals per customer |
| `How many orders are pending?` | Counts orders with status = pending |
| `Unpaid invoices` | Filters invoices by payment status |

### Flow Tracing (Graph path)
| Query | What it does |
|---|---|
| `trace order 740506` | Full downstream flow: Order → Customer, Products, Deliveries → Invoices → Payments |
| `show full flow of order 740556` | Same as above, for Order 740556 |
| `track delivery 80738076` | Trace from a specific delivery node |
| `what happened to invoice 90504248` | Trace connections of Invoice 90504248 |
| `flow of payment 9400000220_1` | Shows what an individual payment connects to |

### Blocked Queries (Guardrails)
| Query | Response |
|---|---|
| `Tell me a joke` | *"This system is designed to answer questions related to the provided dataset only."* |
| `Write a Python function` | *"This system is designed to answer questions related to the provided dataset only."* |
| `What is the capital of France?` | *"This system is designed to answer questions related to the provided dataset only."* |

---

## 📁 Project Structure

```
DodgeAI/
├── main.py                 # FastAPI app entry point
├── database.py             # SQLAlchemy engine + session
├── models.py               # ORM models (8 tables)
├── schema.sql              # DDL reference
├── load_data.py            # CSV/JSON → SQLite loader
├── guardrails.py           # Pre-LLM query relevance filter
├── intent_detector.py      # Trace vs query classification
├── nl_to_sql.py            # LLM-based NL → SQL generation
├── query_executor.py       # Safe SQL execution + validation
├── answer_generator.py     # LLM-based result → NL answer
├── graph.py                # NetworkX graph construction + BFS trace
├── routes/
│   ├── chat.py             # /chat endpoint (orchestrator)
│   ├── graph.py            # /graph/* endpoints
│   ├── customers.py        # CRUD routes
│   ├── orders.py           #   ...
│   └── ...                 #   (7 entity routes)
├── data/                   # Sample CSV/JSON datasets
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Two-pane layout
│   │   ├── GraphPanel.jsx  # Force-directed graph viz
│   │   ├── ChatPanel.jsx   # Chat UI + trace chain
│   │   ├── api.js          # Backend API client
│   │   └── index.css       # Dark theme design system
│   ├── vite.config.js      # Dev server + API proxy
│   └── package.json
└── requirements.txt
```

---

## 📄 License

This project is for educational and demonstration purposes.
