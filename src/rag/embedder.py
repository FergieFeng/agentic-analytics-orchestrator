"""
Embedder: Convert text to vector embeddings using OpenAI.

Uses text-embedding-3-small for cost-effective, high-quality embeddings.
"""

from typing import List, Optional
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from src.config.settings import settings


# Embedding model configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # Default for text-embedding-3-small


@lru_cache(maxsize=1)
def get_embedder() -> OpenAIEmbeddings:
    """
    Get or create the OpenAI embeddings client.
    
    Returns:
        OpenAIEmbeddings instance configured with API key
    """
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=settings.openai_api_key
    )


def embed_text(text: str) -> List[float]:
    """
    Embed a single text string.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    embedder = get_embedder()
    return embedder.embed_query(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple text strings.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    embedder = get_embedder()
    return embedder.embed_documents(texts)


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings produced by this model."""
    return EMBEDDING_DIMENSIONS
