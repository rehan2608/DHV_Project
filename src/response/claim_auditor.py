"""
Independent Claim Auditor for NIRF Response Generation (Phase 6.1).
Performs a dual-direction consistency audit between:
1. The natural-language prose answer.
2. The model-generated structured claim list.
3. The underlying analytical execution evidence.
Ensures no checkable numerical statement in prose can silently bypass verification.
"""

import math
import re
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import uuid

from src.execution.result_schema import ExecutionResult
from src.response.claim_extractor import ClaimExtractor
from src.response.result_schema import NumericalClaim, ClaimType


class IndependentClaimAuditor:
    """
    Independently cross-checks prose text against structured claims.
    Reconciles missing claims and audits coverage.
    """

    def __init__(self, float_tolerance: float = 0.05):
        self.float_tolerance = float_tolerance
        self.extractor = ClaimExtractor()

    def audit_and_reconcile(
        self,
        prose_answer: str,
        structured_claims: List[Union[NumericalClaim, Dict[str, Any]]],
        execution_result: Optional[ExecutionResult],
    ) -> Tuple[List[NumericalClaim], Dict[str, Any]]:
        """
        Reconciles structured claims with prose text, checks for omitted numerical facts,
        and harmonizes entity UIDs from execution evidence.
        """
        reconciled_claims: List[NumericalClaim] = []
        known_institutions = self.extractor._extract_known_institutions(execution_result)

        # 1. Normalize and validate structured claims from LLM
        for claim in structured_claims:
            norm_claim = self._normalize_claim(claim, known_institutions, execution_result)
            reconciled_claims.append(norm_claim)

        # 2. Extract checkable numerical assertions independently from prose text
        prose_claims = self.extractor.extract_claims(prose_answer, execution_result)

        # 3. Cross-check: ensure every prose claim is represented in structured claims
        omitted_claims: List[NumericalClaim] = []
        covered_count = 0

        for p_claim in prose_claims:
            is_covered = False
            for s_claim in reconciled_claims:
                if self._claims_match(p_claim, s_claim):
                    is_covered = True
                    break

            if is_covered:
                covered_count += 1
                if not getattr(s_claim, "qualitative_direction", None) and getattr(p_claim, "qualitative_direction", None):
                    s_claim.qualitative_direction = p_claim.qualitative_direction
            else:
                # Discrepancy: checkable fact mentioned in prose was omitted from structured claims
                p_claim.audit_discrepancy = "Numerical statement in prose was omitted from structured claims list."
                omitted_claims.append(p_claim)
                reconciled_claims.append(p_claim)

        total_prose = len(prose_claims)
        coverage = (covered_count / total_prose) if total_prose > 0 else 1.0

        audit_metrics = {
            "structured_claims_count": len(structured_claims),
            "text_audited_facts_count": total_prose,
            "omitted_from_structured_count": len(omitted_claims),
            "extraction_coverage": round(coverage, 4),
            "prose_numbers_found": total_prose,
            "unclaimed_prose_numbers": len(omitted_claims),
        }

        # Canonical fact deduplication: preserve distinct assertions while preventing
        # duplicate representations of the identical underlying fact from inflating claim counts
        deduped_claims: List[NumericalClaim] = []
        for c in reconciled_claims:
            matched_idx = -1
            for idx, existing in enumerate(deduped_claims):
                if self._claims_match(c, existing):
                    matched_idx = idx
                    break

            if matched_idx >= 0:
                # Harmonize richer metadata into the existing claim
                existing = deduped_claims[matched_idx]
                if not existing.category and c.category:
                    existing.category = c.category
                if existing.year is None and c.year is not None:
                    existing.year = c.year
                if not existing.institution_uid and c.institution_uid:
                    existing.institution_uid = c.institution_uid
                if not existing.state and c.state:
                    existing.state = c.state
                if not existing.statistic_type and c.statistic_type:
                    existing.statistic_type = c.statistic_type
                if not getattr(existing, "qualitative_direction", None) and getattr(c, "qualitative_direction", None):
                    existing.qualitative_direction = c.qualitative_direction
                continue

            deduped_claims.append(c)

        return deduped_claims, audit_metrics

    def build_semantic_fact_key(self, claim: NumericalClaim) -> Tuple:
        """
        Builds a comprehensive semantic identity key for a claim.
        Deduplicates identical factual assertions while strictly preserving distinct:
        - Categories (e.g. Engineering vs Overall)
        - Operations / analytical contexts
        - Cohorts (e.g. Top 10 vs Top 50)
        - Entities (institutions or states)
        - Metrics (score vs rpc vs tlr)
        - Statistics (mean vs median)
        - Years / Year ranges
        - Numerical values (within tolerance)
        - Units
        """
        c_type = claim.claim_type
        # Entity identity: prioritize UID, then normalized institution name, then state
        entity = (claim.institution_uid or claim.institution_name or claim.state or "").lower().strip()
        category = (claim.category or "").lower().strip()
        metric = (claim.metric or "").lower().strip()
        stat_type = (claim.statistic_type or "").lower().strip()
        unit = (claim.unit or "").lower().strip()

        # Year or temporal window
        year_key: Any = None
        if claim.year is not None:
            year_key = claim.year
        elif claim.comparison_period:
            year_key = tuple(claim.comparison_period)

        # Operation identity if present
        op_id = (claim.operation_id or claim.source_operation_id or "").strip()

        # Cohort signature from statement or metric
        cohort = ""
        full_text = f"{claim.claim_text or ''} {claim.statement or ''}".lower()
        if "top 10" in full_text or "top_10" in metric:
            cohort = "top_10"
        elif "top 50" in full_text or "top_50" in metric:
            cohort = "top_50"
        elif "top 100" in full_text or "top_100" in metric:
            cohort = "top_100"

        # Normalized value
        val = claim.claimed_value if claim.claimed_value is not None else claim.value
        try:
            val_norm = round(float(val), 4) if val is not None else None
        except (ValueError, TypeError):
            val_norm = str(val) if val is not None else None

        return (
            c_type,
            entity,
            category,
            year_key,
            metric,
            stat_type,
            cohort,
            op_id,
            val_norm,
            unit,
        )

    def _normalize_claim(
        self,
        claim: Union[NumericalClaim, Dict[str, Any]],
        known_institutions: Dict[str, str],
        execution_result: Optional[ExecutionResult],
    ) -> NumericalClaim:
        """Harmonizes institution UIDs, category, and year on structured claims."""
        if isinstance(claim, dict):
            c_type = claim.get("claim_type", "METRIC_VALUE")
            stmt = claim.get("statement", claim.get("claim_text", ""))
            val = claim.get("value", claim.get("claimed_value"))
            claim_obj = NumericalClaim(
                claim_id=claim.get("claim_id") or f"c_{uuid.uuid4().hex[:6]}",
                claim_type=c_type,
                claim_text=stmt,
                statement=stmt,
                institution_name=claim.get("institution_name"),
                institution_uid=claim.get("institution_uid"),
                metric=claim.get("metric"),
                claimed_value=val,
                value=val,
                year=claim.get("year"),
                state=claim.get("state"),
                statistic_type=claim.get("statistic_type"),
                unit=claim.get("unit"),
            )
            claim = claim_obj

        # Normalize institution UID if missing but name is present
        if not claim.institution_uid and claim.institution_name:
            name_clean = claim.institution_name.lower().strip()
            if name_clean in known_institutions:
                claim.institution_uid = known_institutions[name_clean]
            else:
                for k, uid in known_institutions.items():
                    if k in name_clean or name_clean in k:
                        claim.institution_uid = uid
                        break

        # Normalize category and year from execution metadata if omitted
        if execution_result and execution_result.metadata:
            if not claim.category and execution_result.metadata.category:
                claim.category = execution_result.metadata.category
            if claim.year is None and execution_result.metadata.year:
                claim.year = execution_result.metadata.year

        # Normalize value representation
        target_val = claim.claimed_value if claim.claimed_value is not None else claim.value
        if target_val is not None and isinstance(target_val, str):
            try:
                if "." in target_val:
                    target_val = float(target_val)
                else:
                    target_val = int(target_val)
            except ValueError:
                pass
        claim.claimed_value = target_val
        claim.value = target_val

        return claim

    def _claims_match(self, c1: NumericalClaim, c2: NumericalClaim) -> bool:
        """Determines if two claims refer to the same factual assertion."""
        # 1. Compare values if both are specified
        val1 = c1.claimed_value if c1.claimed_value is not None else c1.value
        val2 = c2.claimed_value if c2.claimed_value is not None else c2.value

        if val1 is not None and val2 is not None:
            try:
                f1, f2 = float(val1), float(val2)
                if abs(f1 - f2) > self.float_tolerance:
                    if abs(abs(f1) - abs(f2)) > self.float_tolerance:
                        return False
            except (ValueError, TypeError):
                if val1 != val2:
                    return False
        elif val1 is None and val2 is None:
            # Both are qualitative claims: ensure compatible claim types and directions
            if c1.claim_type != c2.claim_type:
                return False
            d1 = getattr(c1, "qualitative_direction", None)
            d2 = getattr(c2, "qualitative_direction", None)
            if d1 and d2 and d1.lower().strip() != d2.lower().strip():
                return False
        else:
            # One is numerical and one is qualitative: match if same claim_type
            if c1.claim_type != c2.claim_type:
                return False

        # 2. Compare institution if specified in both
        if c1.institution_uid and c2.institution_uid:
            if c1.institution_uid.lower() != c2.institution_uid.lower():
                return False
        elif c1.institution_name and c2.institution_name:
            n1 = c1.institution_name.lower().strip()
            n2 = c2.institution_name.lower().strip()
            if n1 != n2 and n1 not in n2 and n2 not in n1:
                return False

        # 3. Compare metric if specified in both
        if c1.metric and c2.metric:
            m1 = c1.metric.lower().strip()
            m2 = c2.metric.lower().strip()
            if m1 != m2 and m1 not in m2 and m2 not in m1:
                params = {"rpc", "tlr", "go", "oi", "perception", "score"}
                count_metrics = {"count", "rank", "institutions", "colleges", "entities", "cohort", "sample"}
                if (m1 == "score" and m2 in params) or (m2 == "score" and m1 in params):
                    pass
                elif m1 in count_metrics and m2 in count_metrics:
                    pass
                else:
                    return False

        # 4. Compare state / geographic entity if specified
        s1 = (c1.state or "").lower().strip()
        s2 = (c2.state or "").lower().strip()
        if s1 and s2 and s1 != s2:
            return False
        if s2 and not s1:
            t1 = (c1.claim_text or "").lower()
            for ks in ("karnataka", "tamil nadu", "maharashtra", "delhi", "kerala", "uttar pradesh", "west bengal"):
                if ks in t1 and ks != s2:
                    return False
        elif s1 and not s2:
            t2 = (c2.claim_text or "").lower()
            for ks in ("karnataka", "tamil nadu", "maharashtra", "delhi", "kerala", "uttar pradesh", "west bengal"):
                if ks in t2 and ks != s1:
                    return False

        # 5. Compare category if specified in both
        cat1 = (c1.category or "").lower().strip()
        cat2 = (c2.category or "").lower().strip()
        if cat1 and cat2 and cat1 != cat2:
            return False

        # 6. Compare statistic type if specified in both
        st1 = (c1.statistic_type or "").lower().strip()
        st2 = (c2.statistic_type or "").lower().strip()
        if st1 and st2 and st1 != st2:
            return False

        # 7. Compare operation identity if specified in both
        op1 = (c1.operation_id or c1.source_operation_id or "").strip()
        op2 = (c2.operation_id or c2.source_operation_id or "").strip()
        if op1 and op2 and op1 != op2:
            return False

        # 8. Compare cohort / subgroup signature if detectable in text
        t1 = f"{c1.claim_text or ''} {c1.statement or ''}".lower()
        t2 = f"{c2.claim_text or ''} {c2.statement or ''}".lower()
        cohort_keywords = ("top 10", "top 50", "top 100", "outlier", "gainer", "decliner", "new entrant", "departed")
        found1 = {ck for ck in cohort_keywords if ck in t1}
        found2 = {ck for ck in cohort_keywords if ck in t2}
        if found1 and found2 and found1 != found2:
            return False
        if found1 and not found2:
            if any(ck in found1 for ck in ("outlier", "departed", "new entrant")):
                return False
        elif found2 and not found1:
            if any(ck in found2 for ck in ("outlier", "departed", "new entrant")):
                return False

        return True
