import asyncio
import os
from dotenv import load_dotenv

# Load environment variables (API Keys)
load_dotenv()

from core_engine.orchestrator import ResearchOrchestrator
from core_engine.utilities.vector_db import ingest_pdf_to_chroma

async def main():
    print("🚀 Initializing Agentic AI Research System...")
    
    # --- OPTIONAL: Prime the RAG Database ---
    # If you have a specific PDF you want the AI to know about, put it in the root folder.
    # We will check if it exists and ingest it before starting the research.
    sample_pdf = "knowledge_base.pdf"
    if os.path.exists(sample_pdf):
        print(f"\n📚 Found local knowledge base '{sample_pdf}'. Ingesting into Vector DB...")
        ingest_pdf_to_chroma(sample_pdf)
    else:
        print(f"\nℹ️ No '{sample_pdf}' found in root. Skipping local RAG ingestion.")

    # --- GET USER QUERY ---
    print("\n" + "="*50)
    query = input("Enter your research topic:\n> ")
    print("="*50 + "\n")
    
    if not query.strip():
        print("No query provided. Shutting down.")
        return

    # --- EXECUTE ARCHITECTURE ---
    orchestrator = ResearchOrchestrator()
    
    try:
        final_report = await orchestrator.run_single_research(query)
        # final_report = await orchestrator.run_deep_research(query)
        
        # --- SAVE THE OUTPUT ---
        output_file = "final_report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_report)
            
        print(f"\n🎉 SUCCESS! Full academic report generated and saved to '{output_file}'")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")

if __name__ == "__main__":
    # Windows-specific fix for asyncio loops
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())