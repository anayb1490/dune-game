"""
POST /api/rules/ask — RAG-powered Dune rules explainer.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/rules", tags=["rules"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=400)


class Source(BaseModel):
    page: int
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/ask", response_model=AskResponse)
async def ask_rules(request: AskRequest) -> AskResponse:
    """
    Retrieve relevant rulebook passages and generate an answer via Gemini.

    Returns the answer and the source page(s) it was drawn from.
    """
    from ...services.rag.chat import ask
    from ...services.rag.indexer import index_exists

    if not index_exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Rules index is not built yet. "
                "Run:  python -m backend.app.services.rag.indexer"
            ),
        )

    try:
        result = ask(request.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")

    return AskResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
    )
