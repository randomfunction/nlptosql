# Agentic Text-to-SQL Pipeline

A production-grade, highly concurrent Natural Language to SQL generation engine built with **LangGraph**, **FastAPI**, and **Asyncio**. 

Designed for scalability, low latency, and deterministic execution accuracy, this system moves beyond simple Prompt-to-SQL scripts to implement a robust, self-correcting agentic workflow equipped with enterprise-grade observability, semantic caching, and strict SQL sandboxing.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-purple)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green)
![Redis](https://img.shields.io/badge/Redis-Caching-red)

## Engineering Objectives

- **Concurrency & Non-blocking I/O:** Migrated from synchronous execution to an `async/await` foundation using `aiosqlite` and asynchronous LLM providers.
- **Provider Agnosticism:** Abstracted LLM interactions into a `BaseLLMProvider` interface to prevent vendor lock-in (supporting Gemini, OpenAI, etc.).
- **Reliability & Self-Correction:** Implemented a LangGraph state machine that evaluates SQL syntax, sandboxes execution, catches runtime DB errors, and dynamically prompts the LLM to self-correct up to 3 times before failing gracefully.
- **Latency Optimization:** Introduced a deterministic semantic cache layer via **Redis**, yielding a ~90% reduction in P99 latency for repeated analytical queries.
- **Observability:** Centralized structured JSON logging and configured endpoints for OpenTelemetry tracing and Prometheus metrics scraping.

---

## System Architecture

The architecture isolates concerns across the API, Service, Data, and Orchestration layers.

```mermaid
graph TD
    User([Client/User]) -->|HTTP POST| API[FastAPI Layer]
    
    subgraph Core
        API --> Orchestrator[LangGraph Workflow]
        Orchestrator <--> Cache[(Redis Semantic Cache)]
    end
    
    subgraph Services
        Orchestrator --> SchemaSvc[Schema Introspection Service]
        Orchestrator --> ExecSvc[Safe Execution Sandbox]
    end
    
    subgraph Providers
        Orchestrator --> LLM[BaseLLMProvider]
        LLM --> Gemini(Google Gemini)
        LLM --> OpenAI(OpenAI GPT-4o)
    end
    
    ExecSvc --> SQLite[(Read-Only SQLite)]
    SchemaSvc --> SQLite
```

### The Orchestration DAG (LangGraph)
Our query lifecycle maps to a strict Directed Acyclic Graph:
1. **Understanding:** Intent classification & relevance gating.
2. **Schema Retrieval:** Fetches subset schema context mapping to identified entities.
3. **Plan Generation:** Constructs an intermediate multi-step plan.
4. **SQL Generation:** Translates the plan into dialect-specific SQL.
5. **Safe Execution:** Executes in a Read-Only sandboxed connection with enforced row limits.
6. **Recovery Loop:** On SQLite exception, routes back to Step 4 with the exact error trace.

---

## Benchmarks & Evaluation Framework

We utilize a reproducible evaluation pipeline (`scripts/evaluate.py`) against subsets of the **Spider** and **WikiSQL** datasets. 

| Metric | Measurement | Notes |
|--------|-------------|-------|
| **Execution Accuracy** | `89.5%` | Measures exact set match of returned rows vs. ground truth. |
| **P50 Latency (Cold)** | `2.1s` | Full LLM reasoning and code generation pass. |
| **P99 Latency (Cached)**| `35ms` | Hash-based exact match hit on Redis. |
| **Recovery Rate** | `72%` | Percentage of failed queries successfully corrected by the retry loop. |

*Execute the benchmark locally:*
```bash
python scripts/evaluate.py
```

---

## 🛡️ Safety & Security

- **SQL Sandboxing:** The executor strictly mounts the database with a `?mode=ro` flag at the connection level. 
- **Layer 7 Inspection:** Keyword blocklists reject mutation statements (`DROP`, `ALTER`, `DELETE`) before DB connection.
- **Hard Limits:** Queries lacking aggregation automatically receive an enforced `LIMIT 1000`.
- **Timeouts:** Database execution logic is wrapped in an `asyncio.wait_for` constraint, defaulting to 15 seconds to prevent hung queries locking resources.
- **Pydantic Validation:** All incoming payloads and environment variables are strictly typed and validated via Pydantic Settings.

---

## Infrastructure & Deployment

We support containerized deployments utilizing `docker-compose`. The stack launches the FastAPI server, the Redis cache, and a Prometheus monitoring daemon.

### 1. Prerequisites
- Docker Engine
- A Google Gemini or OpenAI API Key

### 2. Local Setup
```bash
git clone <your-repo-url>
cd nlptosql

# Install dependencies (if running locally without Docker)
pip install -r requirements.txt

# Create your .env file
echo "GEMINI_API_KEY=your_key" > .env

# Download the sample database
python setup_db.py
```

### 3. Docker Compose Deployment
```bash
docker-compose up -d --build
```
This deploys:
- **API Server** on `http://localhost:8000`
- **Redis Cache** on `localhost:6379`
- **Prometheus Scraper** on `localhost:9090`

---

## Observability & Logging

- **Metrics Endpoint:** Visit `/metrics` to view Prometheus scrape targets including query success rates, latency distributions, and total token usage.
- **Structured Logs:** All modules output structured JSON compatible with ELK or Datadog ingestion:
```json
{
  "timestamp": "2026-05-11 10:45:00",
  "level": "INFO",
  "logger": "nlptosql",
  "message": "Query answered successfully.",
  "module": "server",
  "line": 49
}
```

