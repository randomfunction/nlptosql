# 🧠 Agentic Text-to-SQL

An intelligent natural language to SQL system that **thinks, explores, validates, and recovers from mistakes** — going beyond naive prompt-to-SQL approaches.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-purple)
![Gemini](https://img.shields.io/badge/Google%20Gemini-API-orange)
![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-green)

## 🎯 What This Does

Takes natural language questions → Reasons about the database → Generates safe SQL → Returns human-readable answers with full transparency.

```
User: "Which artist has the most albums?"

System Reasoning:
├── Understanding: aggregation query, moderate complexity
├── Schema Retrieved (Vector Search): Artist, Album
├── Plan: JOIN Artist with Album, GROUP BY, ORDER BY COUNT DESC
├── Generated SQL: SELECT a.Name, COUNT(al.AlbumId)...
└── Execution: Success, 1 row

Answer: "Iron Maiden has the most albums with 21 albums."
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| **LangGraph Agentic Workflow** | State machine-based agent with conditional routing |
| **RAG-based Schema Selection** | ChromaDB + Google Embeddings for vector similarity search |
| **LLM-based Meta Queries** | Dynamically generates SQL for schema introspection questions |
| **Irrelevant Query Detection** | Politely rejects off-topic questions (greetings, general knowledge) |
| **Self-Correction** | Automatically retries with fixes when queries fail (up to 3 attempts) |
| **Reasoning Trace** | Shows every step of the decision-making process |
| **Ambiguity Handling** | Asks clarifying questions for vague queries |
| **Data Exploration** | Validates entities exist before querying |
| **Safe Execution** | Read-only queries only, with LIMIT protection |
| **Auto Visualization** | Generates Chart.js charts for suitable results |
| **Streaming UI** | Real-time step-by-step updates in the web interface |

## 🏗️ Architecture

The system uses **LangGraph** to orchestrate an agentic workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Question                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Understanding Node                        │
│      (Intent, Complexity, Entities, Relevance Check)        │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    [Irrelevant]        [Meta Query]        [Normal Query]
          │                   │                   │
          ▼                   ▼                   ▼
    Reject Politely     Handle Meta      Get Schema (RAG/LLM)
                              │                   │
                              ▼                   ▼
                         Generate SQL       Explore Data
                              │                   │
                              ▼                   ▼
                          Execute          Generate Plan
                                                  │
                                                  ▼
                                            Generate SQL
                                                  │
                                                  ▼
                                        Execute & Validate ◄──┐
                                                  │           │
                                        ┌─────────┴─────────┐ │
                                        ▼                   ▼ │
                                   [Success]            [Error]──┘
                                        │              (Retry 3x)
                                        ▼
                                Generate Visualization
                                        │
                                        ▼
                                Generate Answer
```

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Google Gemini API key ([Get one free](https://aistudio.google.com/app/apikey))

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd nlptosql

# Install dependencies
pip install -r requirements.txt

# Set up environment (use GEMINI_API_KEY or GOOGLE_API_KEY)
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

### 3. Run

**Web Interface (Recommended):**
```bash
python src/server.py
# Open http://localhost:8000
```

**CLI Mode:**
```bash
python main.py "Which artist has the most albums?"
```

## 📁 Project Structure

```
nlptosql/
├── main.py                 # CLI entry point
├── baseline.py             # Naive approach for comparison
├── requirements.txt        # Dependencies
├── Chinook_Sqlite.sqlite   # Sample music database
├── src/
│   ├── server.py           # FastAPI web server (streaming)
│   ├── schema.py           # Schema management
│   ├── vector_store.py     # ChromaDB RAG for schema selection
│   ├── examples_data.py    # Few-shot examples for RAG
│   ├── validator.py        # SQL validation
│   ├── meta_handler.py     # LLM-based meta-query handling
│   ├── static/
│   │   └── index.html      # Web UI with Chart.js
│   └── graph/              # LangGraph Agentic Workflow
│       ├── workflow.py     # State machine definition
│       ├── nodes.py        # Node implementations
│       └── state.py        # State type definitions
└── test_suite.py           # Test cases
```

## 🔧 Configuration

### Using a Different Database

1. Replace `Chinook_Sqlite.sqlite` with your database
2. Update `DB_FILE` in `src/graph/nodes.py`:
   ```python
   DB_FILE = "your_database.sqlite"
   ```
3. Delete the `chroma_db/` folder (to re-index schema)
4. Restart the server — the system auto-detects table structure

### Changing the LLM Model

Edit `src/graph/nodes.py` in the `get_llm()` function:
```python
_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
```

## 📊 Sample Queries

| Type | Example |
|------|---------|
| Simple | "How many tracks are there?" |
| Filtering | "Find all tracks longer than 5 minutes" |
| Joins | "List all tracks in the 'Rock' genre" |
| Aggregation | "Total revenue by country, sorted highest first" |
| Complex | "Customers who purchased both Rock and Jazz" |
| Meta | "Which tables have more than 5 columns?" |
| Ambiguous | "Show me the best artists" → asks for clarification |
| Irrelevant | "How are you doing?" → politely declined |

## 🧪 Testing

```bash
python test_suite.py
```

## 🛡️ Safety Features

- ✅ **Read-only**: Only SELECT queries allowed
- ✅ **LIMIT protection**: Auto-adds LIMIT 1000 to prevent runaway queries
- ✅ **Validation**: Checks for dangerous patterns before execution
- ✅ **Error recovery**: Graceful handling with up to 3 retry attempts
- ✅ **Irrelevant query rejection**: Won't hallucinate on off-topic questions

## 📦 Dependencies

- `langgraph` — Agentic workflow orchestration
- `langchain-google-genai` — Gemini LLM integration
- `chromadb` — Vector store for RAG
- `fastapi` / `uvicorn` — Web server with streaming
- `sqlparse` — SQL validation
- `python-dotenv` — Environment management

## 📄 License

MIT License
