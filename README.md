# 🎸 Empório da Música — AI Customer Support Agent

Hybrid **ReAct + RAG** conversational AI agent engineered in Python for **Empório da Música** (Campo Grande/MS), automating WhatsApp customer support across product catalog inquiries, real-time stock checks, non-cumulative promotional pricing, credit card installment rules, order tracking, and store policy enforcement.

---

## 🏗️ Architecture & Technical Decisions

| Decision Dimension | Selected Approach | Engineering Justification |
| :--- | :--- | :--- |
| **Agent Orchestration** | **LangGraph** (`StateGraph` + `ToolNode`) | Provides deterministic state transitions, explicit tool-execution loops, and native multi-turn checkpointing without opaque prompt-only chains. |
| **Reasoning Pattern** | **Hybrid ReAct (SQL Function Calling + Vector RAG)** | Structured transactional data (`products`, `orders`, `promotions`) requires zero-hallucination SQL queries and exact arithmetic, whereas the 10-section store policy manual (`políticas_da_loja.pdf`) benefits from hierarchical semantic retrieval. |
| **LLM Provider & Model** | **Google Gemini (`gemini-2.5-flash`)** / **OpenAI (`gpt-4o-mini`)** | Configurable via `.env`. Both models offer low latency (<2s response time ideal for WhatsApp chat) and high reliability in Pydantic-typed function calling. |
| **Relational Storage & ETL** | **SQLite + SQLAlchemy 2.0 ORM** | Self-contained, zero-config relational database seeded idempotently from `data/*.csv`, normalizing JSON `specs` and handling catalog edge cases. |
| **Policy RAG Engine** | **PyMuPDF + ChromaDB + Hybrid Lexical Boosting** | Parses `políticas_da_loja.pdf` by chapter/subsection headers (`1.0` through `10.0`) and combines cosine vector similarity with domain keyword boosting in an offline-safe persistent collection. |
| **Conversation Memory** | **LangGraph `SqliteSaver`** | Persists multi-turn dialog state per `thread_id` in `storage/checkpoints.db`, allowing customers to ask follow-up questions naturally (e.g., *"E como fica o parcelamento dele?"*). |
| **User Interfaces** | **Streamlit Web UI + Interactive CLI** | Includes a WhatsApp-themed Streamlit app (`src/app.py`) with expandable tool-call inspection and quick-test buttons, plus a terminal CLI (`src/cli.py`). |

---

## 📂 Project Structure

```text
emporio-musica-agent/
├── data/                               # Provided CSV datasets and store policy PDF
├── examples/                           # 4 end-to-end multi-turn conversation transcripts
│   ├── 01_catalog_and_non_cumulative_promo.md
│   ├── 02_expired_promo_and_out_of_stock.md
│   ├── 03_order_tracking_and_return_policy.md
│   └── 04_store_info_and_out_of_scope_guardrails.md
├── src/
│   ├── config.py                       # Centralized environment and path settings
│   ├── app.py                          # WhatsApp-inspired Streamlit web interface
│   ├── cli.py                          # Interactive command-line interface
│   ├── database/
│   │   ├── models.py                   # SQLAlchemy 2.0 ORM entities (6 tables)
│   │   └── ingest_csv.py               # Idempotent CSV sanitization & seeding pipeline
│   ├── rag/
│   │   ├── ingest_pdf.py               # Hierarchical PDF section parser & ChromaDB indexer
│   │   └── retriever.py                # Hybrid vector + domain-boosted policy retriever
│   └── agent/
│       ├── tools.py                    # 4 Pydantic-validated deterministic tools
│       ├── prompts.py                  # Store persona & strict business-rule guardrails
│       └── graph.py                    # Stateful LangGraph workflow with SqliteSaver
├── tests/
│   ├── conftest.py                     # Automated test database & vector store fixtures
│   ├── test_tools.py                   # Unit tests for pricing, PIX, installments & stock
│   └── test_scenarios.py               # Integration tests for order windows & RAG policies
├── .env.example                        # Environment variable template
└── pyproject.toml                      # Package manifest & dependencies
```

---

## 🚀 Setup & Execution Instructions

### 1. Prerequisites
* **Python 3.11+**
* A Google Gemini API key (`GOOGLE_API_KEY`) or OpenAI API key (`OPENAI_API_KEY`).

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/arthurceicorrea/emporio-musica-agent.git
cd emporio-musica-agent

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project and development dependencies
pip install -e ".[dev]"
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and configure your chosen LLM provider:

