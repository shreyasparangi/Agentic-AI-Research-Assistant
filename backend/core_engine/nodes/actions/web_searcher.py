"""
Web Searcher Action Wrapper
===========================
The primary external data ingestion filter. 
Prevents "Context Window Collapse" by converting 8,000+ characters of raw Google Search 
HTML into a concise, 150-word factual summary before allowing it to enter the LangGraph 
State memory. This ensures the system remains fast and within API token limits over multiple loops.
"""

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter
from core_engine.utilities.google_search import web_searcher

# --- 1. PYDANTIC SCHEMA ---
class SearchSummaryOutput(BaseModel):
    """Structured output for the search action node."""
    summary: str = Field(description="A detailed summary addressing the knowledge gap, using exact facts and figures.")
    sources: list[str] = Field(description="List of exact URLs that provided the information used in the summary.")


# --- 2. THE SYSTEM PROMPT ---
SEARCH_ACTION_PROMPT = """
You are an AI Research Analyst. Your job is to read raw, scraped web text and extract the exact information needed to fill a specific knowledge gap.

KNOWLEDGE GAP TO FILL: {gap}

RAW WEB DATA:
{raw_data}

GUIDELINES:
1. Write a detailed summary that specifically answers the knowledge gap using the provided text.
2. Quote exact facts, figures, and numbers.
3. Include inline citations using brackets [1], [2] next to the facts you extract.
4. If the raw data does not contain the answer to the gap, explicitly state "No relevant results found."
5. Do NOT hallucinate information outside of the provided raw web data.
"""


# --- 3. THE ACTION NODE WRAPPER ---
async def execute_search_action(gap: str, query: str) -> str:
    """
    Executes the raw web search, then uses the Fast LLM to summarize the results 
    before passing it back to the main LangGraph memory.
    """
    print(f"🔎 [Action: Search] Fetching raw data for query: '{query}'")
    
    # 1. Fire the raw utility tool (The "Hands")
    # This triggers the Serper API and the concurrent Beautifulsoup HTML scrapers.
    raw_text = await web_searcher.ainvoke({"query": query})
    
    # If the search failed or returned nothing
    if not raw_text or "Error" in raw_text:
        return f"Search failed for '{query}'. Raw error: {raw_text}"

    print(f"🧠 [Action: Search] Reading {len(raw_text)} characters of raw HTML text...")

    # 2. Initialize the Fast Model (The "Filter")
    router = LLMRouter()
    llm = router.fast_model
    
    # Force the output into our clean Pydantic schema
    structured_llm = llm.with_structured_output(SearchSummaryOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SEARCH_ACTION_PROMPT),
        ("human", "Summarize the raw data to fill the knowledge gap.")
    ])
    
    chain = prompt | structured_llm
    
    # 3. Compress the data
    try:
        result: SearchSummaryOutput = await chain.ainvoke({"gap": gap, "raw_data": raw_text})
        
        # 4. Format beautifully for the LangGraph state memory
        # We preserve the URL lineage so the Synthesizer node can build a bibliography later.
        formatted_output = f"### Web Search Summary: '{query}'\n{result.summary}\n\n**Sources:**\n"
        for i, src in enumerate(result.sources, 1):
            formatted_output += f"[{i}] {src}\n"
            
        print(f"✅ [Action: Search] Successfully compressed data into summary.")
        return formatted_output

    except Exception as e:
        print(f"⚠️ [Action: Search] LLM parsing failed: {str(e)}")
        return f"Raw text retrieved but summarization failed: {str(e)}\n\nRaw Text snippet: {raw_text[:500]}"