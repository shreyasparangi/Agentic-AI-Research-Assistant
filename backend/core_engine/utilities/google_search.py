"""
Google Search Utility Module
============================
This module handles real-time external data retrieval. It uses the Serper API to 
query Google, followed by asynchronous, concurrent scraping of the top results using aiohttp.
Designed to be highly performant and network-efficient, it actively prevents LLM 
context-window bloat by strictly enforcing content length limits.
"""

import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from core_engine.utilities.cache_manager import get_cached_content, save_to_cache

# Hard limit on scraped characters to prevent overwhelming the LLM's context window.
# 8000 characters is roughly 1500-2000 tokens, which is the optimal reading size.
CONTENT_LENGTH_LIMIT = 8000 

# Prevent the scraper from downloading binary files or massive PDFs that would crash the parser.
RESTRICTED_EXTENSIONS = [".pdf", ".doc", ".xls", ".ppt", ".zip", ".png", ".jpg", ".mp4", ".mp3"]

async def fetch_and_scrape(session: aiohttp.ClientSession, url: str) -> str:
    """
    Helper coroutine to asynchronously fetch and extract clean text from a single URL.
    
    Args:
        session (aiohttp.ClientSession): The active async HTTP session.
        url (str): The target webpage URL.
        
    Returns:
        str: The cleaned, scraped text, or an error/skip message.
    """
    # Fail-fast check to avoid downloading unsupported file types
    if any(ext in url.lower() for ext in RESTRICTED_EXTENSIONS):
        return f"[Skipped {url}: Restricted file type]"

    cached_content = get_cached_content(url)
    if cached_content:
        print(f"⚡ [Web Searcher] Cache hit for: {url}")
        return cached_content

    try:
        # 8-second timeout ensures a single slow website doesn't hang the entire LangGraph worker
        async with session.get(url, timeout=8) as response:
            if response.status != 200:
                return f"[Failed to fetch {url}: HTTP {response.status}]"
            
            html_content = await response.text()
            # We explicitly use 'html.parser' to avoid requiring the external 'lxml' C-dependency
            soup = BeautifulSoup(html_content, "html.parser") 
            
            # Extract only semantically relevant tags (headers, paragraphs, lists).
            # This strips away javascript, CSS, footers, and navbars automatically.
            tags_to_extract = ("h1", "h2", "h3", "p", "li")
            extracted_text = "\n".join(
                element.get_text(separator=" ", strip=True)
                for element in soup.find_all(tags_to_extract)
                if element.get_text(strip=True)
            )
            
            # Enforce the context window safety limit
            content = extracted_text[:CONTENT_LENGTH_LIMIT]
            formatted_content = f"\n--- SOURCE: {url} ---\n{content}\n"
            save_to_cache(url, formatted_content)
            return formatted_content
            
    except Exception as e:
        return f"[Error fetching {url}: {str(e)}]"

@tool
async def web_searcher(query: str) -> str:
    """
    Perform a Google search for a given query, concurrently scrape the top websites, 
    and return the aggregated text.
    
    This is an asynchronous LangChain @tool, designed to be invoked by the Action Nodes.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY not found in environment."

    print(f"🌐 [Web Searcher] Searching Google for: '{query}'")
    
    # 1. Search Google via Serper API (Lightweight JSON API for Google SERP)
    search_url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(search_url, headers=headers, json={"q": query}) as response:
            if response.status != 200:
                return f"Search API failed with status {response.status}"
            
            data = await response.json()
            
        # Extract the top 3 organic search links
        links = [item.get("link") for item in data.get("organic", [])[:3] if item.get("link")]
        
        if not links:
            return "No valid search results found."

        print(f"🕷️ [Web Searcher] Scraping top {len(links)} results...")
        
        # 2. Concurrency: Fire all scraping tasks simultaneously rather than sequentially.
        # This reduces the total I/O wait time from O(N) to O(1) relative to the slowest site.
        tasks = [fetch_and_scrape(session, url) for url in links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    # 3. Combine and return the text for the Action Node's LLM to read
    final_output = "".join([r for r in results if isinstance(r, str)])
    return final_output
