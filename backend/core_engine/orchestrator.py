"""
Orchestrator Module
===================
The master controller for the entire Agentic AI system. 
This module implements a Map-Reduce concurrency pattern, capable of breaking down 
a complex user query into sub-tasks (Map), spinning up independent asynchronous 
LangGraph workers to research each sub-task in parallel, and aggregating the results
into a cohesive final document (Reduce).
"""

import asyncio
from core_engine.nodes.strategy_planner import strategy_planner_node
from core_engine.loop_worker import build_loop_worker, ResearchState

class ResearchOrchestrator:
    """
    Manages the lifecycle and execution of LangGraph research loops.
    Handles dynamic scaling, state initialization, and concurrency throttling.
    """
    
    def __init__(self):
        # Pre-compile the LangGraph state machine once upon initialization.
        # This compiled graph acts as a blueprint that can be cloned and run concurrently.
        self.worker_graph = build_loop_worker()

    async def _run_single_section(self, overall_query: str, section_title: str, section_question: str, semaphore: asyncio.Semaphore) -> str:
        """
        Initializes and executes a single instance of the LangGraph worker.
        
        Args:
            overall_query (str): The main topic of the research.
            section_title (str): The specific subsection title for this worker.
            section_question (str): The targeted question this worker must answer.
            semaphore (asyncio.Semaphore): A concurrency lock to prevent API rate-limit exhaustion.
            
        Returns:
            str: The synthesized markdown content for this specific section.
        """
        # Acquire the semaphore lock. If the max concurrent worker limit is reached,
        # this execution will pause here until a slot opens up.
        async with semaphore:
            # Initialize a fresh, isolated memory state for this specific worker thread
            initial_state: ResearchState = {
                "query": overall_query,
                "current_section_title": section_title,
                "current_section": section_question,
                "research_history": "",
                "research_complete": False,
                "current_gaps": [section_question], 
                "pending_tool_tasks": [],
                "completed_sections": [],
                "loop_count": 0
            }
            
            print(f"🧵 [Worker Spawned] Starting research loop for: '{section_title}'")
            
            # Execute the LangGraph state machine asynchronously
            final_state = await self.worker_graph.ainvoke(initial_state)
            
            # Extract and return the finalized section text
            return final_state["completed_sections"][0]

    async def run_deep_research(self, query: str) -> str:
        """
        The primary Map-Reduce execution pipeline.
        
        Workflow:
        1. Planning: Uses a reasoning LLM to generate a structured outline.
        2. Execution: Spawns a highly-concurrent pool of LangGraph workers for each section.
        3. Aggregation: Waits for all workers to finish and concatenates the final report.
        
        Args:
            query (str): The user's input topic.
            
        Returns:
            str: A fully formatted, multi-section Markdown document with citations.
        """
        print(f"\n🚀 [Orchestrator] Starting Deep Research for: '{query}'\n")
        
        # Step 1: Generate the Blueprint (Map)
        plan_state = strategy_planner_node({"query": query})
        report_plan = plan_state["report_plan"]
        
        print(f"\n📋 [Orchestrator] Blueprint generated! {len(report_plan.report_outline)} sections required.")
        
        # --- CONCURRENCY THROTTLING ---
        # A semaphore limits the number of concurrent asynchronous tasks.
        # Setting this to 2 ensures we do not overwhelm the LLM API and trigger a 429 Resource Exhausted error.
        semaphore = asyncio.Semaphore(2)
        
        # Step 2: Spawn Workers (Execute)
        tasks = []
        for section in report_plan.report_outline:
            # WRAP in asyncio.create_task so we have physical control over the thread
            task_coroutine = self._run_single_section(query, section.title, section.key_question, semaphore)
            task = asyncio.create_task(task_coroutine)
            tasks.append(task)
            
        print("\n⚡ [Orchestrator] Firing throttled research loops...\n")
        
        try:
            # Await all parallel workers.
            completed_sections = await asyncio.gather(*tasks)
            
        except Exception as e:
            # --- EMERGENCY KILL SWITCH ---
            print(f"\n🚨 [Orchestrator] CRITICAL WORKER FAILURE: {str(e)}")
            print("🛑 [Orchestrator] Emergency Abort! Cancelling all other background workers to protect API billing...")
            
            for t in tasks:
                if not t.done():
                    t.cancel() # Instantly kills the zombie thread
                    
            # Re-raise the error so the frontend knows it failed
            raise e
            
        print("\n📚 [Orchestrator] All workers finished. Compiling final report...\n")
        
        # Step 3: Compile the Final Output (Reduce)
        final_report = f"# {report_plan.report_title}\n\n"
        final_report += f"**Background Context:**\n{report_plan.background_context}\n\n"
        final_report += "---\n\n"
        final_report += "\n\n".join(completed_sections)
        
        print("✅ [Orchestrator] Deep Research Architecture Execution Complete!\n")
        return final_report
    
    async def run_single_research(self, query: str) -> str:
        """
        A lightweight execution mode that bypasses the multi-agent planning phase.
        Treats the user's query as a single section and routes it directly to a single worker loop.
        
        Args:
            query (str): The specific question or topic to research.
            
        Returns:
            str: The synthesized Markdown response.
        """
        print(f"\n🚀 [Orchestrator] Starting Single Iterative Research for: '{query}'\n")
        
        initial_state: ResearchState = {
            "query": query,
            "current_section_title": "Research Summary",
            "current_section": query, # Treat the raw query as the target gap
            "research_history": "",
            "research_complete": False,
            "current_gaps": [query], 
            "pending_tool_tasks": [],
            "completed_sections": [],
            "loop_count": 0
        }
        
        # Execute the single worker directly
        final_state = await self.worker_graph.ainvoke(initial_state)
        
        print("\n✅ [Orchestrator] Single Iterative Research Complete!\n")
        
        # The Synthesizer node inherently adds the title, so we just return the raw text block
        return final_state["completed_sections"][0]