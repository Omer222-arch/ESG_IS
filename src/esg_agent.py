"""Evidence-first ESG compliance retrieval."""
from __future__ import annotations
from typing import Any
from src.vector_store import EsgVectorStore

def analyze_esg(query: str, store: EsgVectorStore) -> dict[str, Any]:
    docs = store.retrieve(query)
    return {"context": [item["text"] for item in docs], "sources": [{"source": item["metadata"]["source"], "standard": item["metadata"]["standard"], "document_id": item["id"], "score": item["score"]} for item in docs]}
