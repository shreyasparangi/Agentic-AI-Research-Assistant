"""
Tool Router Node
================
Functions as the Semantic Router for the system.
When the Gap Analyzer identifies missing knowledge, this node maps those abstract gaps 
to specific, actionable tool executions (e.g., routing a broad question to `web_searcher` 
or an internal document question to `rag_retriever`).
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter

# --- 1. PYDANTIC SCHEMAS (The Action Payload Blueprint) ---
class ToolTask(BaseModel):
    """Payload representing a single tool invocation request."""
    gap: str = Field(description="The specific knowledge gap being addressed")
    # Strict Enum-style enforcement to ensure the execution node can parse the command
    tool_name: str = Field(description="MUST BE EXACTLY ONE OF: 'web_searcher', 'web_crawler', 'rag_retriever', or 'arxiv_researcher'")
    query: str = Field(description="The specific search string or URL to pass to the tool (3-6 words preferred)")
    entity_website: Optional[str] = Field(description="The URL to crawl if using the web_crawler", default=None)

class ToolSelectionPlan(BaseModel):
    """The aggregated array of tools to fire concurrently."""
    tasks: List[ToolTask] = Field(description="List of tools to execute in parallel")


def build_fallback_plan(query: str, gaps: List[str]) -> ToolSelectionPlan:
    """
    Build a deterministic tool plan when structured LLM routing fails.
    This keeps the research loop productive instead of executing zero tools.
    """
    combined_text = " ".join([query, *gaps]).lower()
    tasks = []

    if any(term in combined_text for term in ["academic", "paper", "papers", "preprint", "research", "literature", "arxiv"]):
        tasks.append(ToolTask(
            gap=gaps[0] if gaps else query,
            tool_name="arxiv_researcher",
            query=query,
        ))

    if len(tasks) < 3:
        tasks.append(ToolTask(
            gap=gaps[1] if len(gaps) > 1 else (gaps[0] if gaps else query),
            tool_name="web_searcher",
            query=query,
        ))

    return ToolSelectionPlan(tasks=tasks[:3])


# --- 2. THE SYSTEM PROMPT ---
TOOL_ROUTER_PROMPT = """
You are the Action Orchestrator for an AI Research System. Today's date is {date}.
Your job is to look at the current knowledge gaps and select the best tools to find the missing information.

ORIGINAL OVERALL QUERY: {query}
CURRENT KNOWLEDGE GAPS TO ADDRESS:
{gaps}

HISTORY OF FINDINGS SO FAR:
{history}

AVAILABLE TOOLS (CHOOSE FROM THESE EXACT NAMES):
1. 'web_searcher': Use this for general Google searches to find broad topics, news, or external context.
2. 'web_crawler': Use this if you have a specific URL and need to scrape the text from that specific page.
3. 'rag_retriever': Use this to query the local Vector Database. Choose this ONLY if the gap requires reading from the user's provided PDF documents or internal academic literature.
4. 'arxiv_researcher': Use this for academic paper discovery, scientific literature, preprints, and technical research abstracts from arXiv.

Guidelines:
- Generate at most 3 tool tasks. 
- You can call 'web_searcher' multiple times with different queries if needed.
- Prefer 'arxiv_researcher' when the gap asks for academic papers, recent research methods, scientific evidence, or preprint literature.
- If a gap doesn't clearly match the local RAG database, default to the web_searcher.
- Keep the 'query' parameter concise and highly targeted.

CRITICAL OUTPUT INSTRUCTIONS:
You are a machine-to-machine routing API. You MUST return ONLY valid, raw JSON. 
- DO NOT wrap the output in ```json or any markdown formatting.
- DO NOT output any introductory or conversational text.
- Your entire response must be a JSON object or JSON array.
"""

# --- 3. THE LANGGRAPH NODE ---
def tool_router_node(state: dict):
    """Maps identified knowledge gaps to specific functional APIs."""
    user_query = state.get("query", "")
    current_gaps = state.get("current_gaps", [])
    research_history = state.get("research_history", "")
    
    print(f"🔀 [Tool Router] Routing {len(current_gaps)} gaps to specialized tools...")
    
    router = LLMRouter()
    
    # We use the strictly deterministic Routing Model to prevent JSON hallucination glitches.
    llm = router.routing_model
    
    structured_llm = llm.with_structured_output(ToolSelectionPlan)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", TOOL_ROUTER_PROMPT),
        ("human", "Select the tools to address the current knowledge gaps.")
    ])
    
    chain = prompt | structured_llm
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        plan: ToolSelectionPlan = chain.invoke({
            "date": current_date, 
            "query": user_query,
            "gaps": "\n".join([f"- {gap}" for gap in current_gaps]),
            "history": research_history
        })
    except Exception as e:
        print(f"⚠️ [Tool Router] LLM parsing glitch detected. Deploying safety hatch.")
        print(f"[Tool Router] LLM routing failed: {type(e).__name__}: {e}")
        print("[Tool Router] Deploying deterministic fallback plan.")
        plan = build_fallback_plan(user_query, current_gaps)
    
    print(f"🛠️ [Tool Router] Selected {len(plan.tasks)} tools to execute.")
    for task in plan.tasks:
        print(f"   -> Assigned '{task.tool_name}' with query: '{task.query}'")
    
    # Inject the planned tasks back into state for the execution node to process
    return {
        "pending_tool_tasks": plan.tasks
    }
