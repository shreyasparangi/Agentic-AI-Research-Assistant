"""
Loop Worker Module
==================
This module defines the core LangGraph state machine representing a single autonomous "Worker Agent".
It utilizes a cyclic graph architecture to iteratively evaluate knowledge gaps, route to 
appropriate external tools (Search, Scrape, RAG), execute them asynchronously, and synthesize 
the findings.
"""

import operator
from langgraph.graph import StateGraph, END

# --- IMPORT THE SHARED STATE ---
from core_engine.nodes.base_node import ResearchState

# --- IMPORT THE GRAPH NODES ---
from core_engine.nodes.gap_analyzer import gap_analyzer_node
from core_engine.nodes.tool_router import tool_router_node
from core_engine.nodes.synthesizer import synthesizer_node

# --- IMPORT THE ACTION WRAPPERS (The Filters) ---
from core_engine.nodes.actions.web_searcher import execute_search_action
from core_engine.nodes.actions.web_scraper import execute_scrape_action
from core_engine.nodes.actions.rag_retriever import execute_rag_action
from core_engine.utilities.arxiv_search import arxiv_researcher


# --- 1. THE TOOL EXECUTION NODE ---
import asyncio

# --- 1. THE TOOL EXECUTION NODE (CONCURRENT UPGRADE) ---
async def execute_tools_node(state: ResearchState):
    """
    Executes pending tool requests concurrently using asyncio.
    """
    tasks = state.get("pending_tool_tasks", [])
    print(f"⚙️ [Tool Executor] Firing {len(tasks)} tools concurrently...")
    
    # Define an internal async wrapper to process each task
    async def run_task(task):
        if task.tool_name == "web_searcher":
            result = await execute_search_action(gap=task.gap, query=task.query)
            return f"--- WEB SEARCH RESULTS FOR '{task.query}' ---\n{result}"
            
        elif task.tool_name == "rag_retriever":
            result = await execute_rag_action(gap=task.gap, query=task.query)
            return f"--- RAG DATABASE RESULTS FOR '{task.query}' ---\n{result}"
            
        elif task.tool_name == "web_crawler":
            target_url = task.entity_website if task.entity_website else task.query
            result = await execute_scrape_action(gap=task.gap, target_url=target_url)
            return f"--- WEB SCRAPE RESULTS FOR '{target_url}' ---\n{result}"

        elif task.tool_name == "arxiv_researcher":
            result = await arxiv_researcher.ainvoke({"query": task.query})
            return f"--- ARXIV RESEARCH RESULTS FOR '{task.query}' ---\n{result}"
        
        return ""

    # Fire all tools at the exact same millisecond!
    new_findings = await asyncio.gather(*(run_task(task) for task in tasks))
    
    # Combine all individual tool findings into a single chronological block
    combined_findings = "\n\n".join(new_findings) + "\n\n"
    current_loops = state.get("loop_count", 0)
    
    return {
        "research_history": combined_findings,
        "loop_count": current_loops + 1
    }


# --- 2. THE CONDITIONAL ROUTING LOGIC ---
def check_research_status(state: ResearchState):
    """
    The traffic controller for the StateGraph.
    
    Evaluates the current state to determine if the agent should continue iterating
    through the research loop or break out and proceed to document synthesis.
    Includes a hard-stop safety mechanism to prevent infinite API loops.
    
    Args:
        state (ResearchState): The current memory state.
        
    Returns:
        str: The name of the next node to transition to.
    """
    # Hard safety limit: Force synthesis after 3 tool execution loops to conserve API quota
    if state.get("loop_count", 0) >= 3:
        print("🛑 [System] Max iterations reached. Forcing Synthesis.")
        return "write_section"
        
    # Natural exit: The Gap Analyzer determined all questions have been answered
    if state.get("research_complete"):
        return "write_section"
        
    # Default behavior: Continue the research cycle
    return "fetch_more_data"


# --- 3. BUILD THE GRAPH ---
def build_loop_worker():
    """
    Compiles and constructs the LangGraph state machine.
    
    This function defines the topology of the agentic workflow, linking cognitive nodes
    (evaluation, routing, synthesis) with action nodes (tool execution) via directed edges.
    
    Returns:
        CompiledGraph: An executable LangGraph workflow ready for invocation.
    """
    workflow = StateGraph(ResearchState)
    
    # 1. Register all nodes to the graph
    workflow.add_node("evaluate_gaps", gap_analyzer_node)
    workflow.add_node("route_tools", tool_router_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("synthesize", synthesizer_node)
    
    # 2. Define the Entry Point
    workflow.set_entry_point("evaluate_gaps")
    
    # 3. Define the Dynamic/Conditional Edge
    # This determines whether we gather more data or write the final report
    workflow.add_conditional_edges(
        "evaluate_gaps",
        check_research_status,
        {
            "fetch_more_data": "route_tools",
            "write_section": "synthesize"
        }
    )
    
    # 4. Define the Static Edges (The standard execution pipeline)
    workflow.add_edge("route_tools", "execute_tools")
    workflow.add_edge("execute_tools", "evaluate_gaps") # Close the loop
    
    # 5. Define the Exit Point
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()
