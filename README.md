# 🧠 Agentic AI Research System
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Next.js](https://img.shields.io/badge/Next.js-15.0-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-teal)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange)

An enterprise-grade, multi-agent artificial intelligence research architecture. This system autonomously crawls the web, parses data, cross-references local vector databases (RAG), and synthesizes fully cited academic reports using a Map-Reduce state machine.

## ⚡ Features
* **Dual Execution Modes:** * `Flash Agent`: High-speed iterative reasoning loop for rapid synthesis.
  * `Deep Parallel`: Asynchronous, concurrent multi-agent architecture (Map-Reduce) for massive, multi-faceted queries.
* **Concurrent Web Scraping:** Asynchronous HTTP sessions combined with Beautifulsoup HTML parsing.
* **Smart Context Management:** Auto-compresses 8,000+ character web scrapes to prevent LLM context window collapse.
* **Local RAG Integration:** Built-in ChromaDB pipeline for ingesting and querying private PDF knowledge bases.
* **SaaS UI:** Dark-mode Next.js dashboard with dynamic Markdown rendering and a localized 'Research Library'.

## 🏗️ Architecture Stack
* **Frontend:** Next.js, React, Tailwind CSS, Lucide Icons.
* **Backend:** Python, FastAPI, LangGraph, asyncio.
* **AI/LLM:** Google Gemini 2.5 Flash (Fast Tasks) & Gemini 2.5 Pro (Deep Reasoning).
* **Data Retrieval:** Serper API (Google Search), ChromaDB (Local Vector Store).

## 🚀 Quick Start
### 1. Environment Setup
Create a `.env` file in the `backend/` directory:
```text
GEMINI_API_KEY=your_gemini_key_here
SERPER_API_KEY=your_serper_key_here

2. Start the Backend
Open a terminal in the backend/ folder:

Bash
pip install -r requirements.txt
uvicorn api:app --reload
3. Start the Frontend
Open a split terminal in the frontend/ folder:

Bash
npm install
npm run dev
Navigate to http://localhost:3000 to launch the dashboard.

Built by,
Shreyas Parangi, 2026