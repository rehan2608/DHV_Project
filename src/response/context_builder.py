"""
Context builder module for NIRF Response Generation (Phase 6).
Compiles structured analytical execution results (Phase 4) and retrieved documentation
chunks (Phase 5) into a unified, controlled evidence context for Gemma.
"""

from typing import Dict, Any, List, Optional, Tuple
import json

from src.execution.result_schema import ExecutionResult, OperationResult
from src.rag.result_schema import RetrievalResult, RetrievedChunk
from src.response.exceptions import ContextBuildingError
from src.response.result_schema import ResponseType


class ContextBuilder:
    """
    Constructs strict, traceable evidence contexts from Phase 4 and Phase 5 outputs.
    Enforces clear separation between empirical analytical figures and qualitative documentation.
    """

    @classmethod
    def determine_response_type(
        cls,
        execution_result: Optional[ExecutionResult] = None,
        retrieval_result: Optional[RetrievalResult] = None,
    ) -> ResponseType:
        """
        Determines the classification of the query situation based on available evidence.
        """
        has_exec = execution_result is not None
        has_rag = retrieval_result is not None and retrieval_result.has_results()

        if has_exec and execution_result.status == "CLARIFICATION_REQUIRED":
            return "CLARIFICATION_REQUIRED"

        if has_exec and execution_result.status == "PARTIAL_SUCCESS":
            return "PARTIAL_EXECUTION"

        if has_exec and execution_result.status == "FAILED":
            if has_rag:
                return "DOCUMENTATION_ONLY"
            return "FAILED"

        has_valid_exec_data = False
        if has_exec and execution_result.operations:
            for op in execution_result.operations:
                if op.status == "SUCCESS" and op.data:
                    has_valid_exec_data = True
                    break

        if has_valid_exec_data and has_rag:
            return "COMBINED"
        elif has_valid_exec_data:
            return "ANALYTICAL_ONLY"
        elif has_rag:
            return "DOCUMENTATION_ONLY"
        else:
            return "NO_EVIDENCE"

    def build_context(
        self,
        original_question: str,
        execution_result: Optional[ExecutionResult] = None,
        retrieval_result: Optional[RetrievalResult] = None,
    ) -> Tuple[str, ResponseType, Dict[str, Any]]:
        """
        Builds the complete evidence string, determines response type,
        and compiles an evidence summary.
        """
        try:
            resp_type = self.determine_response_type(execution_result, retrieval_result)
            evidence_sections: List[str] = []
            evidence_summary: Dict[str, Any] = {
                "response_type": resp_type,
                "has_analytical_evidence": False,
                "has_documentation_evidence": False,
                "operations": [],
                "chunks": [],
                "warnings": [],
            }

            # 1. Analytical Evidence Block
            if execution_result is not None:
                analytical_block, op_summaries, warnings = self._format_analytical_evidence(execution_result)
                if analytical_block:
                    evidence_sections.append(analytical_block)
                    evidence_summary["has_analytical_evidence"] = True
                    evidence_summary["operations"] = op_summaries
                    evidence_summary["warnings"].extend(warnings)

            # 2. Documentation Evidence Block
            if retrieval_result is not None and retrieval_result.has_results():
                doc_block, chunk_summaries = self._format_documentation_evidence(retrieval_result)
                if doc_block:
                    evidence_sections.append(doc_block)
                    evidence_summary["has_documentation_evidence"] = True
                    evidence_summary["chunks"] = chunk_summaries

            # 3. Handle Empty Evidence
            if not evidence_sections:
                empty_block = (
                    "### EVIDENCE STATUS: NO GROUNDED EVIDENCE AVAILABLE\n"
                    "Neither empirical analytical records nor authoritative NIRF documentation "
                    "could be retrieved for this prompt. State clearly that sufficient evidence is unavailable."
                )
                evidence_sections.append(empty_block)

            # Assemble full context
            full_context = "\n\n" + ("\n" + "=" * 60 + "\n").join(evidence_sections) + "\n\n"
            return full_context, resp_type, evidence_summary

        except Exception as e:
            raise ContextBuildingError(f"Failed to assemble response evidence context: {e}")

    def _format_analytical_evidence(
        self,
        execution_result: ExecutionResult,
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """
        Formats OperationResults, data records, sample sizes, and warnings into Markdown text.
        """
        sections: List[str] = []
        op_summaries: List[Dict[str, Any]] = []
        all_warnings: List[str] = list(execution_result.warnings)

        sections.append("### SECTION 1: EMPIRICAL ANALYTICAL EVIDENCE (PHASE 4 EXECUTION)")
        sections.append(f"**Execution Status:** {execution_result.status}")
        sections.append(f"**Query Type:** {execution_result.query_type}")

        for op in execution_result.operations:
            op_summary = {
                "operation_id": op.operation_id,
                "function_name": op.function_name,
                "status": op.status,
            }
            op_summaries.append(op_summary)

            sections.append(f"\n#### Operation: `{op.operation_id}` ({op.function_name})")
            sections.append(f"- **Status:** {op.status}")

            if op.warnings:
                all_warnings.extend(op.warnings)
                sections.append(f"- **Operation Warnings:** {'; '.join(op.warnings)}")

            if op.error_message:
                sections.append(f"- **Error:** {op.error_message}")

            if op.data:
                formatted_data = self._format_operation_data(op.data)
                sections.append(formatted_data)

            if op.metadata:
                sections.append(f"- **Execution Metadata:** {json.dumps(op.metadata, default=str)}")

        # Add overall warnings / comparability notes
        if all_warnings:
            sections.append("\n#### MANDATORY DATA QUALITY & COMPARABILITY WARNINGS:")
            for w in set(all_warnings):
                sections.append(f"- ⚠️ {w}")

        return "\n".join(sections), op_summaries, list(set(all_warnings))

    def _format_operation_data(self, data: Dict[str, Any]) -> str:
        """
        Converts diverse analytical dictionary outputs into clear, readable text blocks.
        """
        lines: List[str] = ["- **Analytical Output Records:**"]

        # Check for list of records / rankings / trends
        for key in ("rankings", "trends", "data", "institutions", "outliers", "transitions", "gainers", "decliners", "top_institutions", "comparisons"):
            if key in data and isinstance(data[key], list):
                records = data[key]
                lines.append(f"  *Total items ({key}): {len(records)}*")
                for idx, row in enumerate(records[:15]):  # Show up to 15 records in prompt context
                    if isinstance(row, dict):
                        desc_parts = []
                        # Print UID and Name
                        name = row.get("institution_name", row.get("institute_name_std", row.get("institute_name", row.get("name", "Unknown"))))
                        uid = row.get("institution_uid", row.get("uid", ""))
                        desc_parts.append(f"[{uid}] {name}" if uid else str(name))

                        # Print ranks / movements
                        if "rank_diff" in row:
                            diff = row["rank_diff"]
                            start_r = row.get("rank_start", "N/A")
                            end_r = row.get("rank_end", "N/A")
                            direction = "improved" if diff > 0 else "declined" if diff < 0 else "unchanged"
                            desc_parts.append(f"Movement: {diff:+d} ranks ({direction}, Rank {start_r} -> {end_r})")
                        elif "rank_improvement" in row:
                            diff = row["rank_improvement"]
                            start_r = row.get("start_rank", row.get("rank_start", "N/A"))
                            end_r = row.get("end_rank", row.get("rank_end", "N/A"))
                            direction = "improved" if diff > 0 else "declined" if diff < 0 else "unchanged"
                            desc_parts.append(f"Movement: {diff:+d} ranks ({direction}, Rank {start_r} -> {end_r})")
                        elif "rank" in row:
                            desc_parts.append(f"Rank: {row['rank']}")

                        # Print scores / parameters
                        for metric in ("score", "tlr", "rpc", "go", "oi", "perception", "research_sfc", "research_qnr", "research_qlr"):
                            val = row.get(metric)
                            if val is None and "parameters" in row and isinstance(row["parameters"], dict):
                                val = row["parameters"].get(metric)
                            if val is not None:
                                desc_parts.append(f"{metric.upper()}: {val}")

                        # Print other relevant fields
                        for extra in ("state", "state_std", "year", "category"):
                            if extra in row and row[extra] is not None:
                                desc_parts.append(f"{extra}: {row[extra]}")

                        lines.append(f"  {idx + 1}. " + " | ".join(desc_parts))
                if len(records) > 15:
                    lines.append(f"  ... [and {len(records) - 15} additional records in dataset]")
                return "\n".join(lines)

        # Check for correlation result
        if "correlation" in data or "pearson" in data or "spearman" in data:
            lines.append("  *Correlation Statistics:*")
            for k, v in data.items():
                lines.append(f"  - {k}: {v}")
            return "\n".join(lines)

        # Check for distribution / summary stats
        if "summary" in data or "mean" in data or "median" in data:
            lines.append("  *Summary Statistics:*")
            for k, v in data.items():
                lines.append(f"  - {k}: {v}")
            return "\n".join(lines)

        # Fallback pretty JSON representation
        lines.append(f"```json\n{json.dumps(data, indent=2, default=str)}\n```")
        return "\n".join(lines)

    def _format_documentation_evidence(
        self,
        retrieval_result: RetrievalResult,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Formats retrieved documentation chunks into traceable evidence entries with citation tags.
        """
        sections: List[str] = []
        chunk_summaries: List[Dict[str, Any]] = []

        sections.append("### SECTION 2: RETRIEVED AUTHORITATIVE NIRF DOCUMENTATION (PHASE 5)")

        for idx, chunk in enumerate(retrieval_result.chunks, start=1):
            cite_tag = f"CITE-{idx:02d}"
            chunk_summary = {
                "cite_tag": cite_tag,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "section_title": chunk.section_title,
                "source_reference": chunk.source_reference,
                "score": chunk.score,
                "page_number": chunk.page_number,
                "file_path": chunk.file_path,
            }
            chunk_summaries.append(chunk_summary)

            sections.append(f"\n#### [{cite_tag}] Source: `{chunk.document_id}`")
            sections.append(f"- **Title / Section:** {chunk.section_title or 'N/A'}")
            sections.append(f"- **Authority / Reference:** {chunk.source_reference or 'Official NIRF Documentation'}")
            if chunk.page_number is not None:
                sections.append(f"- **Page:** {chunk.page_number}")
            sections.append(f"- **Relevance Score:** {chunk.score:.4f}")
            sections.append(f"- **Passage Text:**\n```\n{chunk.text.strip()}\n```")

        return "\n".join(sections), chunk_summaries
