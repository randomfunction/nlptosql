# 🧠 Agentic Text-to-SQL

An intelligent natural language to SQL system that **thinks, explores, validates, and recovers from mistakes** — going beyond naive prompt-to-SQL approaches.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LangChain](https://img.shields.io/badge/LangChain-Enabled-green)
![Gemini](https://img.shields.io/badge/Google%20Gemini-API-orange)

## 🎯 What This Does

Takes natural language questions → Reasons about the database → Generates safe SQL → Returns human-readable answers with full transparency.

```
User: "Which artist has the most albums?"

System Reasoning:
├── Understanding: aggregation query, moderate complexity
├── Relevant Tables: Artist, Album
├── Plan: JOIN Artist with Album, GROUP BY, ORDER BY COUNT DESC
├── Generated SQL: SELECT a.Name, COUNT(al.AlbumId)...
└── Execution: Success, 1 row

Answer: "Iron Maiden has the most albums with 21 albums."
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| **RAG-based Schema Selection** | Uses vector embeddings to retrieve only relevant tables, scales to large databases |
| **Few-Shot Learning** | Retrieves similar past examples to improve query accuracy |
| **Self-Correction** | Automatically retries with fixes when queries fail |
| **Reasoning Trace** | Shows every step of the decision-making process |
| **Ambiguity Handling** | Asks clarifying questions for vague queries |
| **Meta Queries** | Answers questions about the database itself |
| **Safe Execution** | Read-only queries only, with LIMIT protection |
| **Visualization** | Auto-generates charts for suitable results |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Question                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Understanding Node                        │
│         (Intent, Complexity, Entities, Ambiguity)           │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        [Meta Query]    [Ambiguous]     [Normal Query]
              │               │               │
              ▼               ▼               ▼
        Handle Meta      Clarify        Schema Lookup
                                              │
                                              ▼
                                        Generate Plan
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
                                    │              (Retry up to 3x)
                                    ▼
                            Generate Answer
                                    │
                                    ▼
                            Visualization (optional)
```

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Google Gemini API key ([Get one free](https://makersuite.google.com/app/apikey))

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd nlptosql

# Install dependencies
pip install -r requirements.txt

# Set up environment
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### 3. Run

**CLI Mode:**
```bash
python main.py "Which artist has the most albums?"
```

**Web Interface:**
```bash
python src/server.py
# Open http://localhost:8000
```

## 📁 Project Structure

```
nlptosql/
├── main.py                 # CLI entry point
├── baseline.py             # Naive approach for comparison
├── requirements.txt        # Dependencies
├── Chinook_Sqlite.sqlite   # Sample database
├── src/
│   ├── server.py           # FastAPI web server
│   ├── schema.py           # Schema management & RAG
│   ├── vector_store.py     # ChromaDB embeddings
│   ├── generator.py        # SQL generation
│   ├── validator.py        # SQL validation
│   ├── meta_handler.py     # Meta-query handling
│   ├── examples_data.py    # Few-shot examples
│   ├── static/
│   │   └── index.html      # Web UI
│   └── graph/
│       ├── workflow.py     # LangGraph state machine
│       ├── nodes.py        # Graph node implementations
│       └── state.py        # State definitions
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
4. Restart the server

### Changing the LLM Model

Edit `src/graph/nodes.py`:
```python
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
```

## 📊 Sample Queries

| Complexity | Example |
|------------|---------|
| Simple | "How many tracks are there?" |
| Filtering | "Find all tracks longer than 5 minutes" |
| Joins | "List all tracks in the 'Rock' genre" |
| Aggregation | "Total revenue by country, sorted highest first" |
| Complex | "Customers who purchased both Rock and Jazz" |
| Meta | "What tables are in the database?" |
| Ambiguous | "Show me the best artists" → asks for clarification |

## 🧪 Testing

```bash
python test_suite.py
```

## 🛡️ Safety Features

- ✅ **Read-only**: Only SELECT queries allowed
- ✅ **LIMIT protection**: Auto-adds LIMIT 1000 to prevent runaway queries
- ✅ **Validation**: Checks for dangerous patterns before execution
- ✅ **Error recovery**: Graceful handling of failures

## 📦 Dependencies

- `langchain` / `langchain-google-genai` — LLM orchestration
- `chromadb` — Vector store for RAG
- `fastapi` / `uvicorn` — Web server
- `sqlparse` — SQL validation
- `google-generativeai` — Gemini API

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## 📄 License

MIT License
