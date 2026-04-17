# 🤖 Agentic AI Research Assistant

An enterprise-grade, multi-agent AI system designed to autonomously perform deep research, scrape web data, query academic databases, and synthesize comprehensive Markdown reports. 

Built with **LangGraph**, **FastAPI**, and **Next.js**, this architecture prioritizes high-concurrency, context-window safety, and cost-efficient API routing.

## ✨ Core Features

* **Multi-Agent Orchestration (LangGraph):** Utilizes a cyclic graph architecture with a deterministic `Gap Analyzer` and `Tool Router` to autonomously decide when research is complete and when more data is needed.
* **Concurrent Tool Execution:** Fires multiple web scrapers and database queries simultaneously to reduce O(N) network latency to O(1).
* **Local Web Caching (SQLite):** Intercepts redundant HTTP requests to dramatically reduce API costs and bypass network latency during high-volume research loops.
* **Academic Literature Integration:** Features a specialized tool to query the **arXiv API**, pulling peer-reviewed computer science preprints directly into the context window.
* **Secure Local RAG (ChromaDB):** Safely parses and ingests user-uploaded PDFs into a local vector database for private document interrogation, protected against path-traversal vulnerabilities.
* **Expo-Safe Rate Limiting:** Exclusively powered by **Google Gemini 2.5 Flash** to leverage the 1 Million TPM (Tokens Per Minute) limit, guaranteeing crash-free presentations and massive context-window processing.

## 🏗️ System Architecture

1. **Next.js Frontend:** Provides a responsive dashboard for query input, PDF uploading, and rendering the final Markdown report.
2. **FastAPI Backend:** The asynchronous Python engine managing cross-origin requests and temporary file handling.
3. **Semantic Router:** A zero-temperature LLM node that maps identified knowledge gaps to specific functional APIs (`web_searcher`, `web_crawler`, `rag_retriever`, `arxiv_researcher`).
4. **Synthesizer:** The final node that aggregates raw HTML, XML, and PDF embeddings to draft a structured, deeply cited report.

## 🚀 Local Setup Instructions

Follow these steps to run the architecture locally on your machine.

### Prerequisites
* Python 3.10+
* Node.js 18+
* API Keys: Google Gemini & Serper.dev

### 1. Clone the Repository

```git clone https://github.com/shreyasparangi/Agentic-AI-Research-Assistant.git```
```cd Agentic-AI-Research-Assistant```
2. Backend Setup (FastAPI & LangGraph)
Open a terminal in the backend/ directory:
Bash
# Create a virtual environment
```python -m venv venv```
```source venv/bin/activate  # On Windows use: venv\Scripts\activate```

# Install dependencies
```pip install -r requirements.txt```

# Set up your environment variables
# Create a .env file and add:
# GEMINI_API_KEY="your_google_key"
# SERPER_API_KEY="your_serper_key"

# Start the Python server
```python -m uvicorn api:app --reload```
3. Frontend Setup (Next.js)
Open a second terminal in the frontend/ directory:
# Install Node modules
```npm install```
# Start the development server
```npm run dev```
4. Access the Application
Open your browser and navigate to http://localhost:3000. The frontend will automatically route requests to the backend running on port 8000.

👥 Contributors
Built by:
Shreyas Parangi, 2026
