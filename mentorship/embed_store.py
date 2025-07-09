"""
Mentorship Chat Embed Store

This module provides functionality to ingest transcript files and query them
for relevant content using embeddings and similarity search.
"""

import os
import json
import time
from typing import List, Dict, Optional
import hashlib
from pathlib import Path

# Simple in-memory storage for demo purposes
# In production, you'd use a proper vector database like Pinecone, Weaviate, or Chroma
_transcript_store = {}
_embeddings_store = {}

def _create_simple_embedding(text: str) -> List[float]:
    """
    Create a simple embedding for demo purposes.
    In production, use a proper embedding model like OpenAI's text-embedding-ada-002
    or sentence-transformers.
    """
    # Simple hash-based embedding for demo
    # This is just a placeholder - replace with real embeddings
    hash_obj = hashlib.md5(text.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Convert hex to list of floats (simplified embedding)
    embedding = []
    for i in range(0, len(hash_hex), 2):
        if len(embedding) >= 384:  # Standard embedding size
            break
        hex_pair = hash_hex[i:i+2]
        embedding.append(float(int(hex_pair, 16)) / 255.0)
    
    # Pad or truncate to 384 dimensions
    while len(embedding) < 384:
        embedding.append(0.0)
    embedding = embedding[:384]
    
    return embedding

def _calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    """
    if not embedding1 or not embedding2:
        return 0.0
    
    # Dot product
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    
    # Magnitudes
    mag1 = sum(a * a for a in embedding1) ** 0.5
    mag2 = sum(b * b for b in embedding2) ** 0.5
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)

def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better retrieval.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundaries
        if end < len(text):
            # Look for sentence endings
            for i in range(end, max(start + chunk_size - 100, start), -1):
                if text[i] in '.!?':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def ingest_transcript(text: str, doc_id: str) -> bool:
    """
    Ingest a transcript text into the knowledge base.
    
    Args:
        text: The transcript text to ingest
        doc_id: Unique identifier for this document
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Store the original text
        _transcript_store[doc_id] = text
        
        # Create chunks
        chunks = _chunk_text(text)
        
        # Create embeddings for each chunk
        chunk_embeddings = {}
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            embedding = _create_simple_embedding(chunk)
            chunk_embeddings[chunk_id] = {
                "text": chunk,
                "embedding": embedding,
                "doc_id": doc_id,
                "chunk_index": i
            }
        
        # Store embeddings
        _embeddings_store[doc_id] = chunk_embeddings
        
        print(f"Ingested {len(chunks)} chunks from document {doc_id}")
        return True
        
    except Exception as e:
        print(f"Error ingesting transcript {doc_id}: {e}")
        return False

def query_store(query: str, k: int = 5) -> List[str]:
    """
    Query the knowledge base for relevant content.
    
    Args:
        query: The question or query text
        k: Number of top results to return
        
    Returns:
        List[str]: List of relevant text chunks
    """
    try:
        if not _embeddings_store:
            return []
        
        # Create embedding for the query
        query_embedding = _create_simple_embedding(query)
        
        # Calculate similarities with all chunks
        similarities = []
        for doc_id, chunks in _embeddings_store.items():
            for chunk_id, chunk_data in chunks.items():
                similarity = _calculate_similarity(query_embedding, chunk_data["embedding"])
                similarities.append({
                    "chunk_id": chunk_id,
                    "text": chunk_data["text"],
                    "similarity": similarity,
                    "doc_id": doc_id
                })
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top k results
        top_results = similarities[:k]
        
        # Return just the text content
        return [result["text"] for result in top_results if result["similarity"] > 0.1]
        
    except Exception as e:
        print(f"Error querying store: {e}")
        return []

def get_store_stats() -> Dict:
    """
    Get statistics about the knowledge base.
    """
    total_docs = len(_transcript_store)
    total_chunks = sum(len(chunks) for chunks in _embeddings_store.values())
    
    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "documents": list(_transcript_store.keys())
    }

def clear_store() -> bool:
    """
    Clear all stored data.
    """
    try:
        _transcript_store.clear()
        _embeddings_store.clear()
        return True
    except Exception as e:
        print(f"Error clearing store: {e}")
        return False

def delete_document(doc_id: str) -> bool:
    """
    Delete a specific document from the store.
    """
    try:
        if doc_id in _transcript_store:
            del _transcript_store[doc_id]
        
        if doc_id in _embeddings_store:
            del _embeddings_store[doc_id]
        
        return True
    except Exception as e:
        print(f"Error deleting document {doc_id}: {e}")
        return False 