"""
LLM Router Module
=================
Enterprise Production Mode: Configured for Gemini 2.5 Flash (Paid Tier).
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper")

# Fail-fast validation
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY! Please ensure it is in your .env file.")

class LLMRouter:
    """
    A custom routing engine that assigns specialized Gemini 2.5 models to specific agentic tasks.
    """
    
    def __init__(self):
        self.search_provider = SEARCH_PROVIDER
        
        # PRODUCTION ALIAS:
        # Utilizing the blistering speed of Gemini 2.5 Flash across all nodes 
        # now that the paid-tier rate limits are lifted.
        production_model = "gemini-2.5-flash"
        
        # 1. Fast Model: Low latency for Gap Analysis and text scraping
        self.fast_model = ChatGoogleGenerativeAI(
            model=production_model, 
            temperature=0,
            api_key=GEMINI_API_KEY
        )

        # 2. Main Model: Slight temperature variance for creative Synthesizing
        self.main_model = ChatGoogleGenerativeAI(
            model=production_model,
            temperature=0.2, 
            api_key=GEMINI_API_KEY
        )

        # 3. Reasoning Model: Deep reasoning for Strategy Planning
        self.reasoning_model = ChatGoogleGenerativeAI(
            model=production_model, 
            temperature=0,
            api_key=GEMINI_API_KEY
        )
        
        # 4. Semantic Routing Model: Zero temperature to guarantee deterministic JSON
        self.routing_model = ChatGoogleGenerativeAI(
            model=production_model,
            temperature=0.0, 
            api_key=GEMINI_API_KEY
        )

def create_default_config() -> LLMRouter:
    return LLMRouter()