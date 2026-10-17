"""Isolated caller tests: real MCP serialization, scripted summary model, no app server."""

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from langchain_core.runnables import RunnableLambda

from core_engine.utilities import parallel_search as parallel
from core_engine.utilities.search_config import get_search_provider
from core_engine.utilities.web_search import web_searcher

# Import the action without loading saved .env credentials or calling Gemini.
with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"}, clear=True):
    with patch("dotenv.load_dotenv"):
        from core_engine.nodes.actions import web_searcher as action
        from core_engine.nodes.tool_router import build_document_focus_plan


SOURCE = "https://example.org/research"
EXCERPTS = json.dumps({"results": [{
    "url": SOURCE, "title": "Error correction research",
    "excerpts": ["Researchers report a reproducible improvement."],
}]})
REAL_HTTP_CLIENT = httpx.AsyncClient


class SearchCallerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.requests = []
        self.tool_error = False
        self.result_text = EXCERPTS
        self.http_status = 200
        self.block_search = False
        self.entered_search = asyncio.Event()
        self.search_cancelled = asyncio.Event()
        self.prompts = []

        async def handle(request):
            payload = json.loads(request.content)
            self.requests.append((request, payload))
            method = payload["method"]
            if method == "notifications/initialized":
                return httpx.Response(202)
            if self.http_status != 200:
                return httpx.Response(self.http_status, text="Service unavailable")
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fixture", "version": "1"},
                }
            elif method == "tools/list":
                result = {"tools": [{"name": "web_search", "inputSchema": {
                    "type": "object", "properties": {},
                }}]}
            elif method == "tools/call":
                self.entered_search.set()
                if self.block_search:
                    try:
                        await asyncio.Event().wait()
                    finally:
                        self.search_cancelled.set()
                result = {"content": [{"type": "text", "text": self.result_text}],
                          "isError": self.tool_error}
            else:
                raise AssertionError(f"Unexpected MCP method: {method}")
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"],
                                              "result": result})

        self.transport = httpx.MockTransport(handle)

        def make_client(**kwargs):
            return REAL_HTTP_CLIENT(transport=self.transport, **kwargs)

        self.client_patch = patch.object(parallel.httpx, "AsyncClient", make_client)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)

        def summarize(prompt):
            self.prompts.append(prompt.to_string())
            return action.SearchSummaryOutput(
                summary="Researchers report a reproducible improvement [1].", sources=[SOURCE]
            )

        self.model = SimpleNamespace(
            with_structured_output=lambda schema: RunnableLambda(summarize)
        )
        self.router_patch = patch.object(
            action, "LLMRouter", return_value=SimpleNamespace(fast_model=self.model)
        )
        self.router = self.router_patch.start()
        self.addCleanup(self.router_patch.stop)

    async def test_fresh_no_key_action_consumes_mcp_results_and_urls(self):
        result = await action.execute_search_action("What improved?", "error correction research")
        self.assertIn("reproducible improvement [1]", result)
        self.assertIn(f"[1] {SOURCE}", result)
        self.assertIn(EXCERPTS, self.prompts[0])
        methods = [p["method"] for _, p in self.requests]
        self.assertIn("initialize", methods)
        self.assertIn("tools/call", methods)
        for request, payload in self.requests:
            self.assertEqual(str(request.url), "https://search.parallel.ai/mcp")
            self.assertEqual(request.headers["user-agent"], parallel.USER_AGENT)
            self.assertNotIn("authorization", request.headers)
            if payload["method"] == "tools/call":
                self.assertEqual(payload["params"]["name"], "web_search")
                args = payload["params"]["arguments"]
                self.assertEqual(args["objective"], "error correction research")
                self.assertEqual(args["search_queries"], ["error correction research"])
                self.assertEqual(args["session_id"], parallel.SESSION_ID)

    async def test_configured_serper_and_explicit_choice_are_preserved(self):
        with patch.dict(os.environ, {"SERPER_API_KEY": "saved-key"}):
            self.assertEqual(get_search_provider(), "serper")
            serper = AsyncMock(return_value=EXCERPTS)
            with patch("core_engine.utilities.google_search.web_searcher",
                       SimpleNamespace(ainvoke=serper)):
                result = await action.execute_search_action("gap", "query")
                serper.assert_awaited_once_with({"query": "query"})
                self.assertIn(SOURCE, result)
                self.assertEqual(self.requests, [])
            with patch.dict(os.environ, {"SEARCH_PROVIDER": " PARALLEL "}):
                result = await action.execute_search_action("gap", "query")
                self.assertIn(SOURCE, result)
                self.assertTrue(self.requests)

    async def test_explicit_serper_without_key_does_not_fall_back(self):
        with patch.dict(os.environ, {"SEARCH_PROVIDER": "serper"}):
            result = await action.execute_search_action("gap", "query")
        self.assertIn("SERPER_API_KEY", result)
        self.assertEqual(self.requests, [])
        self.router.assert_not_called()

    async def test_serper_api_failure_does_not_reach_model_or_parallel(self):
        serper = AsyncMock(return_value="Search API failed with status 403")
        with patch.dict(os.environ, {"SERPER_API_KEY": "saved-key"}):
            with patch("core_engine.utilities.google_search.web_searcher",
                       SimpleNamespace(ainvoke=serper)):
                result = await action.execute_search_action("gap", "query")
        self.assertIn("Search failed", result)
        self.assertEqual(self.requests, [])
        self.router.assert_not_called()

    async def test_disabled_and_invalid_selections_make_no_requests(self):
        for provider in ("none", "typo"):
            with self.subTest(provider=provider):
                with patch.dict(os.environ, {"SEARCH_PROVIDER": provider}):
                    result = await action.execute_search_action("gap", "query")
                self.assertIn("Search failed", result)
        self.assertEqual(self.requests, [])
        self.router.assert_not_called()

    async def test_ambient_parallel_credentials_are_not_sent(self):
        with patch.dict(os.environ, {"PARALLEL_API_KEY": "unused-secret", "SERPER_API_KEY": "  "}):
            self.assertEqual(get_search_provider(), "parallel")
            await web_searcher.ainvoke({"query": "query"})
        self.assertTrue(self.requests)
        for request, _ in self.requests:
            self.assertNotIn("authorization", request.headers)
            self.assertNotIn("unused-secret", str(request.headers))
            self.assertNotIn(b"unused-secret", request.content)

    async def test_mcp_error_and_empty_response_do_not_reach_model(self):
        for text, is_error in (("Quota exceeded", True), ("", False)):
            with self.subTest(text=text):
                self.result_text, self.tool_error = text, is_error
                result = await action.execute_search_action("gap", "query")
                self.assertIn("Search failed", result)
        self.router.assert_not_called()

    async def test_http_permission_and_server_failures_do_not_reach_model(self):
        for status in (401, 403, 500):
            with self.subTest(status=status):
                self.http_status = status
                result = await action.execute_search_action("gap", "query")
                self.assertIn("Search failed", result)
        self.router.assert_not_called()

    async def test_timeout_cancels_inflight_transport(self):
        self.block_search = True
        with patch.object(parallel, "TIMEOUT_SECONDS", 0.15):
            result = await action.execute_search_action("gap", "query")
        self.assertTrue(self.entered_search.is_set())
        self.assertTrue(self.search_cancelled.is_set())
        self.assertIn("timed out", result)
        self.router.assert_not_called()

    async def test_cancellation_propagates_and_closes_inflight_transport(self):
        self.block_search = True
        task = asyncio.create_task(action.execute_search_action("gap", "query"))
        await asyncio.wait_for(self.entered_search.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(self.search_cancelled.is_set())
        self.router.assert_not_called()

    async def test_document_focus_plan_never_asks_for_external_tools(self):
        plan = build_document_focus_plan("recent research", ["what does the PDF say?"])
        self.assertTrue(plan.tasks)
        self.assertEqual({task.tool_name for task in plan.tasks}, {"rag_retriever"})
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
