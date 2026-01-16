from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv() # Load .env variables

# Import the LangGraph workflow
from src.graph.workflow import app as graph_app

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/api/query")
async def run_query(request: QueryRequest):
    try:
        # Invoke LangGraph
        initial_state = {"question": request.question, "attempts": 0, "logs": []}
        final_state = graph_app.invoke(initial_state)
        
        # Extract Output
        return {
            "success": True, 
            "result": final_state.get("results"), 
            "natural_answer": final_state.get("final_answer"),
            "steps": final_state.get("logs", [])
        }
    except Exception as e:
        import traceback
        return {
            "success": False, 
            "error": str(e),
            "trace": traceback.format_exc()
        }

@app.get("/api/schema")
async def get_schema():
    from src.graph.nodes import schema_manager
    return schema_manager.get_structured_schema()

# Serve static files (HTML/JS/CSS)
app.mount("/", StaticFiles(directory="src/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
