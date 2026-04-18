"""
LLM Router Module
=================
Centralized provider for LLM instantiation. 
Configured for restricted Enterprise/Educational API keys.
"""

import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# Load environment variables
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper")

if not ANTHROPIC_API_KEY:
    raise ValueError("Missing ANTHROPIC_API_KEY! Please ensure it is in your .env file.")

class LLMRouter:
    """
    A custom routing engine that assigns Claude models to specific agentic tasks.
    """
    
    def __init__(self):
        self.search_provider = SEARCH_PROVIDER
        
        # BRUTE FORCE BYPASS: 
        # Educational API keys usually only whitelist this specific Sonnet build.
        # We assign it to every single task to guarantee no 404 errors.
        safe_model = "claude-3-5-sonnet-20240620"
        
        # 1. Fast Model
        self.fast_model = ChatAnthropic(
            model=safe_model, 
            temperature=0,
            api_key=ANTHROPIC_API_KEY
        )

        # 2. Main Model
        self.main_model = ChatAnthropic(
            model=safe_model,
            temperature=0.2, 
            api_key=ANTHROPIC_API_KEY
        )

        # 3. Reasoning Model
        self.reasoning_model = ChatAnthropic(
            model=safe_model, 
            temperature=0,
            api_key=ANTHROPIC_API_KEY
        )
        
        # 4. Semantic Routing Model
        self.routing_model = ChatAnthropic(
            model=safe_model,
            temperature=0.0, 
            api_key=ANTHROPIC_API_KEY
        )

def create_default_config() -> LLMRouter:
    return LLMRouter()