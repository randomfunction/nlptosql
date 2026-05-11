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
import time
from src.core.config import settings
from src.core.logger import logger
from src.services.cache import cache_service
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import Request, HTTPException, Depends

# Expose Prometheus Metrics
Instrumentator().instrument(app).expose(app)

async def verify_api_key(request: Request):
    if settings.API_KEY:
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != f"Bearer {settings.API_KEY}":
            raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/api/query", dependencies=[Depends(verify_api_key)])
async def run_query(request: QueryRequest):
    start_time = time.time()
    logger.info(f"Received query: {request.question}")
    
    async def event_generator():
        success = False
        try:
            initial_state = {"question": request.question, "attempts": 0, "logs": []}
            
            # Use .astream() to avoid blocking the API thread
            async for event in graph_app.astream(initial_state, stream_mode="updates"):
                for node_name, state_update in event.items():
                    if "logs" in state_update and state_update["logs"]:
                        latest_log = state_update["logs"][-1]
                        yield json.dumps({"type": "step", "data": latest_log}) + "\n"
                    
                    if "results" in state_update:
                        yield json.dumps({"type": "result", "data": state_update["results"]}) + "\n"
                    
                    if "final_answer" in state_update:
                        success = True
                        logger.info(f"Query answered successfully: '{request.question}'")
                        yield json.dumps({"type": "answer", "data": state_update["final_answer"]}) + "\n"

                    if "visualization" in state_update and state_update["visualization"]:
                        yield json.dumps({"type": "visualization", "data": state_update["visualization"]}) + "\n"
                        
                    if "error" in state_update and state_update["error"]:
                        logger.error(f"Error in {node_name}: {state_update['error']}")
                        yield json.dumps({"type": "error", "data": state_update["error"]}) + "\n"

            yield json.dumps({"type": "done"}) + "\n"

        except Exception as e:
            import traceback
            error_msg = str(e)
            logger.error(f"Unhandled Server Error: {error_msg}\n{traceback.format_exc()}")
            yield json.dumps({"type": "error", "data": "An unexpected error occurred while processing your request."}) + "\n"
        finally:
            duration = time.time() - start_time
            logger.info(f"Query completed in {duration:.2f}s with success={success}")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.get("/api/metrics/legacy")
async def get_metrics():
    return {"status": "deprecated, use /metrics for prometheus"}

@app.get("/api/schema")
async def get_schema():
    from src.services.schema import schema_service
    return await schema_service.get_structured_schema()

# Serve static files (HTML/JS/CSS)
app.mount("/", StaticFiles(directory="src/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
