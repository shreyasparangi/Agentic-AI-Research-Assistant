"""
Web Scraper Action Wrapper
==========================
Implements the LLM Filter Pattern for targeted domain crawling.
This module intercepts the raw, noisy HTML text returned by the breadth-first web crawler,
passes it through a low-latency LLM to extract highly specific facts addressing the 
knowledge gap, and formats the output deterministically before it hits the global state.
"""

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter
from core_engine.utilities.web_crawler import web_crawler

# --- 1. PYDANTIC SCHEMA (The Output Contract) ---
# By forcing the LLM to adhere to this schema, we guarantee that the output will 
# always have a clean summary string and a strictly typed list of URLs. This prevents
# the LLM from returning conversational fluff (e.g., "Sure, here is your summary:").
class ScrapeSummaryOutput(BaseModel):
    """Structured output for the web scraping action node."""
    summary: str = Field(description="A detailed summary addressing the knowledge gap, using exact facts from the scraped text.")
    sources: list[str] = Field(description="List of exact URLs from the scraped text that provided the information.")


# --- 2. THE SYSTEM PROMPT ---
# Strict grounding directives are applied here to prevent hallucinations.
# The AI is explicitly instructed to act purely as an extraction engine, not a generative engine.
SCRAPE_ACTION_PROMPT = """
You are an AI Research Analyst. Your job is to read raw, scraped text from a specific website and extract the exact information needed to fill a knowledge gap.

KNOWLEDGE GAP TO FILL: {gap}

RAW SCRAPED WEBSITE DATA:
{raw_data}

GUIDELINES:
1. Write a detailed summary that specifically answers the knowledge gap using ONLY the provided text.
2. Quote exact facts, figures, and numbers.
3. Include inline citations using brackets [1], [2] next to the facts you extract.
4. If the raw data does not contain the answer to the gap, explicitly state "No relevant results found."
5. Do NOT hallucinate information outside of the provided raw website data.
"""


# --- 3. THE ACTION NODE WRAPPER ---
async def execute_scrape_action(gap: str, target_url: str) -> str:
    """
    Executes the deep web crawl, then uses the Fast LLM to summarize the results 
    before passing it back to the main LangGraph memory.
    
    Args:
        gap (str): The specific question or missing data we are looking for.
        target_url (str): The root domain to execute the BFS crawl on.
        
    Returns:
        str: A highly compressed, cited markdown summary of the extracted data.
    """
    if not target_url or target_url.lower() == "null":
        return f"Scrape failed: No valid URL provided to crawl for gap: '{gap}'"

    print(f"🕸️ [Action: Scraper] Crawling target URL: '{target_url}'")
    
    # 1. Fire the raw utility tool (The I/O bound network request)
    raw_text = await web_crawler.ainvoke({"starting_url": target_url})
    
    # Fail-fast mechanism if the target server blocked the scraper (e.g., 403 Forbidden)
    if not raw_text or "Failed" in raw_text:
        return f"Crawler failed to extract text from '{target_url}'."

    print(f"🧠 [Action: Scraper] Reading {len(raw_text)} characters of scraped site data...")

    # 2. Initialize the Fast Model (The "Filter")
    # We use Llama 3.1 8B here because parsing text is a low-reasoning, high-speed task.
    router = LLMRouter()
    llm = router.fast_model
    
    # Bind the schema for strict JSON compliance
    structured_llm = llm.with_structured_output(ScrapeSummaryOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SCRAPE_ACTION_PROMPT),
        ("human", "Summarize the scraped data to fill the knowledge gap.")
    ])
    
    chain = prompt | structured_llm
    
    # 3. Compress the data (Compute-bound processing)
    try:
        result: ScrapeSummaryOutput = await chain.ainvoke({"gap": gap, "raw_data": raw_text})
        
        # 4. Format beautifully for the LangGraph state memory
        formatted_output = f"### Scraped Website Summary: '{target_url}'\n{result.summary}\n\n**Sources:**\n"
        for i, src in enumerate(result.sources, 1):
            formatted_output += f"[{i}] {src}\n"
            
        print(f"✅ [Action: Scraper] Successfully compressed site data into summary.")
        return formatted_output

    except Exception as e:
        # Graceful error handling prevents a single parsing failure from crashing the entire worker loop
        print(f"⚠️ [Action: Scraper] LLM parsing failed: {str(e)}")
        return f"Raw text scraped from {target_url} but summarization failed.\n\nRaw Text snippet: {raw_text[:500]}"