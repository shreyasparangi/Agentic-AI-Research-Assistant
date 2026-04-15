"""
Domain-Specific Web Crawler Utility
===================================
A specialized asynchronous breadth-first search (BFS) web crawler. 
Unlike the web_searcher which hits Google, this tool is designed to deeply inspect 
a specific entity's website (e.g., finding the 'About Us' or 'Documentation' pages).
It strictly bounds the crawl to the original domain to prevent runaway recursion.
"""

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from langchain_core.tools import tool

# Architecture Constraints:
# Limit extraction to keep the AI from getting overwhelmed (Context Window Protection)
CONTENT_LENGTH_LIMIT = 5000
# Keep the expo demo fast and snappy! Limits the BFS tree depth.
MAX_PAGES_TO_CRAWL = 3  

async def fetch_page_data(session: aiohttp.ClientSession, url: str) -> tuple[str, list[str]]:
    """
    Fetches raw HTML, extracts readable text, and parses internal domain links.
    
    Args:
        session (aiohttp.ClientSession): The active async HTTP session.
        url (str): The target webpage URL to scrape.
        
    Returns:
        tuple[str, list[str]]: The extracted text and a list of internal URLs found on the page.
    """
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                return "", []
            
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Extract clean, semantic text (strip out JS, CSS, and structural HTML)
            tags_to_extract = ("h1", "h2", "h3", "p", "li")
            text = "\n".join(
                el.get_text(separator=" ", strip=True)
                for el in soup.find_all(tags_to_extract)
                if el.get_text(strip=True)
            )

            # Extract internal links for the BFS Queue
            base_domain = urlparse(url).netloc
            links = []
            for a in soup.find_all('a', href=True):
                link = urljoin(url, a['href'])
                
                # Domain Restriction: Only keep links that belong to the exact same website.
                # Prevents the crawler from accidentally leaving the site (e.g., clicking a Twitter link).
                if urlparse(link).netloc == base_domain:
                    links.append(link.rstrip('/'))

            return text[:CONTENT_LENGTH_LIMIT], list(set(links))
            
    except Exception as e:
        print(f"⚠️ [Crawler Error] Failed on {url}: {str(e)}")
        return "", []

@tool
async def web_crawler(starting_url: str) -> str:
    """
    Use this tool to deeply crawl a specific website URL. 
    It executes a Breadth-First Search (BFS) to extract detailed text from the 
    target page and its immediate sub-pages.
    """
    # Normalize the URL protocol
    if not starting_url.startswith(('http://', 'https://')):
        starting_url = 'https://' + starting_url

    print(f"🕸️ [Web Crawler] Initiating targeted crawl on: {starting_url}")

    # Initialize data structures for the Breadth-First Search (BFS) algorithm
    visited = set()
    queue = [starting_url]
    all_text_results = []

    async with aiohttp.ClientSession() as session:
        # BFS Loop: Run until queue is empty or we hit our safety limit
        while queue and len(visited) < MAX_PAGES_TO_CRAWL:
            current_url = queue.pop(0) # FIFO Queue behavior
            
            if current_url in visited:
                continue

            visited.add(current_url)
            print(f"   -> Scraping: {current_url}")

            text, new_links = await fetch_page_data(session, current_url)

            if text:
                all_text_results.append(f"--- EXTRACTED FROM: {current_url} ---\n{text}\n")

            # Add discovered internal links to the queue for the next BFS level
            for link in new_links:
                if link not in visited and link not in queue:
                    queue.append(link)

    if not all_text_results:
        return f"Failed to extract readable text from {starting_url}"

    # Compile the results into a single string payload for the Action Node
    return "\n".join(all_text_results)