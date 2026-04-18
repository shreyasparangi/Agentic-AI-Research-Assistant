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
import time
import json
from core_engine.nodes.strategy_planner import strategy_planner_node
from core_engine.loop_worker import build_loop_worker, ResearchState
from core_engine.utilities.progress import sanitize_status

class ResearchOrchestrator:
    """
    Manages the lifecycle and execution of LangGraph research loops.
    Handles dynamic scaling, state initialization, and concurrency throttling.
    """
    
    def __init__(self):
        self.worker_graph = build_loop_worker()

    async def _run_single_section(self, overall_query: str, section_title: str, section_question: str, semaphore: asyncio.Semaphore, progress_queue: asyncio.Queue | None = None) -> str:
        async with semaphore:
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
            
            if progress_queue is not None:
                initial_state["progress_queue"] = progress_queue
                progress_queue.put_nowait(sanitize_status(f"[Worker] Starting research for {section_title}."))

            final_state = await self.worker_graph.ainvoke(initial_state)
            return final_state["completed_sections"][0]

    async def run_deep_research(self, query: str, progress_queue: asyncio.Queue | None = None) -> str:
        print(f"\n🚀 [Orchestrator] Starting Deep Research for: '{query}'\n")
        
        if progress_queue is not None:
            progress_queue.put_nowait(sanitize_status("[Orchestrator] Starting deep parallel research."))

        planner_state = {"query": query}
        if progress_queue is not None:
            planner_state["progress_queue"] = progress_queue
        plan_state = strategy_planner_node(planner_state)
        report_plan = plan_state["report_plan"]
        
        print(f"\n📋 [Orchestrator] Blueprint generated! {len(report_plan.report_outline)} sections required.")
        
        semaphore = asyncio.Semaphore(2)
        
        tasks = []
        for section in report_plan.report_outline:
            task_coroutine = self._run_single_section(query, section.title, section.key_question, semaphore, progress_queue)
            task = asyncio.create_task(task_coroutine)
            tasks.append(task)
            
        print("\n⚡ [Orchestrator] Firing throttled research loops...\n")
        
        try:
            completed_sections = await asyncio.gather(*tasks)
        except Exception as e:
            print(f"\n🚨 [Orchestrator] CRITICAL WORKER FAILURE: {str(e)}")
            print("🛑 [Orchestrator] Emergency Abort! Cancelling all other background workers to protect API billing...")
            for t in tasks:
                if not t.done():
                    t.cancel()
            raise e
            
        print("\n📚 [Orchestrator] All workers finished. Compiling final report...\n")
        
        final_report = f"# {report_plan.report_title}\n\n"
        final_report += f"**Background Context:**\n{report_plan.background_context}\n\n"
        final_report += "---\n\n"
        final_report += "\n\n".join(completed_sections)
        
        print("✅ [Orchestrator] Deep Research Architecture Execution Complete!\n")
        return final_report
    
    async def run_single_research(self, query: str, progress_queue: asyncio.Queue | None = None) -> str:
        print(f"\n🚀 [Orchestrator] Starting Single Iterative Research for: '{query}'\n")
        
        initial_state: ResearchState = {
            "query": query,
            "current_section_title": "Research Summary",
            "current_section": query,
            "research_history": "",
            "research_complete": False,
            "current_gaps": [query], 
            "pending_tool_tasks": [],
            "completed_sections": [],
            "loop_count": 0
        }
        
        if progress_queue is not None:
            initial_state["progress_queue"] = progress_queue
            progress_queue.put_nowait(sanitize_status("[Orchestrator] Starting single-agent iterative research."))

        final_state = await self.worker_graph.ainvoke(initial_state)
        
        print("\n✅ [Orchestrator] Single Iterative Research Complete!\n")
        return final_state["completed_sections"][0]

    async def stream_research(self, query: str, mode: str):
        """
        Streams sanitized progress events and calculates final Telemetry.
        """
        progress_queue: asyncio.Queue = asyncio.Queue()
        
        # 1. Start the Telemetry Trackers
        start_time = time.time()
        cache_hits = 0
        api_calls = 0

        if mode == "single":
            research_task = asyncio.create_task(self.run_single_research(query, progress_queue))
        elif mode == "deep":
            research_task = asyncio.create_task(self.run_deep_research(query, progress_queue))
        else:
            yield {"event": "error", "data": "Invalid mode. Use 'single' or 'deep'."}
            return

        while not research_task.done():
            try:
                message = await asyncio.wait_for(progress_queue.get(), timeout=0.25)
                clean_msg = sanitize_status(message)
                
                # 2. Dynamically Track Network vs Cache
                if "Cache hit" in clean_msg:
                    cache_hits += 1
                elif "Searching" in clean_msg or "Evaluating" in clean_msg or "Querying" in clean_msg:
                    api_calls += 1
                
                yield {"event": "progress", "data": clean_msg}
                
                # 3. GLOBAL THROTTLE: Protects the Gemini 15 RPM Free Tier limit
                if "Searching" in clean_msg or "Evaluating" in clean_msg or "Querying" in clean_msg:
                    await asyncio.sleep(4.5)
                    
            except asyncio.TimeoutError:
                continue

        # Drain the remaining queue
        while not progress_queue.empty():
            message = progress_queue.get_nowait()
            clean_msg = sanitize_status(message)
            if "Cache hit" in clean_msg:
                cache_hits += 1
            yield {"event": "progress", "data": clean_msg}

        try:
            report = await research_task
            
            # 4. CALCULATE FINAL TELEMETRY
            execution_time = round(time.time() - start_time, 2)
            tokens_saved = cache_hits * 4500 # Estimate of tokens saved by bypassing the scrape
            
            telemetry_payload = json.dumps({
                "execution_time": execution_time,
                "cache_hits": cache_hits,
                "api_calls": api_calls,
                "tokens_saved": tokens_saved
            })
            
            # Emit Telemetry Event, THEN the complete report
            yield {"event": "telemetry", "data": telemetry_payload}
            yield {"event": "complete", "data": report}
            
        except Exception as e:
            yield {"event": "error", "data": sanitize_status(str(e))}