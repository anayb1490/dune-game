"""
RAG retriever — cosine similarity search over the rulebook chunk embeddings.

The index is loaded once at module level (lazy, on first call) and cached
in memory for the lifetime of the process.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TypedDict

import numpy as np

from .indexer import Chunk, load_index

logger = logging.getLogger(__name__)


class SearchResult(TypedDict):
    chunk_id: int
    text: str
    page: int
    score: float


# ---------------------------------------------------------------------------
# Index cache (loaded once per process)
# ---------------------------------------------------------------------------

_chunks:     list[Chunk]  | None = None
_embeddings: np.ndarray   | None = None


def _load() -> tuple[list[Chunk], np.ndarray]:
    global _chunks, _embeddings
    if _chunks is None:
        logger.info("Loading RAG index into memory …")
        _chunks, _embeddings = load_index()
        # Pre-normalise for fast cosine similarity (dot-product of unit vecs)
        norms = np.linalg.norm(_embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)   # avoid div-by-zero
        _embeddings = _embeddings / norms
        logger.info("RAG index loaded (%d chunks).", len(_chunks))
    return _chunks, _embeddings


# ---------------------------------------------------------------------------
# Embedding a query
# ---------------------------------------------------------------------------

def _embed_query(question: str) -> np.ndarray:
    """Return a normalised 768-dim embedding for the query."""
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=question,
        task_type="retrieval_query",   # different task type for queries
    )
    vec = np.array(result["embedding"], dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


# ---------------------------------------------------------------------------
# Public search API
# ---------------------------------------------------------------------------

def search(question: str, top_k: int = 4) -> list[SearchResult]:
    """
    Find the top_k rulebook chunks most relevant to the question.

    Returns results sorted by cosine similarity (highest first).
    """
    chunks, embeddings = _load()
    query_vec = _embed_query(question)        # shape (768,)

    # Cosine similarity = dot product of unit vectors
    scores: np.ndarray = embeddings @ query_vec   # shape (N,)

    # Grab top_k indices (unsorted then sort)
    top_indices = np.argpartition(scores, -top_k)[-top_k:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

    results: list[SearchResult] = []
    for idx in top_indices:
        c = chunks[idx]
        results.append(
            SearchResult(
                chunk_id=c["chunk_id"],
                text=c["text"],
                page=c["page"],
                score=float(scores[idx]),
            )
        )
    return results
