"""
Gap Analyzer Node
=================
Acts as the Quality Assurance (QA) gatekeeper for the research loop.
This node critically evaluates the aggregated `research_history` against the target 
`current_section` question. It determines whether the agent has sufficient data to synthesize 
a final answer, or if specific knowledge gaps remain that require further tool execution.
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter

# --- 1. PYDANTIC SCHEMA (The Deterministic JSON Blueprint) ---
# Enforcing a strict schema ensures the LLM's output can be safely parsed into 
# Python booleans and lists, controlling the graph's conditional edges without crashing.
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
def gap_analyzer_node(state: dict):
    """Evaluates the state memory to dictate the next routing direction."""
    user_query = state.get("query", "Unknown query")
    current_section = state.get("current_section", "Unknown section")
    research_history = state.get("research_history", "No research conducted yet.")
    
    print(f"🔍 [Gap Analyzer] Evaluating research state for: '{current_section}'")
    
    # Utilizing Gemini 2.5 Flash for this node because
    # binary decision-making and gap extraction requires low latency, not deep reasoning.
    router = LLMRouter()
    llm = router.fast_model
    
    # Bind the schema to guarantee a structured JSON payload
    structured_llm = llm.with_structured_output(KnowledgeGapOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", GAP_ANALYZER_PROMPT),
        ("human", "Evaluate the current state of the research.")
    ])
    
    chain = prompt | structured_llm
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Attempt to parse the LLM's structured output
        evaluation: KnowledgeGapOutput = chain.invoke({
            "date": current_date, 
            "query": user_query,
            "section_question": current_section,
            "history": research_history
        })
    except Exception as e:
        # SAFETY HATCH: If the model returns malformed structured output, do not crash.
        # Instead, assume we have enough data and force it to synthesize the final report.
        print(f"⚠️ [Gap Analyzer] LLM parsing glitch detected. Deploying safety hatch.")
        evaluation = KnowledgeGapOutput(research_complete=True, outstanding_gaps=[])
        
    if evaluation.research_complete:
        print("✅ [Gap Analyzer] Research complete! Ready to write.")
    else:
        print(f"⚠️ [Gap Analyzer] Found {len(evaluation.outstanding_gaps)} missing gaps. Routing back to tools.")
    
    # Inject the evaluation results back into the global state
    return {
        "research_complete": evaluation.research_complete,
        "current_gaps": evaluation.outstanding_gaps
    }
