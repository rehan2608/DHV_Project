"""
Response generator coordinator module for NIRF Assistant (Phase 6 & 6.1).
Orchestrates context compilation, LLM generation, structured claim extraction,
independent prose auditing, deterministic verification, citation auditing, and failure/regeneration loops.
"""

import json
import time
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple

from src.execution.result_schema import ExecutionResult
from src.llm.gemma_client import GemmaClient, get_gemma_client
from src.rag.result_schema import RetrievalResult
from src.response.citation_validator import CitationValidator
from src.response.claim_auditor import IndependentClaimAuditor
from src.response.claim_extractor import ClaimExtractor
from src.response.context_builder import ContextBuilder
from src.response.exceptions import GenerationError
from src.response.prompts import (
    RESPONSE_SYSTEM_PROMPT,
    build_generation_prompt,
    build_regeneration_prompt,
)
from src.response.result_schema import (
    GeneratedResponse,
    GenerationMetadata,
    ResponseStatus,
    ResponseType,
    VerificationSummary,
)
from src.response.verifier import NumericalClaimVerifier


class ResponseGenerator:
    """
    Main interface for generating verified natural-language responses.
    Integrates Gemma with deterministic verification and strict warning preservation.
    """

    def __init__(
        self,
        gemma_client: Optional[GemmaClient] = None,
        max_regeneration_attempts: int = 1,
        float_tolerance: float = 0.05,
    ):
        self._gemma_client = gemma_client
        self.max_regeneration_attempts = max_regeneration_attempts
        self.context_builder = ContextBuilder()
        self.claim_extractor = ClaimExtractor()
        self.auditor = IndependentClaimAuditor(float_tolerance=float_tolerance)
        self.verifier = NumericalClaimVerifier(float_tolerance=float_tolerance)
        self.citation_validator = CitationValidator()

    def _get_llm(self) -> GemmaClient:
        """Lazy loads the Gemma client singleton if not injected."""
        if self._gemma_client is None:
            self._gemma_client = get_gemma_client()
        return self._gemma_client

    def _get_model_name(self) -> str:
        """Safely returns the string model name even if a mock was passed."""
        llm = self._get_llm()
        m = getattr(llm, "model", "gemma4:31b-cloud")
        if isinstance(m, str):
            return m
        return "gemma4:31b-cloud"

    def _parse_llm_output(self, raw_output: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parses LLM output, extracting prose answer and structured claims.
        Handles valid JSON, markdown fenced JSON (```json ... ```), and raw text fallback.
        """
        if not raw_output or not raw_output.strip():
            return "", []

        text = raw_output.strip()

        # Try extracting JSON from markdown code fence
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        json_candidate = fence_match.group(1).strip() if fence_match else text

        try:
            parsed = json.loads(json_candidate)
            if isinstance(parsed, dict):
                answer = parsed.get("answer", "")
                claims = parsed.get("claims", [])
                if isinstance(answer, str) and answer.strip():
                    return answer.strip(), claims if isinstance(claims, list) else []
        except Exception:
            pass

        # Also attempt looking for the outermost { ... }
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                candidate = text[start_idx : end_idx + 1]
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and "answer" in parsed:
                    answer = parsed.get("answer", "")
                    claims = parsed.get("claims", [])
                    if isinstance(answer, str) and answer.strip():
                        return answer.strip(), claims if isinstance(claims, list) else []
            except Exception:
                pass

        # Fallback: raw text as answer, empty claims (auditor will extract claims from prose)
        return text, []

    def generate_response(
        self,
        original_question: str,
        query_id: Optional[str] = None,
        execution_result: Optional[ExecutionResult] = None,
        retrieval_result: Optional[RetrievalResult] = None,
        custom_instructions: Optional[str] = None,
    ) -> GeneratedResponse:
        """
        Coordinates full response generation and verification lifecycle.
        """
        start_total = time.perf_counter()
        qid = query_id or f"q_{uuid.uuid4().hex[:6]}"

        # 1. Build controlled evidence context
        evidence_context, response_type, evidence_summary = self.context_builder.build_context(
            original_question=original_question,
            execution_result=execution_result,
            retrieval_result=retrieval_result,
        )

        # 2. Check for immediate clarification or failed execution
        if response_type == "CLARIFICATION_REQUIRED":
            return self._build_clarification_response(
                qid, original_question, execution_result, evidence_summary, start_total
            )

        if response_type == "FAILED" and (retrieval_result is None or not retrieval_result.has_results()):
            return self._build_failed_execution_response(
                qid, original_question, execution_result, evidence_summary, start_total
            )

        # 3. Initial text generation with Gemma
        prompt = build_generation_prompt(
            user_question=original_question,
            evidence_context=evidence_context,
            response_type=response_type,
            custom_instructions=custom_instructions,
        )

        t_gen_start = time.perf_counter()
        llm = self._get_llm()
        try:
            raw_output = llm.generate(
                prompt=prompt,
                system_prompt=RESPONSE_SYSTEM_PROMPT,
                temperature=0.0,
            )
        except Exception as e:
            raise GenerationError(f"Gemma response generation failed: {e}")
        t_gen_duration = time.perf_counter() - t_gen_start

        draft_answer, raw_claims = self._parse_llm_output(raw_output)

        # 4. Independent prose audit & claim reconciliation
        t_ver_start = time.perf_counter()
        claims, audit_meta = self.auditor.audit_and_reconcile(
            prose_answer=draft_answer,
            structured_claims=raw_claims,
            execution_result=execution_result,
        )

        # 5. Deterministic verification
        claims, verification_summary = self.verifier.verify_claims(claims, execution_result, retrieval_result=retrieval_result)
        verification_summary.extraction_coverage = audit_meta.get("extraction_coverage", 1.0)
        verification_summary.text_audited_claims_count = audit_meta.get("text_audited_facts_count", 0)
        verification_summary.omitted_from_structured_count = audit_meta.get("omitted_from_structured_count", 0)
        verification_summary.structured_claims_count = audit_meta.get("structured_claims_count", 0)
        t_ver_duration = time.perf_counter() - t_ver_start

        # 6. Validate citations
        citations = self.citation_validator.validate_and_extract_citations(draft_answer, retrieval_result)

        # 7. Regeneration Loop if verification finds discrepancies
        regeneration_count = 0
        if (
            not verification_summary.all_claims_verified
            and self.max_regeneration_attempts > 0
            and execution_result is not None
            and execution_result.status != "FAILED"
        ):
            failed_claims = [c.model_dump() for c in claims if c.verification_status in ("CONFLICTING", "UNVERIFIED")]
            if failed_claims:
                feedback = (
                    f"Found {len(failed_claims)} unverifiable or conflicting claims. "
                    "Ensure numerical values, institution names, and rank directions strictly match the empirical evidence."
                )
                regen_prompt = build_regeneration_prompt(
                    user_question=original_question,
                    evidence_context=evidence_context,
                    previous_response=draft_answer,
                    failed_claims=failed_claims,
                    verification_feedback=feedback,
                )

                t_regen_start = time.perf_counter()
                try:
                    raw_regen = llm.generate(
                        prompt=regen_prompt,
                        system_prompt=RESPONSE_SYSTEM_PROMPT,
                        temperature=0.0,
                    )
                    t_gen_duration += (time.perf_counter() - t_regen_start)
                    regeneration_count += 1

                    regen_answer, regen_raw_claims = self._parse_llm_output(raw_regen)
                    new_claims, new_audit_meta = self.auditor.audit_and_reconcile(
                        prose_answer=regen_answer,
                        structured_claims=regen_raw_claims,
                        execution_result=execution_result,
                    )
                    new_claims, new_summary = self.verifier.verify_claims(new_claims, execution_result, retrieval_result=retrieval_result)
                    new_summary.extraction_coverage = new_audit_meta.get("extraction_coverage", 1.0)
                    new_summary.text_audited_claims_count = new_audit_meta.get("text_audited_facts_count", 0)
                    new_summary.omitted_from_structured_count = new_audit_meta.get("omitted_from_structured_count", 0)
                    new_summary.structured_claims_count = new_audit_meta.get("structured_claims_count", 0)
                    new_summary.regeneration_attempted = True
                    new_summary.regeneration_count = regeneration_count

                    # If improved or verified, adopt
                    if new_summary.all_claims_verified or new_summary.conflicting_claims <= verification_summary.conflicting_claims:
                        draft_answer = regen_answer
                        claims = new_claims
                        verification_summary = new_summary
                        citations = self.citation_validator.validate_and_extract_citations(draft_answer, retrieval_result)

                except Exception:
                    # Log but keep original draft if regeneration fails
                    pass

        # 8. Preserve Warnings & Limitations
        all_warnings: List[str] = []
        all_limitations: List[str] = []

        if execution_result is not None:
            all_warnings.extend(execution_result.warnings)
            for op in execution_result.operations:
                all_warnings.extend(op.warnings)
            if execution_result.metadata and execution_result.metadata.comparability_warnings:
                all_limitations.extend(execution_result.metadata.comparability_warnings)

        # Check for unverified claims caveat
        if not verification_summary.all_claims_verified:
            caveat = (
                f"Caution: {verification_summary.unverified_claims + verification_summary.conflicting_claims} "
                "numerical claim(s) in this answer could not be fully reconciled against analytical results."
            )
            all_limitations.append(caveat)

        # 9. Extract Key Findings
        key_findings = self._extract_key_findings(draft_answer)

        # 10. Determine final ResponseStatus
        final_status: ResponseStatus = "SUCCESS"
        if response_type == "PARTIAL_EXECUTION":
            final_status = "PARTIAL_SUCCESS"
        elif response_type == "NO_EVIDENCE":
            final_status = "INSUFFICIENT_EVIDENCE"
        elif not verification_summary.all_claims_verified:
            final_status = "VERIFICATION_FAILED" if verification_summary.conflicting_claims > 0 else "PARTIAL_SUCCESS"

        total_duration = time.perf_counter() - start_total

        metadata = GenerationMetadata(
            model_name=self._get_model_name(),
            generation_duration_seconds=round(t_gen_duration, 3),
            verification_duration_seconds=round(t_ver_duration, 3),
            total_duration_seconds=round(total_duration, 3),
            prompt_tokens_estimated=int(len(prompt.split()) * 1.3),
            response_type=response_type,
            operations_count=len(execution_result.operations) if execution_result else 0,
            chunks_count=len(retrieval_result.chunks) if retrieval_result else 0,
        )

        return GeneratedResponse(
            response_id=f"resp_{uuid.uuid4().hex[:8]}",
            query_id=qid,
            response_status=final_status,
            original_question=original_question,
            answer=draft_answer,
            key_findings=key_findings,
            numerical_claims=claims,
            verification_summary=verification_summary,
            citations=citations,
            warnings=list(set(all_warnings)),
            limitations=list(set(all_limitations)),
            evidence_summary=evidence_summary,
            generation_metadata=metadata,
        )

    def _extract_key_findings(self, text: str) -> List[str]:
        """
        Extracts bullet points from the generated response to populate key_findings.
        """
        findings = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ", "• ")) and len(line) > 10:
                cleaned = re.sub(r"^[-*•]\s*", "", line).strip()
                # Remove bold wrappers if entire bullet is wrapped
                cleaned = re.sub(r"^\*\*(.*?)\*\*:\s*", r"\1: ", cleaned)
                findings.append(cleaned)
        return findings[:5]

    def _build_clarification_response(
        self,
        query_id: str,
        question: str,
        execution_result: Optional[ExecutionResult],
        evidence_summary: Dict[str, Any],
        start_total: float,
    ) -> GeneratedResponse:
        """Generates a structured clarification request response."""
        err_msg = execution_result.errors[0] if execution_result and execution_result.errors else "Clarification needed."
        answer = (
            f"To provide an accurate analysis, please clarify your question.\n\n"
            f"**Reason:** {err_msg}\n\n"
            f"Please specify the ranking category (e.g., Engineering, Management, Overall), "
            f"target year (2017–2025), or specific institutions you wish to analyze."
        )
        return GeneratedResponse(
            response_id=f"resp_{uuid.uuid4().hex[:8]}",
            query_id=query_id,
            response_status="CLARIFICATION_REQUIRED",
            original_question=question,
            answer=answer,
            key_findings=[],
            numerical_claims=[],
            verification_summary=VerificationSummary(),
            citations=[],
            warnings=execution_result.warnings if execution_result else [],
            limitations=["Query lacks required parameters for execution."],
            evidence_summary=evidence_summary,
            generation_metadata=GenerationMetadata(
                model_name=self._get_model_name(),
                total_duration_seconds=round(time.perf_counter() - start_total, 3),
                response_type="CLARIFICATION_REQUIRED",
            ),
        )

    def _build_failed_execution_response(
        self,
        query_id: str,
        question: str,
        execution_result: Optional[ExecutionResult],
        evidence_summary: Dict[str, Any],
        start_total: float,
    ) -> GeneratedResponse:
        """Generates a structured error disclosure response."""
        errors = execution_result.errors if execution_result else ["Execution error."]
        answer = (
            f"The requested analytical operation could not be completed successfully.\n\n"
            f"**Error Details:** {'; '.join(errors)}\n\n"
            f"Please verify that the requested criteria (years, categories, parameters) "
            f"exist within the NIRF dataset (2017–2025)."
        )
        return GeneratedResponse(
            response_id=f"resp_{uuid.uuid4().hex[:8]}",
            query_id=query_id,
            response_status="FAILED",
            original_question=question,
            answer=answer,
            key_findings=[],
            numerical_claims=[],
            verification_summary=VerificationSummary(),
            citations=[],
            warnings=execution_result.warnings if execution_result else [],
            limitations=["Operation execution failed."],
            evidence_summary=evidence_summary,
            generation_metadata=GenerationMetadata(
                model_name=self._get_model_name(),
                total_duration_seconds=round(time.perf_counter() - start_total, 3),
                response_type="FAILED",
            ),
        )
