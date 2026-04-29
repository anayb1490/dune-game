"""
RAG chat — retrieves relevant rulebook chunks and generates an answer
using Gemini 1.5 Flash.
"""

from __future__ import annotations

import os
from typing import TypedDict

from .retriever import SearchResult, search


# ---------------------------------------------------------------------------
# Response type
# ---------------------------------------------------------------------------

class RulesAnswer(TypedDict):
    answer: str
    sources: list[dict]   # [{page, excerpt}]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM = """You are a concise, accurate rules expert for the Dune board game (Gale Force Nine edition).

Your job: answer the player's question using ONLY the rulebook excerpts provided below.

Rules for your answers:
- Be direct and specific. Players are mid-game and need quick clarity.
- If multiple excerpts are relevant, synthesise them into one clear answer.
- If the excerpts do not fully address the question, say so honestly — do NOT invent rules.
- Use plain language. Avoid restating the question.
- Cite the rulebook page number(s) when they add useful context, e.g. "(p. 9)".
- Keep answers under 150 words unless the rule genuinely requires more detail.
"""


def _build_prompt(question: str, chunks: list[SearchResult]) -> str:
    excerpts = "\n\n".join(
        f"[Page {c['page']}]\n{c['text']}"
        for c in chunks
    )
    return (
        f"Rulebook excerpts:\n\n{excerpts}\n\n"
        f"---\n\n"
        f"Player's question: {question}"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def ask(question: str, top_k: int = 4) -> RulesAnswer:
    """
    Full RAG pipeline: retrieve relevant chunks → generate answer.

    Raises RuntimeError if the index is not built or GEMINI_API_KEY is unset.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    genai.configure(api_key=api_key)

    # 1. Retrieve
    chunks = search(question, top_k=top_k)

    # 2. Build prompt
    prompt = _build_prompt(question, chunks)

    # 3. Generate
    model    = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=_SYSTEM,
    )
    response = model.generate_content(prompt)
    answer   = response.text.strip()

    # 4. Format sources (deduplicated by page, highest-scoring chunk per page)
    seen_pages: set[int] = set()
    sources: list[dict]  = []
    for c in chunks:
        if c["page"] not in seen_pages:
            seen_pages.add(c["page"])
            # Show a short excerpt (first 120 chars) so the player can locate it
            sources.append({
                "page": c["page"],
                "excerpt": c["text"][:120].rstrip() + "…",
            })

    return RulesAnswer(answer=answer, sources=sources)
