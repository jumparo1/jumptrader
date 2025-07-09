"""
Mentorship Chat Module

This module provides functionality for creating a mentorship chat system
that can ingest transcript files and answer questions based on their content.
"""

from .embed_store import (
    ingest_transcript,
    query_store,
    get_store_stats,
    clear_store,
    delete_document
)

__all__ = [
    "ingest_transcript",
    "query_store", 
    "get_store_stats",
    "clear_store",
    "delete_document"
] 