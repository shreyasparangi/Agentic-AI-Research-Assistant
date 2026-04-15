import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core_engine.orchestrator import ResearchOrchestrator
from core_engine.utilities.vector_db import ingest_pdf_to_chroma

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

# --- 2. RAG UPLOAD ENDPOINT ---
@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Receives a PDF from the frontend, saves it temporarily, and ingests it into ChromaDB."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    # Save the uploaded file temporarily to the local disk
    temp_file_path = f"./{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        # Fire your custom Vector DB ingestion utility
        ingest_pdf_to_chroma(temp_file_path)
        
        # Clean up the temp file after successful ingestion
        os.remove(temp_file_path)
        
        return {"status": "success", "message": f"'{file.filename}' successfully ingested into Vector Database!"}
        
    except Exception as e:
        # Ensure cleanup happens even if ingestion crashes
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f"❌ Upload Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

# To run this server, use the command: uvicorn api:app --reload