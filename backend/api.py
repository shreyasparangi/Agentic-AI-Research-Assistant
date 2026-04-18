import os
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from werkzeug.utils import secure_filename

from core_engine.orchestrator import ResearchOrchestrator
from core_engine.utilities.vector_db import ingest_pdf_to_chroma
from core_engine.utilities.progress import sanitize_status

# Initialize the FastAPI App
app = FastAPI(title="Agentic AI Research API")

# --- CORS CONFIGURATION ---
# This allows your local HTML/JS frontend to talk to this Python server 
# without getting blocked by the browser's security policies.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Engine once when the server starts
orchestrator = ResearchOrchestrator()

# --- SCHEMAS ---
class ResearchRequest(BaseModel):
    query: str
    mode: str  # Must be 'single' or 'deep'

# --- 1. RESEARCH ENDPOINT ---
@app.post("/api/research")
async def generate_research(request: ResearchRequest):
    """Takes a query from the frontend and fires the LangGraph architecture."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
        
    try:
        if request.mode == "single":
            report = await orchestrator.run_single_research(request.query)
        elif request.mode == "deep":
            report = await orchestrator.run_deep_research(request.query)
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'single' or 'deep'.")
            
        return {"status": "success", "report": report}
    
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def format_sse_event(event: str, payload: dict) -> str:
    """Format a dictionary payload as a Server-Sent Event chunk."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"


async def research_event_stream(request: ResearchRequest):
    """Yield clean progress updates, telemetry, and a final report as SSE chunks."""
    try:
        async for update in orchestrator.stream_research(request.query, request.mode):
            event_type = update["event"]
            data = update["data"]

            if event_type == "progress":
                yield format_sse_event("progress", {"message": sanitize_status(data)})
            
            elif event_type == "telemetry":
                # NEW: Catch the telemetry event, parse the JSON string back to a dict, 
                # and safely route it to the frontend dashboard.
                yield format_sse_event("telemetry", json.loads(data))
                
            elif event_type == "complete":
                yield format_sse_event("complete", {"report": data})
                
            else:
                # Only trigger an error if the event type is completely unknown
                yield format_sse_event("error", {"message": sanitize_status(data)})
                return
                
    except Exception as e:
        yield format_sse_event("error", {"message": sanitize_status(str(e))})


@app.post("/api/research-stream")
async def stream_research(request: ResearchRequest):
    """Streams LangGraph progress updates and the final Markdown report via SSE."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    if request.mode not in {"single", "deep"}:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'single' or 'deep'.")

    return StreamingResponse(
        research_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- 2. RAG UPLOAD ENDPOINT ---
@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Receives a PDF from the frontend, saves it temporarily, and ingests it into ChromaDB."""
    original_filename = file.filename or ""
    safe_filename = secure_filename(original_filename)

    if not safe_filename or Path(safe_filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
    temp_dir = tempfile.mkdtemp(prefix="agentic_upload_")
    temp_file_path = os.path.join(temp_dir, unique_filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        # Fire your custom Vector DB ingestion utility
        ingest_pdf_to_chroma(temp_file_path)
        
        return {"status": "success", "message": f"'{safe_filename}' successfully ingested into Vector Database!"}
        
    except Exception as e:
        print(f"❌ Upload Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
    finally:
        # Ensure cleanup happens even if ingestion crashes
        shutil.rmtree(temp_dir, ignore_errors=True)

# To run this server, use the command: uvicorn api:app --reload
