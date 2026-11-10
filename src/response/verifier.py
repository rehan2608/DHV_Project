"""
Numerical claim verifier module for NIRF Response Generation (Phase 6 & 6.1).
Deterministically audits extracted claims against actual Phase 4 analytical outputs,
enforcing display-rounding tolerance, sign conventions, causality prohibitions,
zero-imputation bans, and support for aggregate statistics and multi-operation contexts.
"""

import math
import re
from typing import List, Dict, Any, Optional, Tuple

from src.execution.result_schema import ExecutionResult, OperationResult
from src.response.result_schema import (
    NumericalClaim,
    VerificationStatus,
    VerificationSummary,
    ContradictedStatus,
)


class NumericalClaimVerifier:
    """
    Independent deterministic verifier that cross-checks all extracted claims against
    grounded Phase 4 ExecutionResult data.
    """

    CAUSAL_PATTERNS = [
        r"\bcauses\b",
        r"\bcaused by\b",
        r"\bleads to\b",
        r"\bdrives\b",
        r"\bdriven by\b",
        r"\bresults in\b",
        r"\bbecause of the correlation\b",
    ]

    def __init__(self, float_tolerance: float = 0.05):
        self.float_tolerance = float_tolerance

    def verify_claims(
        self,
        claims: List[NumericalClaim],
        execution_result: Optional[ExecutionResult],
        retrieval_result: Optional[Any] = None,
    ) -> Tuple[List[NumericalClaim], VerificationSummary]:
        """
        Audits a list of claims against the provided ExecutionResult and optional RetrievalResult.
        Updates each claim's verification_status and verification_notes,
        and returns a VerificationSummary.
        """
        if not claims:
            return [], VerificationSummary(
                total_claims=0,
                verified_claims=0,
                unverified_claims=0,
                conflicting_claims=0,
                contradicted_claims=0,
                not_factual_claims=0,
                all_claims_verified=True,
            )

        if execution_result is None or not execution_result.operations:
            # Check if documentation retrieval evidence is available
            verified_count = 0
            unverified_count = 0
            conflicting_count = 0
            not_factual_count = 0

            empty_stats: Dict[str, Any] = {
                "counts": set(),
                "correlations": [],
                "regression": [],
                "state_stats": {},
                "aggregates": {},
                "all_records_count": 0,
            }

            for c in claims:
                status, notes, actual_val = self._verify_single_claim(
                    claim=c,
                    records_by_uid={},
                    records_by_name={},
                    global_stats=empty_stats,
                    retrieval_result=retrieval_result,
                )
                c.verification_status = status
                c.verification_notes = notes
                if actual_val is not None:
                    c.actual_value = actual_val

                if status == "VERIFIED":
                    verified_count += 1
                elif status in ("CONFLICTING", "CONTRADICTED"):
                    conflicting_count += 1
                elif status == "NOT_FACTUAL":
                    not_factual_count += 1
                else:
                    unverified_count += 1

            all_verified = (unverified_count == 0 and conflicting_count == 0)
            precision = (
                round(verified_count / (verified_count + conflicting_count), 4)
                if (verified_count + conflicting_count) > 0
                else None
            )
            recall = (
                round(verified_count / len(claims), 4)
                if claims
                else None
            )

            return claims, VerificationSummary(
                total_claims=len(claims),
                verified_claims=verified_count,
                unverified_claims=unverified_count,
                conflicting_claims=conflicting_count,
                contradicted_claims=conflicting_count,
                not_factual_claims=not_factual_count,
                all_claims_verified=all_verified,
                verification_precision=precision,
                verification_recall=recall,
            )

        # Index all analytical data records across operations
        records_by_uid, records_by_name, global_stats = self._index_execution_data(execution_result)

        verified_count = 0
        unverified_count = 0
        conflicting_count = 0
        not_factual_count = 0

        for claim in claims:
            status, notes, actual_val = self._verify_single_claim(
                claim=claim,
                records_by_uid=records_by_uid,
                records_by_name=records_by_name,
                global_stats=global_stats,
                retrieval_result=retrieval_result,
            )
            claim.verification_status = status
            claim.verification_notes = notes
            if actual_val is not None:
                claim.actual_value = actual_val

            if status == "VERIFIED":
                verified_count += 1
            elif status in ("CONFLICTING", "CONTRADICTED"):
                conflicting_count += 1
            elif status == "NOT_FACTUAL":
                not_factual_count += 1
            elif status == "UNVERIFIED":
                unverified_count += 1

        all_verified = (unverified_count == 0 and conflicting_count == 0)

        # Explicit definitions matching audit standards:
        # Factual precision: TP / (TP + FP) where FP is contradictory claims
        precision = (
            round(verified_count / (verified_count + conflicting_count), 4)
            if (verified_count + conflicting_count) > 0
            else None
        )
        # Empirical verification recall: verified assertions / total assertions evaluated
        recall = (
            round(verified_count / len(claims), 4)
            if claims
            else None
        )

        summary = VerificationSummary(
            total_claims=len(claims),
            verified_claims=verified_count,
            unverified_claims=unverified_count,
            conflicting_claims=conflicting_count,
            contradicted_claims=conflicting_count,
            not_factual_claims=not_factual_count,
            all_claims_verified=all_verified,
            verification_precision=precision,
            verification_recall=recall,
        )

        return claims, summary

    def _index_execution_data(
        self,
        execution_result: ExecutionResult,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Builds lookup tables for fast matching against execution data records.
        """
        records_by_uid: Dict[str, List[Dict[str, Any]]] = {}
        records_by_name: Dict[str, List[Dict[str, Any]]] = {}
        global_stats: Dict[str, Any] = {
            "counts": set(),
            "correlations": [],
            "regression": [],
            "state_stats": {},
            "aggregates": {},
            "all_records_count": 0,
        }

        def _collect_counts_recursively(val: Any):
            if isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        if not math.isnan(v) and not math.isinf(v):
                            global_stats["counts"].add(int(v))
                    elif isinstance(v, (dict, list)):
                        _collect_counts_recursively(v)
            elif isinstance(val, (list, tuple)):
                global_stats["counts"].add(len(val))
                for item in val:
                    _collect_counts_recursively(item)

        for op in execution_result.operations:
            if not op.data:
                continue

            # Recursively collect all counts and integers
            _collect_counts_recursively(op.data)

            # Check for records list
            for k in (
                "rankings",
                "trends",
                "data",
                "institutions",
                "outliers",
                "transitions",
                "gainers",
                "decliners",
                "top_institutions",
                "comparisons",
                "points",
            ):
                if k in op.data and isinstance(op.data[k], list):
                    records = op.data[k]
                    global_stats["counts"].add(len(records))
                    global_stats["all_records_count"] += len(records)
                    for r in records:
                        if isinstance(r, dict):
                            # Populate category and year context if missing from row
                            op_cat = op.data.get("category") or (execution_result.metadata.category if execution_result.metadata else None)
                            op_yr = op.data.get("year") or op.data.get("end_year") or (execution_result.metadata.year if execution_result.metadata else None)
                            if op_cat and "category" not in r:
                                r["category"] = op_cat
                            if op_yr and "year" not in r:
                                r["year"] = op_yr

                            # In points, x and y might map to param_x and param_y
                            if k == "points":
                                px = op.data.get("param_x")
                                py = op.data.get("param_y")
                                if px and "x" in r:
                                    r[str(px).lower()] = r["x"]
                                if py and "y" in r:
                                    r[str(py).lower()] = r["y"]

                            uid = str(r.get("institution_uid", "")).strip().lower()
                            name = str(
                                r.get("institution_name", r.get("institute_name_std", r.get("institute_name", r.get("name", ""))))
                            ).strip().lower()
                            if uid:
                                records_by_uid.setdefault(uid, []).append(r)
                            if name:
                                records_by_name.setdefault(name, []).append(r)
                                # Bidirectional acronym normalization
                                if "indian institute of technology" in name:
                                    short = name.replace("indian institute of technology", "iit").strip()
                                    records_by_name.setdefault(short, []).append(r)
                                elif "iit " in name or name.startswith("iit"):
                                    long_name = name.replace("iit", "indian institute of technology").strip()
                                    records_by_name.setdefault(long_name, []).append(r)

                                if "national institute of technology" in name:
                                    short = name.replace("national institute of technology", "nit").strip()
                                    records_by_name.setdefault(short, []).append(r)
                                elif "nit " in name or name.startswith("nit"):
                                    long_name = name.replace("nit", "national institute of technology").strip()
                                    records_by_name.setdefault(long_name, []).append(r)

                                if "indian institute of management" in name:
                                    short = name.replace("indian institute of management", "iim").strip()
                                    records_by_name.setdefault(short, []).append(r)
                                elif "iim " in name or name.startswith("iim"):
                                    long_name = name.replace("iim", "indian institute of management").strip()
                                    records_by_name.setdefault(long_name, []).append(r)

                                if "national institute of pharmaceutical education and research" in name:
                                    short = name.replace("national institute of pharmaceutical education and research", "niper").strip()
                                    records_by_name.setdefault(short, []).append(r)
                                elif "niper " in name or name.startswith("niper"):
                                    long_name = name.replace("niper", "national institute of pharmaceutical education and research").strip()
                                    records_by_name.setdefault(long_name, []).append(r)

                                if "all india institute of medical sciences" in name:
                                    short = name.replace("all india institute of medical sciences", "aiims").strip()
                                    records_by_name.setdefault(short, []).append(r)
                                elif "aiims " in name or name.startswith("aiims"):
                                    long_name = name.replace("aiims", "all india institute of medical sciences").strip()
                                    records_by_name.setdefault(long_name, []).append(r)

                                if "indian institute of science" in name:
                                    short = name.replace("indian institute of science", "iisc").strip()
                                    records_by_name.setdefault(short, []).append(r)
                                elif "iisc " in name or name.startswith("iisc"):
                                    long_name = name.replace("iisc", "indian institute of science").strip()
                                    records_by_name.setdefault(long_name, []).append(r)

            # Check for correlation & regression statistics
            if "regression" in op.data and isinstance(op.data["regression"], dict):
                reg = op.data["regression"]
                global_stats["regression"].append(reg)
                global_stats["correlations"].append(reg)
                for rk in ("pearson_r", "spearman_rho", "r_squared", "slope", "intercept"):
                    if rk in reg and isinstance(reg[rk], (int, float)):
                        global_stats["correlations"].append({rk: reg[rk], "correlation": reg[rk]})

            if "pair_correlations" in op.data and isinstance(op.data["pair_correlations"], list):
                for pair in op.data["pair_correlations"]:
                    if isinstance(pair, dict):
                        global_stats["correlations"].append(pair)

            if "pearson_matrix" in op.data and isinstance(op.data["pearson_matrix"], dict):
                for p1, row in op.data["pearson_matrix"].items():
                    if isinstance(row, dict):
                        for p2, val in row.items():
                            if isinstance(val, (int, float)):
                                global_stats["correlations"].append({"correlation": val, "pearson": val})

            if "correlation" in op.data or "pearson" in op.data or "spearman" in op.data:
                global_stats["correlations"].append(op.data)
                if "n" in op.data or "sample_size" in op.data:
                    n_val = op.data.get("n") or op.data.get("sample_size")
                    if isinstance(n_val, int):
                        global_stats["counts"].add(n_val)

            # Check for geographic state statistics
            if "states_analysis" in op.data and isinstance(op.data["states_analysis"], list):
                for s_dict in op.data["states_analysis"]:
                    if isinstance(s_dict, dict) and "state" in s_dict:
                        s_key = str(s_dict["state"]).strip().lower()
                        global_stats["state_stats"][s_key] = s_dict

            if "head_to_head_comparison" in op.data and isinstance(op.data["head_to_head_comparison"], dict):
                h2h = op.data["head_to_head_comparison"]
                if "metrics" in h2h and isinstance(h2h["metrics"], list):
                    for m_dict in h2h["metrics"]:
                        if isinstance(m_dict, dict) and "state" in m_dict:
                            s_key = str(m_dict["state"]).strip().lower()
                            global_stats["state_stats"].setdefault(s_key, {}).update(m_dict)

            # Check for cohort distribution aggregates
            for dist_key in ("distribution", "score_distribution", "summary", "stats"):
                if dist_key in op.data and isinstance(op.data[dist_key], dict):
                    for k_sub, v_sub in op.data[dist_key].items():
                        if isinstance(v_sub, (int, float)):
                            global_stats["aggregates"][k_sub] = v_sub

            # Check for medians in parameter relationship / bivariate analysis
            if "medians" in op.data and isinstance(op.data["medians"], dict):
                meds = op.data["medians"]
                px = str(op.data.get("param_x", "")).lower().strip()
                py = str(op.data.get("param_y", "")).lower().strip()
                if "x_median" in meds and isinstance(meds["x_median"], (int, float)):
                    val = float(meds["x_median"])
                    global_stats["aggregates"]["x_median"] = val
                    if px:
                        global_stats["aggregates"][f"median_{px}"] = val
                        global_stats["aggregates"][f"average_{px}"] = val
                        global_stats["aggregates"][px] = val
                if "y_median" in meds and isinstance(meds["y_median"], (int, float)):
                    val = float(meds["y_median"])
                    global_stats["aggregates"]["y_median"] = val
                    if py:
                        global_stats["aggregates"][f"median_{py}"] = val
                        global_stats["aggregates"][f"average_{py}"] = val
                        global_stats["aggregates"][py] = val

        return records_by_uid, records_by_name, global_stats

    def _verify_single_claim(
        self,
        claim: NumericalClaim,
        records_by_uid: Dict[str, List[Dict[str, Any]]],
        records_by_name: Dict[str, List[Dict[str, Any]]],
        global_stats: Dict[str, Any],
        retrieval_result: Optional[Any] = None,
    ) -> Tuple[VerificationStatus, str, Optional[Any]]:
        """
        Audits an individual factual, qualitative, or numerical claim against indexed execution data.
        """
        # 0. Check for non-factual statements
        if claim.claim_type == "NOT_FACTUAL" or not getattr(claim, "is_factual", True):
            return "NOT_FACTUAL", "Non-factual statement (structural heading, transitional phrase, or generic commentary).", None

        # 1. Causality check on any correlation claim
        if claim.claim_type == "CORRELATION":
            full_statement = f"{claim.claim_text or ''} {claim.statement or ''}"
            for pat in self.CAUSAL_PATTERNS:
                if re.search(pat, full_statement, re.IGNORECASE):
                    return (
                        ContradictedStatus("CONTRADICTED"),
                        f"Unsupported causal leap: Claim implies causality ('{pat}') for correlation data.",
                        None,
                    )

        target_value = claim.claimed_value if claim.claimed_value is not None else claim.value

        # Qualitative claim verification when no numerical value is specified
        if target_value is None:
            # A. Qualitative Rank Movement
            if claim.claim_type in ("RANK_CHANGE", "QUALITATIVE_RANK_CHANGE"):
                inst_records = self._find_matching_records(claim, records_by_uid, records_by_name)
                if not inst_records:
                    return (
                        "UNVERIFIED",
                        f"No execution record found for institution '{claim.institution_name or claim.institution_uid}'.",
                        None,
                    )

                rec = inst_records[0]
                if claim.category and rec.get("category"):
                    if claim.category.lower().strip() != str(rec["category"]).lower().strip():
                        return (
                            "UNVERIFIED",
                            f"Category mismatch for institution '{claim.institution_name}'.",
                            None,
                        )

                actual_diff = rec.get("rank_improvement", rec.get("rank_diff"))
                if actual_diff is None and "start_rank" in rec and "end_rank" in rec:
                    actual_diff = rec["start_rank"] - rec["end_rank"]
                if actual_diff is None and "rank_start" in rec and "rank_end" in rec:
                    actual_diff = rec["rank_start"] - rec["rank_end"]

                if actual_diff is None:
                    return "UNVERIFIED", f"Rank movement data unavailable for '{claim.institution_name}'.", None

                # Determine claimed direction
                direction = claim.qualitative_direction
                if not direction:
                    full_text = f"{claim.claim_text or ''} {claim.statement or ''}".lower()
                    if any(w in full_text for w in ("improved", "rose", "climbed", "advanced", "gained", "improvement", "improver", "positive rank")):
                        direction = "improved"
                    elif any(w in full_text for w in ("declined", "dropped", "fell", "lost", "decline", "decliner", "worsened", "negative rank")):
                        direction = "declined"
                    elif any(w in full_text for w in ("unchanged", "retained", "same rank", "flat")):
                        direction = "unchanged"

                if not direction:
                    return "UNVERIFIED", "Claim does not specify a numerical value or rank movement direction.", None

                start_lbl = rec.get("start_rank_label", rec.get("start_rank", rec.get("rank_start", "?")))
                end_lbl = rec.get("end_rank_label", rec.get("end_rank", rec.get("rank_end", "?")))

                if direction == "improved":
                    if actual_diff > 0:
                        return (
                            "VERIFIED",
                            f"Rank improvement verified for '{claim.institution_name}' (improved by {actual_diff} ranks: {start_lbl} -> {end_lbl}).",
                            actual_diff,
                        )
                    elif actual_diff < 0:
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Empirical contradiction: Claimed rank improvement for '{claim.institution_name}', but institution actually declined by {abs(actual_diff)} ranks ({start_lbl} -> {end_lbl}).",
                            actual_diff,
                        )
                    else:
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Empirical contradiction: Claimed rank improvement for '{claim.institution_name}', but rank was unchanged ({start_lbl}).",
                            actual_diff,
                        )
                elif direction == "declined":
                    if actual_diff < 0:
                        return (
                            "VERIFIED",
                            f"Rank decline verified for '{claim.institution_name}' (declined by {abs(actual_diff)} ranks: {start_lbl} -> {end_lbl}).",
                            actual_diff,
                        )
                    elif actual_diff > 0:
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Empirical contradiction: Claimed rank decline for '{claim.institution_name}', but institution actually improved by {actual_diff} ranks ({start_lbl} -> {end_lbl}).",
                            actual_diff,
                        )
                    else:
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Empirical contradiction: Claimed rank decline for '{claim.institution_name}', but rank was unchanged ({start_lbl}).",
                            actual_diff,
                        )
                elif direction == "unchanged":
                    if actual_diff == 0:
                        return (
                            "VERIFIED",
                            f"Unchanged rank verified for '{claim.institution_name}' ({start_lbl}).",
                            0,
                        )
                    else:
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Empirical contradiction: Claimed unchanged rank for '{claim.institution_name}', but rank changed by {actual_diff:+d} ranks ({start_lbl} -> {end_lbl}).",
                            actual_diff,
                        )

            # B. Qualitative Superlatives & Top Performers
            full_text = f"{claim.claim_text or ''} {claim.statement or ''}".lower()
            if (
                claim.claim_type in ("METRIC_VALUE", "RANK_VALUE", "SUPERLATIVE", "GENERAL_FACT")
                and (
                    claim.qualitative_direction in ("top", "highest", "lead", "best")
                    or any(w in full_text for w in ("leads", "highest", "top performer", "ranked first", "rank 1", "number 1"))
                )
            ):
                if "rpc" in (claim.metric or "").lower() or "research" in full_text:
                    max_inst = None
                    max_rpc = -1e9
                    for name_k, recs in records_by_name.items():
                        for r in recs:
                            val = r.get("rpc")
                            if val is None and "parameters" in r and isinstance(r["parameters"], dict):
                                val = r["parameters"].get("rpc")
                            if val is not None and isinstance(val, (int, float)):
                                if float(val) > max_rpc:
                                    max_rpc = float(val)
                                    max_inst = r.get("institution_name", r.get("institute_name_std", name_k))
                    if max_inst:
                        inst_records = self._find_matching_records(claim, records_by_uid, records_by_name)
                        inst_match = any(
                            r.get("institution_name", r.get("institute_name_std", "")).lower() == max_inst.lower()
                            for r in inst_records
                        )
                        if inst_match or (claim.institution_name and claim.institution_name.lower() in max_inst.lower()):
                            return "VERIFIED", f"Institution '{claim.institution_name}' verified with highest RPC ({max_rpc:.2f}).", round(max_rpc, 4)
                        else:
                            return (
                                ContradictedStatus("CONTRADICTED"),
                                f"Empirical contradiction: '{max_inst}' had the highest RPC ({max_rpc:.2f}), not '{claim.institution_name}'.",
                                round(max_rpc, 4),
                            )

                if "score" in (claim.metric or "").lower() or "overall" in full_text or "top" in full_text:
                    max_inst = None
                    max_score = -1e9
                    for name_k, recs in records_by_name.items():
                        for r in recs:
                            val = r.get("score")
                            if val is not None and isinstance(val, (int, float)):
                                if float(val) > max_score:
                                    max_score = float(val)
                                    max_inst = r.get("institution_name", r.get("institute_name_std", name_k))
                    if max_inst:
                        inst_records = self._find_matching_records(claim, records_by_uid, records_by_name)
                        inst_match = any(
                            r.get("institution_name", r.get("institute_name_std", "")).lower() == max_inst.lower()
                            for r in inst_records
                        )
                        if inst_match or (claim.institution_name and claim.institution_name.lower() in max_inst.lower()):
                            return "VERIFIED", f"Institution '{claim.institution_name}' verified as highest overall score ({max_score:.2f}).", round(max_score, 4)
                        else:
                            return (
                                ContradictedStatus("CONTRADICTED"),
                                f"Empirical contradiction: '{max_inst}' had the highest score ({max_score:.2f}), not '{claim.institution_name}'.",
                                round(max_score, 4),
                            )

            # C. Qualitative Comparisons (State or Institution)
            if claim.claim_type in ("INSTITUTION_COMPARISON", "QUALITATIVE_COMPARISON"):
                if claim.comparison_entities and len(claim.comparison_entities) >= 2:
                    ent_a, ent_b = claim.comparison_entities[0], claim.comparison_entities[1]
                    s_a = global_stats["state_stats"].get(ent_a.lower().strip())
                    s_b = global_stats["state_stats"].get(ent_b.lower().strip())
                    if s_a and s_b:
                        m = (claim.metric or "average_score").lower()
                        val_a = s_a.get(m, s_a.get(f"average_{m}", s_a.get("average_score")))
                        val_b = s_b.get(m, s_b.get(f"average_{m}", s_b.get("average_score")))
                        if val_a is not None and val_b is not None:
                            is_a_higher = float(val_a) > float(val_b)
                            claimed_a_higher = claim.qualitative_direction in ("better", "higher", "outperformed", "more", None)
                            if (is_a_higher and claimed_a_higher) or (not is_a_higher and not claimed_a_higher):
                                return "VERIFIED", f"Comparison verified: {ent_a} ({val_a:.2f}) outperformed {ent_b} ({val_b:.2f}).", None
                            else:
                                return (
                                    ContradictedStatus("CONTRADICTED"),
                                    f"Empirical contradiction: {ent_a} ({val_a:.2f}) did not outperform {ent_b} ({val_b:.2f}).",
                                    None,
                                )

            # D. Documentation / RAG claims check
            if retrieval_result is not None and getattr(retrieval_result, "has_results", lambda: False)():
                claim_str = f"{claim.claim_text or ''} {claim.statement or ''}".lower()
                for chunk in retrieval_result.chunks:
                    chunk_text = (getattr(chunk, "text", None) or getattr(chunk, "content", "") or "").lower()
                    if "research and professional practice" in claim_str and "research and professional practice" in chunk_text:
                        return "VERIFIED", f"Verified against retrieved documentation [{chunk.document_id}].", None
                    if "0.00 to 100.00" in claim_str and "0.00 to 100.00" in chunk_text:
                        return "VERIFIED", f"Verified against retrieved documentation [{chunk.document_id}].", None
                    if claim.institution_name and claim.institution_name.lower() in chunk_text:
                        return "VERIFIED", f"Verified against retrieved documentation [{chunk.document_id}].", None

            return "UNVERIFIED", "Claim does not specify a numerical value and cannot be verified from available evidence.", None

        # 1. Verify numerical correlation coefficient
        if claim.claim_type == "CORRELATION":
            claimed_coeff = float(target_value)
            for c_dict in global_stats["correlations"]:
                # Check all common correlation and regression metric fields
                for key_name in ("correlation", "pearson", "spearman", "pearson_r", "spearman_rho", "r_squared", "r"):
                    actual_coeff = c_dict.get(key_name)
                    if actual_coeff is not None and isinstance(actual_coeff, (int, float)):
                        if abs(claimed_coeff - float(actual_coeff)) <= self.float_tolerance:
                            return (
                                "VERIFIED",
                                f"Correlation coefficient {claimed_coeff} matches actual {key_name} {actual_coeff:.4f}",
                                round(float(actual_coeff), 4),
                            )
            return (
                ContradictedStatus("CONTRADICTED"),
                f"Claimed correlation coefficient {claimed_coeff} does not match any executed correlation.",
                None,
            )

        # 2. Check Count Claims
        if claim.claim_type == "COUNT":
            claimed_count = int(round(float(target_value)))
            if claimed_count in global_stats["counts"]:
                return (
                    "VERIFIED",
                    f"Count of {claimed_count} exactly matches executed dataset cohort size.",
                    claimed_count,
                )
            return (
                "UNVERIFIED",
                f"Claimed count {claimed_count} does not match any operation record count in evidence.",
                None,
            )

        # 3. Check Rank Movement Claims (RANK_CHANGE)
        if claim.claim_type == "RANK_CHANGE":
            inst_records = self._find_matching_records(claim, records_by_uid, records_by_name)
            if not inst_records:
                return (
                    "UNVERIFIED",
                    f"No execution record found for institution '{claim.institution_name or claim.institution_uid}'.",
                    None,
                )

            claimed_val = float(target_value)

            for rec in inst_records:
                # Support both 'rank_improvement' (rankings.py) and 'rank_diff' (transitions.py)
                actual_diff = rec.get("rank_improvement", rec.get("rank_diff"))

                if actual_diff is None and "start_rank" in rec and "end_rank" in rec:
                    actual_diff = rec["start_rank"] - rec["end_rank"]

                if actual_diff is not None:
                    # Direction check
                    if (actual_diff > 0 and claimed_val < 0) or (actual_diff < 0 and claimed_val > 0):
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Rank direction reversed: Claimed {claimed_val:+g} ranks but actual movement was {actual_diff:+d} ranks.",
                            actual_diff,
                        )
                    # Signed match
                    if abs(claimed_val - actual_diff) <= 0.5:
                        return (
                            "VERIFIED",
                            f"Rank movement of {claimed_val:+g} ranks verified against actual {actual_diff:+d}.",
                            actual_diff,
                        )
                    # Absolute magnitude match when positive verbally indicates improvement
                    if actual_diff > 0 and abs(abs(claimed_val) - actual_diff) <= 0.5:
                        return (
                            "VERIFIED",
                            f"Rank improvement of {actual_diff:+d} ranks verified.",
                            actual_diff,
                        )

            first_diff = inst_records[0].get("rank_improvement", inst_records[0].get("rank_diff"))
            return (
                ContradictedStatus("CONTRADICTED"),
                f"Claimed rank change {claimed_val} differs from actual records.",
                first_diff,
            )

        # 4. Check Aggregate Statistics (AGGREGATE_STATISTIC)
        if claim.claim_type == "AGGREGATE_STATISTIC":
            claimed_num = float(target_value)
            target_state = (claim.state or "").strip().lower()

            # Attempt to locate state from claim text if not explicitly set
            if not target_state:
                combined_text = f"{claim.claim_text or ''} {claim.statement or ''}".lower()
                for s_candidate in global_stats["state_stats"].keys():
                    if s_candidate in combined_text:
                        target_state = s_candidate
                        break

            if target_state and target_state in global_stats["state_stats"]:
                s_rec = global_stats["state_stats"][target_state]
                metric_name = (claim.metric or "").strip().lower()

                candidate_keys = []
                if "rpc" in metric_name:
                    candidate_keys.extend(["average_rpc", "median_rpc", "rpc"])
                elif "tlr" in metric_name:
                    candidate_keys.extend(["average_tlr", "median_tlr", "tlr"])
                elif "score" in metric_name:
                    if (claim.statistic_type or "").lower() == "median":
                        candidate_keys.extend(["median_score", "average_score"])
                    else:
                        candidate_keys.extend(["average_score", "median_score"])
                elif any(k in metric_name for k in ("distinct", "institutions", "count", "entries")):
                    candidate_keys.extend(["distinct_institutions", "total_ranked_entries"])
                elif "top_10" in metric_name or "top 10" in metric_name:
                    candidate_keys.append("top_10_institutions")
                elif "top_50" in metric_name or "top 50" in metric_name:
                    candidate_keys.append("top_50_institutions")
                elif "top_100" in metric_name or "top 100" in metric_name:
                    candidate_keys.append("top_100_institutions")
                elif metric_name:
                    if metric_name in s_rec:
                        candidate_keys.append(metric_name)
                    if f"average_{metric_name}" in s_rec:
                        candidate_keys.append(f"average_{metric_name}")
                    if f"median_{metric_name}" in s_rec:
                        candidate_keys.append(f"median_{metric_name}")
                else:
                    # Check all numeric keys in state record if no metric specified
                    candidate_keys.extend([k for k, v in s_rec.items() if isinstance(v, (int, float))])

                for ck in candidate_keys:
                    if ck in s_rec and s_rec[ck] is not None:
                        act_val = float(s_rec[ck])
                        tol = 0.5 if "institutions" in ck or "entries" in ck else self.float_tolerance
                        if abs(claimed_num - act_val) <= tol:
                            return (
                                "VERIFIED",
                                f"Aggregate {claimed_num} for {target_state.title()} ({ck}) matches actual {act_val:.2f}.",
                                round(act_val, 4),
                            )

                if candidate_keys and candidate_keys[0] in s_rec and s_rec[candidate_keys[0]] is not None:
                    act_val = float(s_rec[candidate_keys[0]])
                    return (
                        ContradictedStatus("CONTRADICTED"),
                        f"Value discrepancy for {target_state.title()} {candidate_keys[0]}: Claimed {claimed_num}, actual is {act_val:.2f}.",
                        round(act_val, 4),
                    )

                return (
                    "UNVERIFIED",
                    f"Metric '{metric_name}' not found for state '{target_state.title()}'.",
                    None,
                )

            # Check general cohort aggregates if not state-specific
            if global_stats["aggregates"]:
                for agg_k, agg_v in global_stats["aggregates"].items():
                    if abs(claimed_num - float(agg_v)) <= self.float_tolerance:
                        return (
                            "VERIFIED",
                            f"Aggregate statistic {claimed_num} matches cohort {agg_k} ({agg_v}).",
                            round(float(agg_v), 4),
                        )

            return "UNVERIFIED", "State or cohort aggregate data not located.", None

        # 5. Check Institution Metric & Rank Values (METRIC_VALUE, RANK_VALUE, INSTITUTION_COMPARISON)
        if claim.claim_type in ("METRIC_VALUE", "RANK_VALUE", "INSTITUTION_COMPARISON"):
            if not claim.institution_name and not claim.institution_uid and retrieval_result is not None and getattr(retrieval_result, "has_results", lambda: False)():
                # Documentation metric/range verification (e.g. data dictionary valid range 0.00 to 100.00)
                claim_str = f"{claim.claim_text or ''} {claim.statement or ''}".lower()
                for chunk in retrieval_result.chunks:
                    chunk_text = (getattr(chunk, "text", None) or getattr(chunk, "content", "") or "").lower()
                    if str(target_value) in chunk_text or "0.00 to 100.00" in chunk_text or (claim.metric and claim.metric.lower() in chunk_text):
                        return (
                            "VERIFIED",
                            f"Documentation parameter metric verified against retrieved reference [{chunk.document_id}].",
                            target_value,
                        )

            inst_records = self._find_matching_records(claim, records_by_uid, records_by_name)
            if not inst_records:
                # Institution not found in output
                return (
                    "UNVERIFIED",
                    f"Institution '{claim.institution_name or claim.institution_uid}' not in execution result.",
                    None,
                )

            metric_name = (claim.metric or "").strip().lower()
            claimed_num = float(target_value)

            for rec in inst_records:
                # Category check: strictly ensure record belongs to the claimed category
                if claim.category and rec.get("category"):
                    if claim.category.lower().strip() != str(rec["category"]).lower().strip():
                        continue

                # Year check: strictly ensure record belongs to the claimed year
                if claim.year is not None and rec.get("year") is not None:
                    try:
                        if int(claim.year) != int(rec["year"]):
                            continue
                    except (ValueError, TypeError):
                        pass

                # Check candidate fields for value
                actual_val = None
                if metric_name == "rank":
                    actual_val = rec.get("rank", rec.get("end_rank", rec.get("start_rank")))
                elif metric_name == "score":
                    actual_val = rec.get("score", rec.get("end_score", rec.get("start_score")))
                else:
                    actual_val = rec.get(metric_name)
                    if actual_val is None and "parameters" in rec and isinstance(rec["parameters"], dict):
                        actual_val = rec["parameters"].get(metric_name)

                # Check zero-imputation prohibition
                if actual_val is None or (isinstance(actual_val, float) and math.isnan(actual_val)):
                    if claimed_num == 0.0:
                        return (
                            "CONFLICTING",
                            f"Violation of missing data rule: Missing {metric_name.upper()} was claimed as 0.0.",
                            None,
                        )
                    return (
                        "UNVERIFIED",
                        f"Metric '{metric_name}' is missing/NaN in record for institution '{claim.institution_name}'.",
                        None,
                    )

                if actual_val is not None and isinstance(actual_val, (int, float)):
                    tol = 0.5 if metric_name == "rank" else self.float_tolerance
                    if abs(claimed_num - float(actual_val)) <= tol:
                        return (
                            "VERIFIED",
                            f"Value {claimed_num} for {metric_name.upper()} matches actual {actual_val:.4f}.",
                            round(float(actual_val), 4),
                        )
                    else:
                        return (
                            ContradictedStatus("CONTRADICTED"),
                            f"Value discrepancy for {metric_name.upper()}: Claimed {claimed_num}, actual is {actual_val:.4f}.",
                            round(float(actual_val), 4),
                        )

            return (
                "UNVERIFIED",
                f"Metric '{metric_name}' not found in record for institution '{claim.institution_name}'.",
                None,
            )

        return "UNVERIFIED", "Unrecognized or unsupported claim type.", None

    def _find_matching_records(
        self,
        claim: NumericalClaim,
        records_by_uid: Dict[str, List[Dict[str, Any]]],
        records_by_name: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        Locates all candidate analytical records matching the claim's institution.
        """
        if claim.institution_uid:
            uid_key = claim.institution_uid.lower().strip()
            if uid_key in records_by_uid:
                return records_by_uid[uid_key]

        if claim.institution_name:
            name_key = claim.institution_name.lower().strip()
            # Normalize acronyms
            name_expanded = (
                name_key.replace("iit", "indian institute of technology")
                .replace("iim", "indian institute of management")
                .replace("nit", "national institute of technology")
                .replace("niper", "national institute of pharmaceutical education and research")
                .replace("aiims", "all india institute of medical sciences")
                .replace("iisc", "indian institute of science")
                .strip()
            )
            name_collapsed = (
                name_key.replace("indian institute of technology", "iit")
                .replace("indian institute of management", "iim")
                .replace("national institute of technology", "nit")
                .replace("national institute of pharmaceutical education and research", "niper")
                .replace("all india institute of medical sciences", "aiims")
                .replace("indian institute of science", "iisc")
                .strip()
            )

            # Exact match
            if name_key in records_by_name:
                return records_by_name[name_key]
            if name_collapsed in records_by_name:
                return records_by_name[name_collapsed]
            if name_expanded in records_by_name:
                return records_by_name[name_expanded]

            # Candidate matching with ambiguity guard
            candidate_recs: List[Dict[str, Any]] = []
            candidate_uids = set()

            for stored_name, recs in records_by_name.items():
                is_match = False
                for query_variant in (name_key, name_collapsed, name_expanded):
                    if len(query_variant) < 4:
                        if re.search(rf"\b{re.escape(query_variant)}\b", stored_name):
                            is_match = True
                            break
                    else:
                        if query_variant in stored_name or stored_name in query_variant:
                            is_match = True
                            break
                if is_match:
                    for r in recs:
                        uid_val = r.get("institution_uid")
                        if uid_val:
                            candidate_uids.add(str(uid_val).lower())
                    candidate_recs.extend(recs)

            # Never resolve an ambiguous institution by choosing the first matching record
            if len(candidate_uids) == 1:
                return candidate_recs
            elif len(candidate_uids) > 1:
                # Ambiguous: multiple distinct institutions match this name
                return []

        return []
