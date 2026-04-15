"""
Vector Database & RAG Utility Module
====================================
Handles the Retrieval-Augmented Generation (RAG) pipeline. 
This module ingests local documents, performs semantic chunking, generates mathematical 
embeddings via Google's Gemini models, and manages storage/retrieval using a local 
ChromaDB vector database.
"""

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# Initialize the embedding model. This converts raw text into mathematical vectors.
# Initialize the embedding model. This converts raw text into mathematical vectors.
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Define the local persistence directory for the SQLite-based Chroma database
CHROMA_PATH = "./chroma_db"

def ingest_pdf_to_chroma(pdf_path: str):
    """
    Loads a PDF document, chunks it to preserve semantic meaning, 
    and saves the embeddings to the local vector database.
    
    Args:
        pdf_path (str): The file path to the target PDF.
        
    Returns:
        bool: True on successful ingestion.
    """
    print(f"📄 [Vector DB] Ingesting {pdf_path}...")
    
    # 1. Extract raw text from the PDF
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # 2. Semantic Chunking Strategy
    # We use RecursiveCharacterTextSplitter to split text intelligently (by paragraphs, then sentences).
    # chunk_overlap=200 ensures that if a sentence spans across a chunk boundary, 
    # the context is not lost in the mathematical embedding.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ [Vector DB] Split PDF into {len(chunks)} chunks.")
    
    # 3. Embed and Persist
    db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=CHROMA_PATH
    )
    print("💾 [Vector DB] Chunks successfully embedded and saved to ChromaDB!")
    return True

def retrieve_context(query: str, k: int = 3):
    """
    Performs a mathematical similarity search against the local Vector DB.
    
    Args:
        query (str): The user's question or search term.
        k (int): The number of closest vector chunks to return. Defaults to 3.
        
    Returns:
        str: The aggregated text chunks relevant to the query.
    """
    # Connect to the existing local database
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    
    # Execute a K-Nearest Neighbors (KNN) style similarity search in the vector space
    results = db.similarity_search(query, k=k)
    
    # Combine the retrieved chunks into a single string context for the LLM prompt
    context = "\n\n".join([doc.page_content for doc in results])
    return context