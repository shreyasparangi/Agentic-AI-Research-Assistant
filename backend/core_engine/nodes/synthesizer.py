"""
Synthesizer Node
================
Handles the 'Reduce' phase of the architecture.
Once the QA node (Gap Analyzer) declares research complete, or the safety loop limit is reached,
this node consumes the raw, aggregated tool findings and drafts a final, academic-grade Markdown section.
"""

from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core_engine.llm_router import LLMRouter

# --- 1. THE SYSTEM PROMPT ---
SYNTHESIZER_PROMPT = """
You are a Senior Academic Researcher and Technical Writer. Today's date is {date}.
Your objective is to write a highly detailed, comprehensive section of a final report based on the provided research findings.

ORIGINAL OVERALL QUERY: {query}
SPECIFIC SECTION TITLE: {section_title}
SPECIFIC SECTION QUESTION: {section_question}

RESEARCH FINDINGS TO SYNTHESIZE:
{findings}

GUIDELINES:
1. Write in a professional, academic markdown format. Do NOT use markdown code blocks (like ```markdown), just return the raw text.
2. Answer the specific section question directly using ONLY the provided research findings.
3. Do NOT hallucinate or add outside information that is not supported by the findings.
4. Include references to the source URLs or Document Names for all data. Use numbered brackets [1], [2], etc., immediately after the claim.
5. Provide a "References" section at the very bottom of your output listing the sources you used.
"""

# --- 2. THE LANGGRAPH NODE ---
def synthesizer_node(state: dict):
    """Consumes the contextual history and generates formatted Markdown."""
    user_query = state.get("query", "Unknown query")
    section_title = state.get("current_section_title", "General Research")
    section_question = state.get("current_section", "Summarize findings")
    findings = state.get("research_history", "No findings provided.")
    
    print(f"✍️ [Synthesizer] Writing report section: '{section_title}'...")
    
    # We use the Main Model here because processing thousands of characters of 
    # aggregated web/RAG data requires a highly robust context window and strong linguistic synthesis.
    router = LLMRouter()
    llm = router.main_model
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYNTHESIZER_PROMPT),
        ("human", "Synthesize the findings and write the final section.")
    ])
    
    # Note: We pivot away from structured JSON here. We use StrOutputParser() 
    # because we want continuous, unstructured raw Markdown text as the final artifact.
    chain = prompt | llm | StrOutputParser()
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    final_draft = chain.invoke({
        "date": current_date, 
        "query": user_query,
        "section_title": section_title,
        "section_question": section_question,
        "findings": findings
    })
    
    print(f"✅ [Synthesizer] Section '{section_title}' successfully written!")
    
    completed_sections = state.get("completed_sections", [])
    completed_sections.append(final_draft)
    
    return {
        "completed_sections": completed_sections,
        # Purge the ephemeral research history to prevent memory leaks across loops
        "research_history": "" 
    }