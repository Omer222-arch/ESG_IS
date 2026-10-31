
"""ESG compliance retrieval agent."""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.state import GraphState, SourceMetadata
from src.vector_store import EsgVectorStore


class EsgComplianceAgent:
    """Retrieves relevant ESG compliance context from Chroma."""

    def __init__(
        self,
        vector_store: Any | None = None,
        top_k: int = 4,
        confidence_threshold: float | None = None,
    ) -> None:
        self.vector_store = vector_store or EsgVectorStore(
            persist_directory=settings.chroma_path,
            collection_name=settings.chroma_collection,
            config=settings,
        )
        self.top_k = top_k
        self.confidence_threshold = (
            settings.human_review_threshold
            if confidence_threshold is None
            else confidence_threshold
        )

        # Ensure the local ESG knowledge base exists.
        if vector_store is None:
            self.vector_store.initialize()
            self.vector_store.seed()

    def analyze(
        self,
        query: str,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve ESG context for a natural-language query."""

        if not query or not query.strip():
            return {
                "query": query,
                "context": [],
                "sources": [],
                "standards_found": [],
                "confidence": 0.0,
                "status": "empty",
            }

        results = self.vector_store.retrieve(
            query=query,
            limit=top_k or self.top_k,
        )

        contexts: list[str] = []
        sources: list[SourceMetadata] = []

        for result in results:
            metadata = result.get("metadata") or {}

            document_id = str(
                result.get("id", "unknown")
            )

            text = str(
                result.get("text", "")
            )

            score = float(
                result.get("score", 0.0)
            )

            source = str(
                metadata.get("source", "Unknown")
            )

            standard = str(
                metadata.get("standard", source)
            )

            if text:
                contexts.append(text)

            sources.append(
                SourceMetadata(
                    source=source,
                    standard=standard,
                    document_id=document_id,
                    score=max(0.0, min(1.0, score)),
                )
            )

        confidence = max(
            (source.score for source in sources),
            default=0.0,
        )

        standards_found = list(
            dict.fromkeys(
                source.standard
                for source in sources
                if source.standard
            )
        )

        return {
            "query": query,
            "context": contexts,
            "sources": sources,
            "standards_found": standards_found,
            "confidence": confidence,
            "status": (
                "success"
                if contexts and confidence >= self.confidence_threshold
                else "low_confidence"
            ),
        }

    def run(
        self,
        input_data: GraphState | str,
    ) -> dict[str, Any]:
        """
        Execute ESG analysis.

        Supports both:
            run(GraphState)
        and:
            run("ESG query")

        This makes the agent compatible with the
        current LangGraph implementation.
        """

        if isinstance(input_data, GraphState):
            query = (
                input_data.esg_query
                or input_data.user_query
            )
        elif isinstance(input_data, str):
            query = input_data
        else:
            raise TypeError(
                "EsgComplianceAgent.run() expects "
                "GraphState or str."
            )

        result = self.analyze(query)

        return {
            "esg_query": query,
            "vector_retrieved_context": result["context"],
            "retrieved_context": result["context"],
            "source_metadata": [
                source.model_dump()
                if isinstance(source, SourceMetadata)
                else source
                for source in result["sources"]
            ],
            "confidence": result["confidence"],
            "status": result["status"],
            "standards_found": result["standards_found"],
            "agent_messages": [
                {
                    "agent": "esg_compliance",
                    "message": "ESG compliance analysis completed.",
                    "level": "info",
                }
            ],
        }


def run_esg_compliance(
    state: GraphState,
) -> dict[str, Any]:
    """LangGraph node helper."""

    agent = EsgComplianceAgent()

    return agent.run(state)
