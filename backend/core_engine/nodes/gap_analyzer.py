"""
Gap Analyzer Node
=================
Acts as the Quality Assurance (QA) gatekeeper for the research loop.
"""

import asyncio
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter
from core_engine.utilities.progress import emit_progress

# --- 1. PYDANTIC SCHEMA ---
class KnowledgeGapOutput(BaseModel):
    """Output schema enforcing deterministic control flow variables."""
    research_complete: bool = Field(description="True if the research findings are complete enough to write the section, False otherwise")
    outstanding_gaps: List[str] = Field(description="Up to 3 specific knowledge gaps that still need to be addressed")

# --- 2. THE SYSTEM PROMPT ---
GAP_ANALYZER_PROMPT = """
You are a Research State Evaluator. Today's date is {date}.
Your job is to critically analyze the current state of a research task, identify what knowledge gaps still exist, and determine if the research loop can end.

ORIGINAL OVERALL QUERY: {query}
SPECIFIC SECTION BEING RESEARCHED: {section_question}

HISTORY OF FINDINGS AND ACTIONS SO FAR:
{history}

Your task:
1. Review the history of findings against the section question.
2. Determine if you have enough detailed, factual information to write a comprehensive answer.
3. If yes, set research_complete to true and outstanding_gaps to an empty list.
4. If no, set research_complete to false and identify up to 3 specific knowledge gaps that need to be addressed next.
"""

# --- 3. THE LANGGRAPH NODE ---
# UPGRADE: Converted to an async node to support non-blocking throttles
async def gap_analyzer_node(state: dict):
    """Evaluates the state memory to dictate the next routing direction."""
    user_query = state.get("query", "Unknown query")
    current_section = state.get("current_section", "Unknown section")
    research_history = state.get("research_history", "No research conducted yet.")
    emit_progress(state, "[Gap Analyzer] Evaluating research coverage and identifying missing information.")
    
    print(f"🔍 [Gap Analyzer] Evaluating research state for: '{current_section}'")
    
    # THROTTLE: Artificially delay execution by 4 seconds to protect the Gemini 15 RPM Free Tier Limit.
    # This prevents the SQLite cache from triggering a 429 Quota Error on rapid repeat searches.
    await asyncio.sleep(4)
    
    router = LLMRouter()
    llm = router.fast_model
    
    structured_llm = llm.with_structured_output(KnowledgeGapOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", GAP_ANALYZER_PROMPT),
        ("human", "Evaluate the current state of the research.")
    ])
    
    chain = prompt | structured_llm
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # UPGRADE: Switched to asynchronous invocation
        evaluation: KnowledgeGapOutput = await chain.ainvoke({
            "date": current_date, 
            "query": user_query,
            "section_question": current_section,
            "history": research_history
        })
    except Exception as e:
        print(f"⚠️ [Gap Analyzer] LLM parsing glitch detected. Deploying safety hatch.")
        # THE FIX: If it glitches, DO NOT quit. Force it to route back to the tools.
        evaluation = KnowledgeGapOutput(
            research_complete=False, 
            outstanding_gaps=[f"Retrieve more detailed sources regarding: {current_section}"]
        )
        
    if evaluation.research_complete:
        emit_progress(state, "[Gap Analyzer] Research coverage is sufficient. Preparing the final report.")
        print("✅ [Gap Analyzer] Research complete! Ready to write.")
    else:
        emit_progress(state, f"[Gap Analyzer] Found {len(evaluation.outstanding_gaps)} knowledge gaps. Selecting the best research tools.")
        print(f"⚠️ [Gap Analyzer] Found {len(evaluation.outstanding_gaps)} missing gaps. Routing back to tools.")
    
    return {
        "research_complete": evaluation.research_complete,
        "current_gaps": evaluation.outstanding_gaps
    }