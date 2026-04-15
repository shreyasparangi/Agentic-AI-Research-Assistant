"""
LLM Router Module
=================
This module acts as the central intelligence hub for the Agentic AI Research System.
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from the .env file
load_dotenv()

# --- 1. ENVIRONMENT SETUP ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper")

# Fail-fast validation
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY! Please ensure it is in your .env file.")

class LLMRouter:
    """
    A custom routing engine that assigns specialized LLMs to specific agentic tasks.
    """
    
    def __init__(self):
        self.search_provider = SEARCH_PROVIDER
        
        # 1. Fast Model: Gemini 2.5 Flash
        # Blisteringly fast. Ideal for gap analysis and scraping.
        self.fast_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0, 
            api_key=GEMINI_API_KEY
        )

        # 2. Main Model: Gemini 2.5 Pro
        # Handles the heavy lifting for reading massive text chunks and drafting the final report.
        self.main_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            temperature=0.2, 
            api_key=GEMINI_API_KEY
        )

        # 3. Reasoning Model: Gemini 2.5 Pro (Higher Temp)
        # Specifically designed for the Strategy Planner node to brainstorm creative outlines.
        self.reasoning_model = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            temperature=0.4, 
            api_key=GEMINI_API_KEY
        )

def create_default_config() -> LLMRouter:
    return LLMRouter()