```bash
cp .env.example .env
```

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your_google_api_key_here
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.2
```
*(Alternatively, set `LLM_PROVIDER=openai`, `OPENAI_API_KEY=sk-...`, and `MODEL_NAME=gpt-4o-mini`.)*

### 4. Initialize Databases (Optional — Auto-runs on App Startup)

```bash
python -m src.database.ingest_csv
python -m src.rag.ingest_pdf
```

### 5. Run the Agent

**Option A — Streamlit WhatsApp Web Interface (Recommended):**
```bash
streamlit run src/app.py
```

**Option B — Interactive Terminal CLI:**
```bash
python -m src.cli --show-tools
```

### 6. Run the Automated Test Suite

```bash
pytest -v
```

---

## 🔍 Data Anomalies & Policy Ambiguities Documented

During exploratory analysis of `data/*.csv` and `data/políticas_da_loja.pdf`, several intentional edge cases and discrepancies were identified and handled deterministically in code:

1. **Non-Cumulative PIX & Promotional Pricing (Sections 3 & 6.2):**
   * Only **4 of the 25 rows** in `promotions.csv` are currently active (`is_active = 1`: Promotion IDs 12, 14, 19, and 24).
   * Section 6.2 states that promotions are **not cumulative** and the **5% PIX discount does not apply** to already promotional prices. `search_products_catalog` and `calculate_payment_and_shipping` enforce this rule automatically (e.g., *Taylor 110e* has an active 8% promo from R$ 5,999.00 to R$ 5,519.08, so its PIX price remains R$ 5,519.08; conversely, *Takamine GD20* has an expired 12% promo, so it is sold at table price R$ 2,199.00 and receives the 5% PIX discount to R$ 2,089.05).
2. **Credit Card Minimum Installment Conflict (Section 3 vs. Section 3.1):**
   * The summary table in Section 3 mentions *"Até 12x sem juros | Parcela mínima de R$ 100,00"*, whereas Section 3.1 specifies tiered minimums: **1x–3x (min R$ 50.00)**, **4x–6x (min R$ 80.00)**, and **7x–12x (min R$ 100.00)**.
   * **Assumption:** The specific rules in Section 3.1 take precedence over the general summary table.
3. **Orphan Categories in Catalog (`categories.csv` vs. `products.csv`):**
   * Categories **6 (`Instrumentos de Sopro - Madeiras`)**, **7 (`Instrumentos de Sopro - Metais`)**, and **8 (`Cordas Orquestrais`)** exist in `categories.csv` but have zero products in `products.csv`. The catalog tool explicitly flags `empty_registered_categories_matched` so the agent transparently informs the customer that no units are currently in stock for immediate delivery.
4. **Stock & Lifecycle Traps (`out_of_stock`, `discontinued`, `coming_soon`):**
   * Product `96` (*Giannini GF-3D*) is `active` with `stock_quantity = 0`.
   * Product `113` (*Shelby SN-7C*) has `stock_quantity = 0` and `status = discontinued`, while Product `136` (*Ibanez Bass 2X*) has `stock_quantity = 13` despite `status = discontinued`.
   * Product `130` (*Kala KA-ABP-CTG Barítono Cedar*) has `status = coming_soon` (`created_at = 2025-05-15`), yet appears in historical orders `#3` and `#14`.
   * In all unavailable cases, `Product.is_available` requires `status == 'active' and stock_quantity > 0`, and `search_products_catalog` automatically attaches 3 in-stock alternatives from the same category (Section 7.3).
5. **Catalog Text vs. JSON `specs` Mismatches (Products 135–144):**
   * Several synthetic rows have mismatched titles, descriptions, and JSON `specs` (e.g., Product `142` is named *Korg Synth 1 Pro*, described as an 88-key *Roland*, with `{"keys": "61"}` in `specs`). Both the description and parsed `specs` dictionary are exposed to the agent so it can clarify details transparently if asked.
6. **WhatsApp Contact & Tracking Code Format Discrepancies:**
   * Cover/Section 1.2 lists phone/WhatsApp `(67) 3341-4444` and email `contato@emporiodamusica.com.br` (spelled with a circumflex `empório` in Table 1.2), whereas Section 7.0 cites `(67) 3321-4500`.
   * Section 5.3 describes tracking codes as `BR` + 9 alphanumeric characters + `BR`, while `orders.csv` uses 11 middle characters (e.g., `BRAB1234567BR`). `lookup_customer_order` performs case-insensitive substring matching to support any format.

---

## ⚠️ Known Limitations & Future Improvements

* **Read-Only Transactional Scope:** The agent currently reads orders and catalog state but does not mutate inventory or create live checkout links/orders in the database. With more time, transactional write tools (`create_order`, `open_support_ticket`) with human-in-the-loop confirmation would be added.
* **Customer Authentication:** Order lookup by name or email (`lookup_customer_order`) does not currently verify an OTP token. Notice that `customers.csv` contains duplicate names/emails across different IDs (e.g., `bruno.martins@jmail.com` on IDs `11` and `43`); the tool returns all matching orders so the agent can disambiguate by order ID or date.
* **Shipping Freight API:** For cities outside Metropolitan Campo Grande (Dourados, Três Lagoas, Corumbá, Ponta Porã), the agent provides the official carrier delivery windows (PAC, SEDEX, Jadlog) from Section 5.2, as live Correios/Jadlog CEP weight/dimension tariff APIs are not connected.

---

## 🤖 AI Coding Assistant Workflow

This project was developed using **Google Gemini** as an interactive architectural and pair-programming collaborator:
1. **Exploratory Data & Policy Auditing:** Used AI to cross-reference all 6 CSV tables against the 8-page `políticas_da_loja.pdf`, surfacing hidden business rules (non-cumulative PIX discounts, expired promotions, discontinued items with positive stock, and orphan categories).
2. **Modular Iterative Engineering:** Rather than generating a monolithic script, the system was designed and validated across 8 incremental stages (scaffolding, SQLAlchemy ETL, hierarchical PDF RAG, deterministic Pydantic tools, LangGraph state machine, Streamlit/CLI interfaces, Pytest suite, and documentation).
3. **Verification & Guardrail Hardening:** All pricing formulas, installment thresholds, and date-window calculations were isolated into deterministic Python functions tested via `pytest`, ensuring the LLM never performs unverified mental math.
