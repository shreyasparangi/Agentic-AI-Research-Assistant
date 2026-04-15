import streamlit as st
import asyncio
import os
from dotenv import load_dotenv

from core_engine.orchestrator import ResearchOrchestrator

# Load API Keys
load_dotenv()

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Agentic AI Researcher",
    page_icon="🧠",
    layout="wide"
)

# --- HEADER ---
st.title("🧠 Agentic AI Research System")
st.markdown("""
Welcome to the multi-agent research architecture. 
Enter a topic below, choose your depth, and the AI will autonomously crawl the web, synthesize data, and draft a fully cited academic report.
""")
st.markdown("---")

# --- UI CONTROLS ---
col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_input("Enter your research topic:", placeholder="e.g., Quantum Computing, Black Holes, LangGraph Architecture")

with col2:
    mode = st.radio(
        "Research Depth:",
        ("Single Iterative Loop", "Deep Research (Parallel)")
    )

# --- ASYNC EXECUTION WRAPPER ---
async def execute_research(search_query: str, search_mode: str):
    """Wrapper to run the Orchestrator based on UI selection."""
    orchestrator = ResearchOrchestrator()
    if search_mode == "Single Iterative Loop":
        return await orchestrator.run_single_research(search_query)
    else:
        return await orchestrator.run_deep_research(search_query)

# --- EXECUTION BUTTON ---
if st.button("🚀 Generate Research Report", type="primary"):
    if not query.strip():
        st.warning("Please enter a research topic to begin.")
    else:
        # Create a UI spinner while the backend does the heavy lifting
        with st.spinner(f"Agents are actively researching '{query}'... This may take a few minutes."):
            try:
                # Windows specific asyncio fix
                if os.name == 'nt':
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                # Streamlit runs synchronously, so we must manually manage the async loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                final_report = loop.run_until_complete(execute_research(query, mode))
                
                # Save the output to a file (just like the CLI did)
                with open("final_report.md", "w", encoding="utf-8") as f:
                    f.write(final_report)
                
                st.success("✅ Research Complete! Report successfully generated.")
                
                # --- DISPLAY THE REPORT ---
                st.markdown("---")
                st.markdown(final_report)
                
            except Exception as e:
                st.error(f"❌ Fatal Error occurred during execution:\n{str(e)}")