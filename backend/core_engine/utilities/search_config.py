"""Shared web-search selection without changing configured Serper installations."""

import os


def get_search_provider() -> str:
    """An explicit choice wins; otherwise keep configured Serper or use Parallel."""
    explicit = os.getenv("SEARCH_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    return "serper" if os.getenv("SERPER_API_KEY", "").strip() else "parallel"
