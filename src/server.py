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

from fastapi.responses import StreamingResponse
import json

@app.post("/api/query")
async def run_query(request: QueryRequest):
    async def event_generator():
        try:
            initial_state = {"question": request.question, "attempts": 0, "logs": []}
            
            # Use .stream() to get updates from the graph. 
            # stream_mode="updates" yields only the partial state changes from each node.
            # We track logs to send them to the UI.
            for event in graph_app.stream(initial_state, stream_mode="updates"):
                # Event is a dict: {node_name: {updated_state_keys}}
                for node_name, state_update in event.items():
                    if "logs" in state_update:
                        # Get the latest log entry (the last one added)
                        new_logs = state_update["logs"]
                        if new_logs:
                             # The node appends to logs, so we just take the last one or diff it.
                             # But simpler: in our nodes we append. 
                             # However, stream(mode="updates") returns the *output* of the node.
                             # Our nodes return state dict with "logs" key = list of logs including new one.
                             # Wait, our nodes return partial state.
                             # If node returns: {"logs": logs + [new_entry]}, update is that list.
                             # So we just take the last element of the list.
                             
                             latest_log = new_logs[-1]
                             yield json.dumps({"type": "step", "data": latest_log}) + "\n"
                    
                    # If we have a result or final answer, check that too
                    if "results" in state_update:
                        yield json.dumps({"type": "result", "data": state_update["results"]}) + "\n"
                    
                    if "final_answer" in state_update:
                        yield json.dumps({"type": "answer", "data": state_update["final_answer"]}) + "\n"

                    if "visualization" in state_update and state_update["visualization"]:
                        yield json.dumps({"type": "visualization", "data": state_update["visualization"]}) + "\n"
                        
                    if "error" in state_update and state_update["error"]:
                        yield json.dumps({"type": "error", "data": state_update["error"]}) + "\n"

            yield json.dumps({"type": "done"}) + "\n"

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            yield json.dumps({"type": "error", "data": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/api/schema")
async def get_schema():
    from src.graph.nodes import schema_manager
    return schema_manager.get_structured_schema()

# Serve static files (HTML/JS/CSS)
app.mount("/", StaticFiles(directory="src/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
