from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import process_question

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/api/query")
async def run_query(request: QueryRequest):
    # Pass input to main logic (which we refactored to return dict)
    response = process_question(request.question, return_steps=True)
    return response

# Serve static files (HTML/JS/CSS)
app.mount("/", StaticFiles(directory="src/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
