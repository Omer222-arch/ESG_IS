import json
import asyncio
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import your graph wrappers from your engine file
from engine import run_analysis_events, resume_analysis

app = FastAPI(
    title="Financial & ESG Compliance Analytics Engine",
    version="1.0.0"
)

# Enable CORS so your React frontend can seamlessly connect without blocking issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your specific React port (e.g., ["http://localhost:5173"]) in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST SCHEMAS ---
class AnalysisRequest(BaseModel):
    user_query: str
    thread_id: str = "default_session"
    live_web_context: str = ""

class ReviewRequest(BaseModel):
    thread_id: str
    human_approved: bool


# --- ROUTES ---

@app.post("/api/analyze")
async def analyze_query(request: AnalysisRequest):
    """
    Spawns the LangGraph pipeline and streams event updates to the frontend 
    using Server-Sent Events (SSE).
    """
    async def event_generator():
        try:
            # Consume the generator function from engine.py
            async for event in run_analysis_events(
                user_query=request.user_query,
                thread_id=request.thread_id,
                live_web_context=request.live_web_context
            ):
                # Format each update precisely as an SSE data block
                yield f"data: {json.dumps(event)}\n\n"
                # Small sleep to guarantee smooth flushing over the network socket
                await asyncio.sleep(0.05)
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'details': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/review")
async def submit_human_review(request: ReviewRequest):
    """
    Receives an explicit human authorization response (approve/reject) from the frontend
    to resume a paused LangGraph execution context.
    """
    try:
        result = await resume_analysis(
            thread_id=request.thread_id,
            human_approved=request.human_approved
        )
        return {
            "status": "success",
            "updated_state": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume graph: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Launch local server
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)