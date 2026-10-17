"""Provider selection for the maintained research action's web-search tool."""

from langchain_core.tools import tool

from core_engine.utilities.search_config import get_search_provider


@tool
async def web_searcher(query: str) -> str:
    """Search the web with the configured provider and return source-bearing text."""
    provider = get_search_provider()
    if provider == "none":
        return "Error: Web search is disabled (SEARCH_PROVIDER=none)."
    if provider == "parallel":
        from core_engine.utilities.parallel_search import parallel_search

        return await parallel_search(query)
    if provider == "serper":
        from core_engine.utilities.google_search import web_searcher as serper_searcher

        # An explicit provider failure never selects another provider.
        return await serper_searcher.ainvoke({"query": query})
    return "Error: Invalid SEARCH_PROVIDER. Choose parallel, serper, or none."
