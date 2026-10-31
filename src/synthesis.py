"""Synthesis Agent for combining SQL and ESG analysis results."""

from __future__ import annotations

from typing import Any

from src.state import GraphState


class SynthesisAgent:
    """Combine specialist-agent outputs into a structured report."""

    def run(self, state: GraphState) -> dict[str, Any]:
        sql_results = state.sql_execution_results
        esg_context = state.vector_retrieved_context
        source_metadata = state.source_metadata

        sections: list[str] = []

        # Executive summary
        sections.append(
            f"Analysis completed for: {state.user_query}"
        )

        # SQL findings
        if sql_results:
            successful_results = [
                result for result in sql_results
                if result.status == "success"
            ]

            if successful_results:
                sections.append("Portfolio / Database Findings:")

                for result in successful_results:
                    sections.append(
                        f"- {result.row_count} rows returned."
                    )

                    for row in result.rows[:10]:
                        sections.append(f"  {row}")
            else:
                sections.append(
                    "Portfolio / Database Findings: "
                    "No successful SQL analysis was available."
                )
        else:
            sections.append(
                "Portfolio / Database Findings: Not requested."
            )

        # ESG findings
        if esg_context:
            sections.append("ESG Compliance Findings:")

            for context in esg_context[:10]:
                sections.append(f"- {context}")
        else:
            sections.append(
                "ESG Compliance Findings: "
                "No ESG context was retrieved."
            )

        # Sources
        if source_metadata:
            sections.append("Sources:")

            seen: set[str] = set()

            for source in source_metadata:
                standard = source.standard

                if standard not in seen:
                    sections.append(
                        f"- {standard} "
                        f"(confidence: {source.score:.3f})"
                    )
                    seen.add(standard)

        # Overall confidence
        sections.append(
            f"Overall Confidence: {state.confidence:.3f}"
        )

        report_text = "\n".join(sections)

        report = {
            "query": state.user_query,
            "summary": sections[0],
            "report": report_text,
            "sql_findings": [
                result.model_dump()
                for result in sql_results
            ],
            "esg_findings": esg_context,
            "sources": [
                source.model_dump()
                for source in source_metadata
            ],
            "confidence": state.confidence,
        }

        return {
            "final_synthesis_report": report
        }


def synthesize(state: GraphState) -> dict[str, Any]:
    """Convenience wrapper for the synthesis agent."""

    return SynthesisAgent().run(state)