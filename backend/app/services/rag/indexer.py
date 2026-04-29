"""
RAG indexer for the Dune rulebook.

Extracts text from the PDF, splits it into overlapping chunks, generates
Gemini text-embedding-004 vectors, and persists both to disk.

Run once to build (or rebuild) the index:
    python -m backend.app.services.rag.indexer

The data directory defaults to  backend/data/rag/
Override the PDF path via the DUNE_RULEBOOK_PATH environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import TypedDict

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).parent.parent.parent.parent   # …/backend
DATA_DIR      = _BACKEND_ROOT / "data" / "rag"
CHUNKS_FILE   = DATA_DIR / "chunks.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.npy"

DEFAULT_RULEBOOK_PATH = Path(
    os.getenv(
        "DUNE_RULEBOOK_PATH",
        r"C:\Users\anayb\Downloads\dune_Official-Rules (1).pdf",
    )
)

# Chunking parameters
CHUNK_SIZE    = 900    # characters (~225 tokens) — enough context, cheap to embed
CHUNK_OVERLAP = 150    # characters — catches rules that straddle boundaries


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Chunk(TypedDict):
    chunk_id: int
    text: str
    page: int


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Normalise extracted PDF text."""
    # Drop non-ASCII artefacts from Windows-1252 encoding
    text = text.encode("ascii", "ignore").decode("ascii")
    # Collapse runs of whitespace to single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, cleaned_text), …] for every non-empty page."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required: pip install pypdf") from exc

    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = _clean(page.extract_text() or "")
        if text:
            pages.append((i, text))
    return pages


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_page(page_num: int, text: str, next_id: int) -> list[Chunk]:
    """Split one page's text into overlapping chunks."""
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        # Try to end on a sentence boundary (period or newline) for cleaner chunks
        if end < len(text):
            last_break = max(
                text.rfind(".", start + CHUNK_SIZE // 2, end),
                text.rfind("\n", start + CHUNK_SIZE // 2, end),
            )
            if last_break > start + CHUNK_SIZE // 2:
                end = last_break + 1

        snippet = text[start:end].strip()
        if len(snippet) > 40:       # skip trivially short fragments
            chunks.append(Chunk(chunk_id=next_id, text=snippet, page=page_num))
            next_id += 1

        start = end - CHUNK_OVERLAP  # step forward with overlap

    return chunks


def build_chunks(pdf_path: Path) -> list[Chunk]:
    """Extract and chunk the entire rulebook."""
    pages = _extract_pages(pdf_path)
    chunks: list[Chunk] = []
    for page_num, text in pages:
        chunks.extend(_chunk_page(page_num, text, next_id=len(chunks)))
    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    """
    Call Gemini text-embedding-004 on up to 100 texts at a time.
    Returns a list of 768-dim float vectors.
    """
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai is required: pip install google-generativeai"
        ) from exc

    genai.configure(api_key=api_key)
    all_embeddings: list[list[float]] = []

    # API accepts batches of up to 100
    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=batch,
            task_type="retrieval_document",
        )
        embeddings = result["embedding"]
        # When content is a list, embedding is a list of lists
        if isinstance(embeddings[0], float):
            # Fallback: single string was returned as flat list
            embeddings = [embeddings]
        all_embeddings.extend(embeddings)

        # Respect free-tier rate limit: 1 500 req/day, 15 req/min
        if i + 100 < len(texts):
            time.sleep(0.5)

    return all_embeddings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def index_exists() -> bool:
    """True if a built index is present on disk."""
    return CHUNKS_FILE.exists() and EMBEDDINGS_FILE.exists()


def build_index(
    pdf_path: Path | None = None,
    api_key: str | None = None,
    force: bool = False,
) -> None:
    """
    Build (or rebuild) the rulebook index.

    Skips if the index already exists unless force=True.
    """
    if index_exists() and not force:
        logger.info("RAG index already exists at %s — skipping build.", DATA_DIR)
        return

    pdf_path = pdf_path or DEFAULT_RULEBOOK_PATH
    api_key  = api_key  or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    if not pdf_path.exists():
        raise FileNotFoundError(f"Rulebook not found: {pdf_path}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting and chunking %s …", pdf_path.name)
    chunks = build_chunks(pdf_path)
    logger.info("  → %d chunks created", len(chunks))

    logger.info("Generating embeddings via Gemini (this may take ~30 s) …")
    texts      = [c["text"] for c in chunks]
    embeddings = _embed_batch(texts, api_key)
    emb_array  = np.array(embeddings, dtype=np.float32)

    with CHUNKS_FILE.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)
    np.save(str(EMBEDDINGS_FILE), emb_array)

    logger.info(
        "Index saved to %s  (%d chunks, embedding shape %s)",
        DATA_DIR,
        len(chunks),
        emb_array.shape,
    )


def load_index() -> tuple[list[Chunk], np.ndarray]:
    """Load chunks and embeddings from disk. Raises if index is not built."""
    if not index_exists():
        raise RuntimeError(
            "RAG index not found. Run:  python -m backend.app.services.rag.indexer"
        )
    with CHUNKS_FILE.open(encoding="utf-8") as f:
        chunks: list[Chunk] = json.load(f)
    embeddings = np.load(str(EMBEDDINGS_FILE))
    return chunks, embeddings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

    force = "--force" in sys.argv
    build_index(force=force)
    print("Done! Index saved to", DATA_DIR)
