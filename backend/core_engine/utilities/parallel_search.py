"""Anonymous Parallel Search MCP over the official Streamable HTTP client."""

import asyncio
from uuid import uuid4

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Implementation

MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = (
    "Agentic-AI-Research-Assistant/1.0 "
    "(+https://github.com/shreyasparangi/Agentic-AI-Research-Assistant)"
)
TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 24000
# Reuse one identity across research tasks in this backend process.
SESSION_ID = uuid4().hex


async def _search(query: str) -> str:
    # No Authorization header or ambient Parallel credentials are used.
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS
    ) as client:
        async with streamable_http_client(MCP_URL, http_client=client) as (read, write, _):
            async with ClientSession(
                read, write,
                client_info=Implementation(name="Agentic-AI-Research-Assistant", version="1.0"),
            ) as session:
                await session.initialize()
                result = await session.call_tool("web_search", {
                    "objective": query,
                    "search_queries": [query],
                    "session_id": SESSION_ID,
                })
                text = "\n".join(
                    block.text for block in result.content if block.type == "text"
                ).strip()
                if result.isError:
                    return "Error: Parallel search failed. " + text[:1000]
                if not text:
                    return "Error: Parallel search returned no text results."
                # Keep source URLs and excerpts together for the action's citation filter.
                return text[:MAX_OUTPUT_CHARS]


async def parallel_search(query: str) -> str:
    """Return source-bearing search excerpts, with a deadline for the entire call."""
    try:
        return await asyncio.wait_for(_search(query), timeout=TIMEOUT_SECONDS)
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        return "Error: Parallel search timed out."
    except Exception:
        # SDK/transport exceptions may contain request internals. Never send them to a model.
        return "Error: Parallel search unavailable. Please retry later."
