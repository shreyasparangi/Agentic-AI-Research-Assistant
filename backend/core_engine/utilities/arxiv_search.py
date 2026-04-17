"""
arXiv Search Utility
====================
Queries the official arXiv API and returns a compact summary of the top papers.
"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from langchain_core.tools import tool

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}


def _clean_text(value: str | None) -> str:
    """Normalize arXiv XML text fields for readable agent output."""
    if not value:
        return ""
    return " ".join(value.split())


@tool
def arxiv_researcher(query: str) -> str:
    """
    Search arXiv for academic papers related to a query and return the top 3 results.
    """
    safe_query = urllib.parse.quote_plus(query.strip())
    if not safe_query:
        return "arXiv search failed: empty query."

    request_url = f"{ARXIV_API_URL}?search_query=all:{safe_query}&start=0&max_results=3"
    request = urllib.request.Request(
        request_url,
        headers={"User-Agent": "AgenticAIResearchAssistant/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            xml_data = response.read()
    except Exception as e:
        return f"arXiv search failed for '{query}': {str(e)}"

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        return f"arXiv search failed for '{query}': invalid XML response ({str(e)})"

    entries = root.findall("atom:entry", ATOM_NAMESPACE)
    if not entries:
        return f"No arXiv papers found for '{query}'."

    formatted_results = [f"### arXiv Research Results for '{query}'"]

    for index, entry in enumerate(entries[:3], 1):
        title = _clean_text(entry.findtext("atom:title", namespaces=ATOM_NAMESPACE))
        published = _clean_text(entry.findtext("atom:published", namespaces=ATOM_NAMESPACE))
        summary = _clean_text(entry.findtext("atom:summary", namespaces=ATOM_NAMESPACE))
        paper_url = _clean_text(entry.findtext("atom:id", namespaces=ATOM_NAMESPACE))

        authors = [
            _clean_text(author.findtext("atom:name", namespaces=ATOM_NAMESPACE))
            for author in entry.findall("atom:author", ATOM_NAMESPACE)
        ]
        author_text = ", ".join(author for author in authors if author) or "Unknown author"

        formatted_results.append(
            "\n".join(
                [
                    f"{index}. {title or 'Untitled paper'}",
                    f"Published: {published or 'Unknown date'}",
                    f"Author: {author_text}",
                    f"Summary: {summary or 'No abstract available.'}",
                    f"URL: {paper_url or 'No URL available.'}",
                ]
            )
        )

    return "\n\n".join(formatted_results)
