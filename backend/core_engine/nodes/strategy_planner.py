"""
Strategy Planner Node
=====================
Initiates the 'Map' phase of the Map-Reduce architecture. 
This node ingests a broad, monolithic user query and decomposes it into highly specific, 
independent sub-tasks (sections). This decomposition allows the Orchestrator to spawn 
parallel LangGraph workers for asynchronous execution.
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter

# --- 1. PYDANTIC SCHEMAS ---
class ReportPlanSection(BaseModel):
    """Data structure representing an isolated research thread."""
    title: str = Field(description="The title of the section")
    key_question: str = Field(description="The specific question the worker agent needs to answer using RAG or Web Search")

class ReportPlan(BaseModel):
    """The full blueprint for the concurrent orchestration."""
    report_title: str = Field(description="The overarching title of the complete report")
    background_context: str = Field(description="1-2 paragraphs of foundational context for the worker agents")
    report_outline: List[ReportPlanSection] = Field(description="List of specific sections that need to be researched")


# --- 2. THE SYSTEM PROMPT ---
PLANNER_SYSTEM_PROMPT = """
You are a Senior Research Manager. Today's date is {date}.
Your job is to take a user's broad research query and break it down into a highly structured report outline. 
CRITICAL RULE: You MUST break the topic down into a STRICT MAXIMUM of 3 to 4 sections. Do not generate more than 4 sections under any circumstances. Prioritize depth over breadth.
You must assign specific, independent key questions for each section. These questions will be handed off to your team of AI Worker Agents who will query vector databases and search the web to find the answers.

Guidelines:
- Each section should cover a single, independent topic.
- If the query involves specific architectures, companies, or technologies, explicitly name them in the key questions.
- Provide a brief 'background_context' paragraph to ground the worker agents before they start their research.
"""

# --- 3. THE LANGGRAPH NODE ---
def strategy_planner_node(state: dict):
    """Generates the execution plan and sections array for parallel processing."""
    user_query = state.get("query")
    print(f"🧠 [Planner Node] Breaking down query: '{user_query}'")
    
    router = LLMRouter()
    
    # We use Gemini 2.5 Pro as the reasoning model here because generating a
    # comprehensive, logically ordered outline requires high cognitive capability.
    llm = router.reasoning_model
    
    structured_llm = llm.with_structured_output(ReportPlan)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", PLANNER_SYSTEM_PROMPT),
        ("human", "Generate a research plan for the following query: {query}")
    ])
    
    chain = prompt | structured_llm
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    plan: ReportPlan = chain.invoke({"date": current_date, "query": user_query})
    
    print(f"✅ [Planner Node] Generated outline with {len(plan.report_outline)} sections.")
    
    return {
        "report_plan": plan,
        # Initialize an empty array to aggregate the asynchronous worker outputs
        "completed_sections": [] 
    }
