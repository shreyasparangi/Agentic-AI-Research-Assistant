"""
RAG Retriever Action Wrapper
============================
Acts as the synthesis layer between the local Vector Database and the LangGraph memory.
Vector databases (ChromaDB) return mathematically similar chunks of text, which are often 
disjointed or cut off mid-sentence. This wrapper uses an LLM to seamlessly stitch those 
raw chunks into a cohesive, logically sound answer.
"""

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from core_engine.llm_router import LLMRouter
from core_engine.utilities.vector_db import retrieve_context

# --- 1. PYDANTIC SCHEMA ---
class RagSummaryOutput(BaseModel):
    """Structured output for the local RAG action node. Demands verbatim quotes for data lineage."""
    summary: str = Field(description="A detailed summary answering the knowledge gap using ONLY the provided local database chunks.")
    quotes: list[str] = Field(description="Exact verbatim quotes from the text that support your summary.")


# --- 2. THE SYSTEM PROMPT ---
# We enforce "Strict Database Isolation" here. The AI is forbidden from using its pre-trained 
# weights to answer the question; it must act only on the injected local RAG chunks.
RAG_ACTION_PROMPT = """
You are an AI Research Analyst parsing internal academic documents and literature.
Your job is to read raw text chunks retrieved from a local Vector Database and extract the exact information needed to fill a knowledge gap.

KNOWLEDGE GAP TO FILL: {gap}

RAW DATABASE CHUNKS:
{raw_data}

GUIDELINES:
1. Write a detailed summary that specifically answers the knowledge gap.
2. You MUST rely strictly on the 'RAW DATABASE CHUNKS' provided. Do NOT use outside web knowledge.
3. If the provided chunks do not contain the answer, explicitly state "The local database does not contain information to answer this gap."
4. Include inline citations using brackets [Local DB] next to the facts you extract.
"""


# --- 3. THE ACTION NODE WRAPPER ---
async def execute_rag_action(gap: str, query: str) -> str:
    """
    Executes the ChromaDB similarity search, then uses the Fast LLM to summarize 
    the disjointed chunks into a cohesive answer.
    """
    print(f"🗄️ [Action: RAG] Querying local vector database for: '{query}'")
    
    # 1. Fire the raw utility tool (The "Hands")
    raw_text = retrieve_context(query)
    
    if not raw_text or len(raw_text.strip()) < 10:
        return f"No relevant information found in the local database for '{query}'."

    print(f"🧠 [Action: RAG] Reading {len(raw_text)} characters of retrieved chunks...")

    # 2. Initialize the Fast Model (The "Filter")
    router = LLMRouter()
    llm = router.fast_model
    
    structured_llm = llm.with_structured_output(RagSummaryOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", RAG_ACTION_PROMPT),
        ("human", "Summarize the vector database chunks to fill the knowledge gap.")
    ])
    
    chain = prompt | structured_llm
    
    # 3. Compress the data
    try:
        result: RagSummaryOutput = await chain.ainvoke({"gap": gap, "raw_data": raw_text})
        
        # 4. Format beautifully for the LangGraph state memory
        formatted_output = f"### Internal Database Summary: '{query}'\n{result.summary}\n\n**Supporting Quotes:**\n"
        for i, quote in enumerate(result.quotes, 1):
            formatted_output += f"- \"{quote}\"\n"
            
        print(f"✅ [Action: RAG] Successfully synthesized local chunks.")
        return formatted_output

    except Exception as e:
        print(f"⚠️ [Action: RAG] LLM parsing failed: {str(e)}")
        return f"Chunks retrieved but summarization failed.\n\nRaw Chunk snippet: {raw_text[:500]}"