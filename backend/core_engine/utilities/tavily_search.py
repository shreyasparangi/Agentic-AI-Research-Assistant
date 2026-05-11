"""
Tavily Search Utility Module
=============================
This module handles real-time external data retrieval using the Tavily API.
It mirrors the output format of google_search.py (source-labelled text blocks)
so either provider can be used interchangeably by the web_searcher action node.
"""

import os
from tavily import TavilyClient
from langchain_core.tools import tool

# Hard limit on content per result to prevent overwhelming the LLM's context window.
CONTENT_LENGTH_LIMIT = 8000


@tool
async def tavily_searcher(query: str) -> str:
    """
    Perform a web search using the Tavily API and return aggregated text
    with source labels matching the format of the Serper-based web_searcher.

    This is an asynchronous LangChain @tool, designed to be invoked by the Action Nodes.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not found in environment."

    print(f"\U0001f310 [Web Searcher] Searching Tavily for: '{query}'")

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=3,
            search_depth="advanced",
            topic="general",
        )
    except Exception as e:
        return f"Search API failed: {str(e)}"

    results = response.get("results", [])
    if not results:
        return "No valid search results found."

    print(f"\U0001f577\ufe0f [Web Searcher] Processing top {len(results)} Tavily results...")

    final_output = ""
    for result in results:
        url = result.get("url", "unknown")
        content = result.get("content", "")[:CONTENT_LENGTH_LIMIT]
        final_output += f"\n--- SOURCE: {url} ---\n{content}\n"

    return final_output
