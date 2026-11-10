"""
Claim extractor module for NIRF Response Generation (Phase 6).
Extracts typed, structured numerical and factual claims from generated responses
using deterministic NLP parsing and evidence entity matching.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple, Union
import uuid

from src.execution.result_schema import ExecutionResult
from src.response.result_schema import NumericalClaim, ClaimType


class ClaimExtractor:
    """
    Scans generated natural-language text to identify extractable factual and numerical assertions.
    Associates claims with known institutions, metrics, and operation contexts.
    """

    METRICS = {
        "score": ["score", "scores", "scored", "achieved", "achieves", "secured", "secures", "obtained", "composite score", "overall score"],
        "tlr": ["tlr", "teaching learning", "teaching, learning"],
        "rpc": ["rpc", "research and professional", "research performance"],
        "go": ["go", "graduation outcomes", "graduation outcome"],
        "oi": ["oi", "outreach and inclusivity", "outreach"],
        "perception": ["perception", "peer perception", "pr"],
        "research_sfc": ["research_sfc", "scholarly faculty"],
        "research_qnr": ["research_qnr", "quantitative output"],
        "research_qlr": ["research_qlr", "qualitative metrics"],
    }

    def __init__(self):
        pass

    def extract_claims(
        self,
        text: str,
        execution_result: Optional[ExecutionResult] = None,
    ) -> List[NumericalClaim]:
        """
        Extracts all verifiable factual assertions from response text.
        """
        if not text or not text.strip():
            return []

        claims: List[NumericalClaim] = []
        known_institutions = self._extract_known_institutions(execution_result)

        # Split into sentences, then clauses
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

        for sent in sentences:
            sent = sent.strip()
            if not sent or sent.startswith("#") or sent.startswith("|") or len(sent) < 5:
                continue

            # Split sentence into clauses (by semicolons, commas, contrastive conjunctions, or 'and' before institution keywords)
            clauses = re.split(r"[,;]|\b(?:while|whereas|but|compared to|versus|vs\.?)\b|\band\s+(?=(?:IIT|NIT|IIM|IISc|BITS|AIIMS|Indian|National)\b)", sent, flags=re.IGNORECASE)

            for clause in clauses:
                clause = clause.strip()
                if not clause or len(clause) < 5:
                    continue

                # Strip citation tags like [CITE-01] so they don't get misparsed as metrics/counts
                clean_clause = re.sub(r"\[CITE-\d+\]", "", clause).strip()
                if not clean_clause:
                    continue

                # 1. Check for Rank Movements
                movement_claims = self._extract_rank_movements(clean_clause, known_institutions)
                claims.extend(movement_claims)

                # 2. Check for Correlation Claims
                corr_claims = self._extract_correlations(clean_clause)
                claims.extend(corr_claims)

                # 3. Check for Institution Metric Scores
                metric_claims = self._extract_metric_scores(clean_clause, known_institutions)
                claims.extend(metric_claims)

                # 4. Check for Static Rankings
                rank_claims = self._extract_static_ranks(clean_clause, known_institutions)
                claims.extend(rank_claims)

                # 5. Check for Counts
                count_claims = self._extract_counts(clean_clause)
                claims.extend(count_claims)

                # 6. Check for Comparisons
                comp_claims = self._extract_comparisons(clean_clause, known_institutions)
                claims.extend(comp_claims)

                # 7. Check for Superlatives
                sup_claims = self._extract_superlatives(clean_clause, known_institutions)
                claims.extend(sup_claims)

        # 8. Check for Markdown Tables (extracting structured tabular assertions directly)
        table_claims = self._extract_table_claims(text, known_institutions, execution_result)
        claims.extend(table_claims)

        # 9. Check for Bullet Lists under Directional Headings
        bullet_claims = self._extract_bullet_list_claims(text, known_institutions)
        claims.extend(bullet_claims)

        # Deduplicate claims by claim_type, entity (inst/state), metric, claimed_value, direction
        unique_claims: List[NumericalClaim] = []
        seen = set()
        for c in claims:
            ent_key = c.institution_uid or c.institution_name or c.state or (tuple(c.comparison_entities) if c.comparison_entities else "")
            key = (c.claim_type, ent_key, c.metric, c.claimed_value, getattr(c, "qualitative_direction", None))
            if key not in seen:
                seen.add(key)
                unique_claims.append(c)

        return unique_claims

    def _extract_known_institutions(
        self,
        execution_result: Optional[ExecutionResult],
    ) -> Dict[str, str]:
        """
        Builds a lookup mapping of known institution names / acronyms to UIDs from execution evidence.
        """
        known: Dict[str, str] = {}
        if not execution_result or not execution_result.operations:
            return known

        for op in execution_result.operations:
            if not op.data:
                continue
            for k in ("rankings", "trends", "data", "institutions", "outliers", "transitions", "gainers", "decliners", "top_institutions", "comparisons", "points"):
                if k in op.data and isinstance(op.data[k], list):
                    for row in op.data[k]:
                        if isinstance(row, dict):
                            uid = row.get("institution_uid", "")
                            name = row.get("institution_name", row.get("institute_name_std", row.get("institute_name", row.get("name", ""))))
                            if name:
                                known[name.lower()] = uid
                                # Also index common acronyms
                                if "indian institute of technology" in name.lower():
                                    short = name.lower().replace("indian institute of technology", "iit")
                                    known[short] = uid
                                elif "national institute of technology" in name.lower():
                                    short = name.lower().replace("national institute of technology", "nit")
                                    known[short] = uid
                                elif "indian institute of management" in name.lower():
                                    short = name.lower().replace("indian institute of management", "iim")
                                    known[short] = uid
        return known

    def _find_institution_in_text(
        self,
        text: str,
        known_institutions: Dict[str, str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Finds the best matching institution name and UID from the text.
        """
        text_lower = text.lower()
        # Direct search prioritizing earliest appearance in clause, then length
        earliest_inst = None
        earliest_uid = None
        earliest_pos = 999999
        longest_len = 0

        for name_key, uid in known_institutions.items():
            pos = text_lower.find(name_key)
            if pos != -1:
                if pos < earliest_pos or (pos == earliest_pos and len(name_key) > longest_len):
                    earliest_pos = pos
                    longest_len = len(name_key)
                    earliest_inst = name_key.title()
                    earliest_uid = uid

        if earliest_inst:
            return earliest_inst, earliest_uid

        # Fallback to regex patterns like "IIT [City]" or "NIT [City]"
        inst_match = re.search(r"\b(IIT|NIT|BITS|IIIT|IIM)\s+([A-Z][a-z]+)\b", text)
        if inst_match:
            return inst_match.group(0), None

        return None, None

    def _extract_rank_movements(
        self,
        sent: str,
        known_institutions: Dict[str, str],
    ) -> List[NumericalClaim]:
        """
        Extracts claims regarding rank movement (improvement or decline).
        """
        claims = []
        inst_name, inst_uid = self._find_institution_in_text(sent, known_institutions)

        # Patterns like: "improved by 12 ranks", "rose 15 spots", "fell by 4 positions", "gained 25 ranks"
        pattern = r"\b(improved|rose|climbed|advanced|gained|fell|declined|dropped|lost)\s+by\s+(\d+(?:\.\d+)?)\s*(?:ranks?|positions?|spots?)\b"
        matches = re.finditer(pattern, sent, re.IGNORECASE)
        for m in matches:
            verb = m.group(1).lower()
            val = float(m.group(2))
            is_improvement = verb in ("improved", "rose", "climbed", "advanced", "gained")
            signed_val = int(val) if is_improvement else -int(val)

            claim = NumericalClaim(
                claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                claim_text=sent,
                claim_type="RANK_CHANGE",
                metric="rank_diff",
                institution_name=inst_name,
                institution_uid=inst_uid,
                claimed_value=signed_val,
                unit="ranks",
                verification_notes=f"Reported {verb} by {val} ranks",
            )
            claims.append(claim)

        # Pattern like: "from rank 45 to [rank] 33"
        from_to = re.search(r"\bfrom\s+(?:rank\s+)?(\d+)\s+to\s+(?:rank\s+)?(\d+)\b", sent, re.IGNORECASE)
        if from_to:
            r_start = int(from_to.group(1))
            r_end = int(from_to.group(2))
            # Exclude assessment years (2015-2030) from rank differentials
            if not (2015 <= r_start <= 2030 or 2015 <= r_end <= 2030):
                diff = r_start - r_end  # Positive is improvement
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="RANK_CHANGE",
                        metric="rank_diff",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        claimed_value=diff,
                        unit="ranks",
                        verification_notes=f"From rank {r_start} to {r_end}",
                    )
                )

        # Qualitative rank movement patterns without specific integers:
        if not claims and inst_name:
            improv_match = re.search(r"\b(improved|rose|climbed|advanced|gained|rank improvement|positive rank movement)\b", sent, re.IGNORECASE)
            decline_match = re.search(r"\b(declined|dropped|fell|lost|rank decline|negative rank movement)\b", sent, re.IGNORECASE)
            unchanged_match = re.search(r"\b(unchanged|retained|same rank)\b", sent, re.IGNORECASE)
            if improv_match:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="RANK_CHANGE",
                        metric="rank_improvement",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        claimed_value=None,
                        qualitative_direction="improved",
                        unit="ranks",
                        verification_notes="Qualitative rank improvement assertion",
                    )
                )
            elif decline_match:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="RANK_CHANGE",
                        metric="rank_improvement",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        claimed_value=None,
                        qualitative_direction="declined",
                        unit="ranks",
                        verification_notes="Qualitative rank decline assertion",
                    )
                )
            elif unchanged_match:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="RANK_CHANGE",
                        metric="rank_improvement",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        claimed_value=None,
                        qualitative_direction="unchanged",
                        unit="ranks",
                        verification_notes="Qualitative rank unchanged assertion",
                    )
                )

        return claims

    def _extract_bullet_list_claims(
        self,
        text: str,
        known_institutions: Dict[str, str],
    ) -> List[NumericalClaim]:
        """
        Extracts contextual claims from bullet lists following directional headings
        (e.g. '* **Institutions with Rank Improvement:**', '* **Identified Gainers:**').
        """
        claims = []
        lines = text.split("\n")
        current_direction = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            line_lower = line_str.lower()
            if any(h in line_lower for h in ("rank improvement", "institutions that improved", "gainers", "top improvers", "positive rank movement")):
                current_direction = "improved"
                continue
            elif any(h in line_lower for h in ("rank decline", "institutions that declined", "decliners", "negative rank movement")):
                current_direction = "declined"
                continue
            elif any(h in line_lower for h in ("unchanged ranks", "retained rank")):
                current_direction = "unchanged"
                continue
            elif line_str.startswith("#") or line_str.startswith("**Data Notes") or line_str.startswith("**Sample Size"):
                current_direction = None

            if current_direction and re.match(r"^[\*\-\+]\s+", line_str):
                clean_bullet = re.sub(r"^[\*\-\+]\s+", "", line_str).strip()
                clean_bullet = re.sub(r"\*\*|\*", "", clean_bullet).strip()
                inst_name, inst_uid = self._find_institution_in_text(clean_bullet, known_institutions)
                if inst_name:
                    claims.append(
                        NumericalClaim(
                            claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                            claim_text=line_str,
                            statement=f"{inst_name} showed rank {current_direction}",
                            claim_type="RANK_CHANGE",
                            metric="rank_improvement",
                            institution_name=inst_name,
                            institution_uid=inst_uid,
                            claimed_value=None,
                            qualitative_direction=current_direction,
                            unit="ranks",
                            verification_notes=f"Contextual bullet claim: rank {current_direction}",
                        )
                    )

        return claims

    def _extract_comparisons(
        self,
        sent: str,
        known_institutions: Dict[str, str],
    ) -> List[NumericalClaim]:
        """
        Extracts qualitative comparative assertions (e.g. 'State A outperformed State B').
        """
        claims = []
        comp_match = re.search(
            r"\b([A-Z][a-zA-Z\s,]+?)\s+(outperformed|performed better than|demonstrated higher|surpassed)\s+([A-Z][a-zA-Z\s,]+?)\b",
            sent,
            re.IGNORECASE,
        )
        if comp_match:
            ent1 = comp_match.group(1).strip()
            ent2 = comp_match.group(3).strip()
            ent1 = re.sub(r"^[,\s]+|[,\s]+$", "", ent1)
            ent2 = re.sub(r"^[,\s]+|[,\s]+$", "", ent2)
            if len(ent1) >= 3 and len(ent2) >= 3:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="INSTITUTION_COMPARISON",
                        comparison_entities=[ent1, ent2],
                        qualitative_direction="better",
                        metric="average_score",
                        claimed_value=None,
                        verification_notes=f"Qualitative comparison: {ent1} outperformed {ent2}",
                    )
                )
        return claims

    def _extract_superlatives(
        self,
        sent: str,
        known_institutions: Dict[str, str],
    ) -> List[NumericalClaim]:
        """
        Extracts qualitative superlative assertions (e.g. 'highest RPC', 'top performer').
        """
        claims = []
        inst_name, inst_uid = self._find_institution_in_text(sent, known_institutions)
        if inst_name:
            sent_lower = sent.lower()
            if "highest research" in sent_lower or "highest rpc" in sent_lower:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="METRIC_VALUE",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        metric="rpc",
                        qualitative_direction="highest",
                        claimed_value=None,
                        verification_notes="Qualitative claim: highest research performance score (RPC)",
                    )
                )
            elif "highest overall" in sent_lower or "highest score" in sent_lower or "top performer" in sent_lower or "ranked first" in sent_lower:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="RANK_VALUE",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        metric="score",
                        qualitative_direction="highest",
                        claimed_value=None,
                        verification_notes="Qualitative claim: highest overall score / top performer",
                    )
                )
        return claims

    def _extract_correlations(self, sent: str) -> List[NumericalClaim]:
        """
        Extracts correlation assertions and coefficients.
        """
        claims = []
        # Patterns like: "correlation of 0.72", "correlation between X and Y was 0.72", "r = 0.85"
        corr_match = re.search(r"\b(?:correlation|coefficient|r\b)[^0-9\n]{0,60}?\b([+-]?0?\.\d+)\b", sent, re.IGNORECASE)
        if corr_match:
            coeff = float(corr_match.group(1))
            claims.append(
                NumericalClaim(
                    claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                    claim_text=sent,
                    claim_type="CORRELATION",
                    metric="correlation",
                    claimed_value=coeff,
                    unit="coefficient",
                    verification_notes=f"Claimed correlation coefficient: {coeff}",
                )
            )
        return claims

    def _extract_metric_scores(
        self,
        sent: str,
        known_institutions: Dict[str, str],
    ) -> List[NumericalClaim]:
        """
        Extracts metric scores (TLR, RPC, GO, composite score).
        Specific parameters take precedence over generic score verbs.
        """
        claims = []
        inst_name, inst_uid = self._find_institution_in_text(sent, known_institutions)
        claimed_numbers: Set[float] = set()

        # Check specific parameters first, generic score last
        ordered_metrics = [
            ("rpc", self.METRICS["rpc"]),
            ("tlr", self.METRICS["tlr"]),
            ("go", self.METRICS["go"]),
            ("oi", self.METRICS["oi"]),
            ("perception", self.METRICS["perception"]),
            ("research_sfc", self.METRICS["research_sfc"]),
            ("research_qnr", self.METRICS["research_qnr"]),
            ("research_qlr", self.METRICS["research_qlr"]),
            ("score", self.METRICS["score"]),
        ]

        # Clean out cohort rank references like 'top 10' so they don't break parameter score matching
        clean_sent = re.sub(r"\b(?:top|first)\s+\d+\b", "cohort", sent, flags=re.IGNORECASE)

        for metric_key, aliases in ordered_metrics:
            for alias in aliases:
                p1 = rf"\b{re.escape(alias)}\b[^0-9\n]{{1,60}}?(\d{{1,3}}\.\d{{1,4}}|\d{{2,3}})\b"
                p2 = rf"\b(\d{{1,3}}\.\d{{1,4}})\s*(?:marks?|points?)?\s*(?:in|for)?\s*\b{re.escape(alias)}\b"

                for pattern in (p1, p2):
                    matches = re.finditer(pattern, clean_sent, re.IGNORECASE)
                    for m in matches:
                        try:
                            val = float(m.group(1))
                            if 0.0 <= val <= 100.0:
                                # If this number was already claimed by a specific metric, skip generic score
                                if val in claimed_numbers and metric_key == "score":
                                    continue
                                claimed_numbers.add(val)
                                claims.append(
                                    NumericalClaim(
                                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                                        claim_text=sent,
                                        claim_type="METRIC_VALUE",
                                        metric=metric_key,
                                        institution_name=inst_name,
                                        institution_uid=inst_uid,
                                        claimed_value=round(val, 4),
                                        unit="marks",
                                        verification_notes=f"Claimed {metric_key.upper()} value: {val}",
                                    )
                                )
                        except ValueError:
                            pass
        return claims

    def _extract_static_ranks(
        self,
        sent: str,
        known_institutions: Dict[str, str],
    ) -> List[NumericalClaim]:
        """
        Extracts static rank positions (e.g. "ranked #1", "rank 3").
        """
        claims = []
        inst_name, inst_uid = self._find_institution_in_text(sent, known_institutions)

        # Patterns like: "rank 1", "ranked #2", "Ranked 4th", "position 1"
        matches = re.finditer(r"\b(?:ranked|rank|position)\s*(?:#|no\.?)?\s*(\d+)(?:st|nd|rd|th)?\b", sent, re.IGNORECASE)
        for m in matches:
            val = int(m.group(1))
            if 1 <= val <= 500:
                claims.append(
                    NumericalClaim(
                        claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                        claim_text=sent,
                        claim_type="RANK_VALUE",
                        metric="rank",
                        institution_name=inst_name,
                        institution_uid=inst_uid,
                        claimed_value=val,
                        unit="rank",
                        verification_notes=f"Claimed rank: {val}",
                    )
                )
        return claims

    def _extract_counts(self, sent: str) -> List[NumericalClaim]:
        """
        Extracts counts of institutions, samples, or cohorts.
        """
        claims = []
        # Patterns like: "14 institutions", "sample size of 8 institutions", "10 colleges"
        pattern = r"\b(\d+)\s+(?:institutions?|colleges?|universities?|entities?|cohorts?)\b"
        matches = re.finditer(pattern, sent, re.IGNORECASE)
        for m in matches:
            count = int(m.group(1))
            # Ignore calendar years misparsed as counts
            if 2000 <= count <= 2040:
                continue
            claims.append(
                NumericalClaim(
                    claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                    claim_text=sent,
                    claim_type="COUNT",
                    metric="count",
                    claimed_value=count,
                    unit="entities",
                    verification_notes=f"Claimed count: {count}",
                )
            )
        return claims

    def _extract_table_claims(
        self,
        text: str,
        known_institutions: Dict[str, str],
        execution_result: Optional[ExecutionResult] = None,
    ) -> List[NumericalClaim]:
        """
        Extracts typed numerical claims directly from Markdown tables.
        Handles both:
        1. Metric-by-Row layouts: column 0 is metric, remaining columns are entities (e.g. Tamil Nadu, Karnataka).
        2. Entity-by-Row layouts: column 0 is entity (institution/state), other columns are metrics (Rank, Score, etc.).
        Filters divider rows and ignores header numbers (e.g. 'Top 50') as counts.
        """
        table_claims: List[NumericalClaim] = []
        if "|" not in text:
            return table_claims

        lines = text.splitlines()
        table_blocks: List[List[str]] = []
        current_block: List[str] = []

        for line in lines:
            s_line = line.strip()
            if s_line.startswith("|") and s_line.endswith("|") and len(s_line) >= 3:
                current_block.append(s_line)
            else:
                if len(current_block) >= 2:
                    table_blocks.append(current_block)
                current_block = []
        if len(current_block) >= 2:
            table_blocks.append(current_block)

        known_states = {
            "tamil nadu", "karnataka", "maharashtra", "delhi", "kerala",
            "uttar pradesh", "west bengal", "gujarat", "punjab", "telangana",
            "andhra pradesh", "rajasthan", "madhya pradesh", "odisha", "bihar",
            "assam", "haryana", "jharkhand", "himachal pradesh", "goa", "chandigarh"
        }

        category_from_exec = None
        year_from_exec = None
        if execution_result and execution_result.metadata:
            category_from_exec = execution_result.metadata.category
            year_from_exec = execution_result.metadata.year

        for block in table_blocks:
            header_cells = [c.strip() for c in block[0].split("|")[1:-1]]
            if not header_cells:
                continue

            data_rows = []
            for r in block[1:]:
                cells = [c.strip() for c in r.split("|")[1:-1]]
                if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                    continue
                data_rows.append(cells)

            if not data_rows:
                continue

            first_header = header_cells[0].lower()
            remaining_headers = [h.strip() for h in header_cells[1:]]

            # Detect Metric-by-Row layout
            is_metric_by_row = False
            if first_header in ("metric", "parameter", "indicator", "statistic", "measure"):
                is_metric_by_row = True
            elif any(h.lower() in known_states for h in remaining_headers):
                is_metric_by_row = True
            elif any(h.lower() in known_institutions for h in remaining_headers):
                is_metric_by_row = True

            if is_metric_by_row:
                for row_cells in data_rows:
                    if len(row_cells) < 2:
                        continue
                    raw_metric_label = row_cells[0]
                    norm_metric, stat_type, cohort_sig = self._parse_metric_label(raw_metric_label)

                    for col_idx, entity_name in enumerate(remaining_headers, start=1):
                        if col_idx >= len(row_cells):
                            break
                        val_str = row_cells[col_idx].replace(",", "").strip()
                        num_val = self._parse_table_cell_number(val_str)
                        if num_val is None:
                            continue

                        ent_lower = entity_name.lower()
                        state_val = entity_name if ent_lower in known_states else None
                        inst_name = None
                        inst_uid = None
                        if not state_val:
                            inst_name, inst_uid = self._find_institution_in_text(entity_name, known_institutions)
                            if not inst_name:
                                inst_name = entity_name

                        c_type: ClaimType = "AGGREGATE_STATISTIC" if state_val else "METRIC_VALUE"
                        if norm_metric == "rank":
                            c_type = "RANK_VALUE"
                        elif any(k in raw_metric_label.lower() for k in ("distinct", "top", "count", "institutions")):
                            c_type = "COUNT"

                        table_claims.append(
                            NumericalClaim(
                                claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                                claim_text=f"| {raw_metric_label} | {entity_name} | {val_str} |",
                                claim_type=c_type,
                                metric=norm_metric,
                                statistic_type=stat_type,
                                institution_name=inst_name,
                                institution_uid=inst_uid,
                                state=state_val,
                                category=category_from_exec,
                                year=year_from_exec,
                                value=num_val,
                                claimed_value=num_val,
                                unit="count" if c_type == "COUNT" else ("ranks" if c_type == "RANK_VALUE" else "marks"),
                                verification_notes=f"Table extracted: {entity_name} {raw_metric_label} = {num_val}",
                            )
                        )
            else:
                # Entity-by-Row layout
                entity_col_idx = 0
                for idx, h in enumerate(header_cells):
                    h_clean = h.lower().strip()
                    if any(k in h_clean for k in ("distinct", "total", "number", "count", "average", "median", "score", "rank", "rpc", "tlr")):
                        continue
                    if any(k in h_clean for k in ("category", "discipline", "institution", "institute", "college", "university", "state", "name", "entity")):
                        entity_col_idx = idx
                        break

                is_category_col = any(k in header_cells[entity_col_idx].lower() for k in ("category", "discipline"))

                for row_cells in data_rows:
                    if len(row_cells) <= entity_col_idx:
                        continue
                    raw_entity = row_cells[entity_col_idx].strip()
                    if not raw_entity:
                        continue

                    ent_lower = raw_entity.lower()
                    cat_val = raw_entity if is_category_col else category_from_exec
                    state_val = None if is_category_col else (raw_entity if ent_lower in known_states else None)
                    inst_name = None
                    inst_uid = None
                    if not is_category_col and not state_val:
                        inst_name, inst_uid = self._find_institution_in_text(raw_entity, known_institutions)
                        if not inst_name:
                            inst_name = raw_entity

                    for col_idx, raw_col_header in enumerate(header_cells):
                        if col_idx == entity_col_idx or col_idx >= len(row_cells):
                            continue
                        val_str = row_cells[col_idx].replace(",", "").strip()
                        num_val = self._parse_table_cell_number(val_str)
                        if num_val is None:
                            continue

                        norm_metric, stat_type, cohort_sig = self._parse_metric_label(raw_col_header)
                        c_type: ClaimType = "METRIC_VALUE"
                        if norm_metric == "rank":
                            c_type = "RANK_VALUE"
                        elif "improvement" in raw_col_header.lower() or "change" in raw_col_header.lower():
                            c_type = "RANK_CHANGE"
                        elif "count" in raw_col_header.lower() or "institutions" in raw_col_header.lower():
                            c_type = "COUNT"
                        elif state_val:
                            c_type = "AGGREGATE_STATISTIC"

                        table_claims.append(
                            NumericalClaim(
                                claim_id=f"claim_{uuid.uuid4().hex[:6]}",
                                claim_text=f"| {raw_entity} | {raw_col_header} | {val_str} |",
                                claim_type=c_type,
                                metric=norm_metric,
                                statistic_type=stat_type,
                                institution_name=inst_name,
                                institution_uid=inst_uid,
                                state=state_val,
                                category=cat_val or category_from_exec,
                                year=year_from_exec,
                                value=num_val,
                                claimed_value=num_val,
                                unit="count" if c_type == "COUNT" else ("ranks" if c_type == "RANK_VALUE" else "marks"),
                                verification_notes=f"Table extracted: {raw_entity} {raw_col_header} = {num_val}",
                            )
                        )

        return table_claims

    def _parse_table_cell_number(self, val_str: str) -> Optional[Union[float, int]]:
        """Parses a numerical value from a table cell, ignoring non-numeric prefixes/suffixes."""
        val_str = val_str.strip()
        val_str = re.sub(r"[*_`]", "", val_str)
        m = re.search(r"^[+-]?\d+(?:\.\d+)?$", val_str)
        if m:
            v = float(val_str)
            return int(v) if v.is_integer() else v
        m2 = re.search(r"^[#+-]?(\d+(?:\.\d+)?)\s*(?:marks?|pts?|%)?$", val_str)
        if m2:
            v = float(m2.group(1))
            return int(v) if v.is_integer() else v
        return None

    def _parse_metric_label(self, label: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Maps table header/row string to standardized (metric, stat_type, cohort_sig)."""
        label_lower = label.lower().strip()
        stat_type = None
        if "average" in label_lower or "mean" in label_lower:
            stat_type = "mean"
        elif "median" in label_lower:
            stat_type = "median"

        cohort_sig = None
        if "top 10" in label_lower:
            cohort_sig = "top_10"
        elif "top 50" in label_lower:
            cohort_sig = "top_50"
        elif "top 100" in label_lower:
            cohort_sig = "top_100"

        metric = "score"
        if "rpc" in label_lower:
            metric = "rpc"
        elif "tlr" in label_lower:
            metric = "tlr"
        elif "go" in label_lower:
            metric = "go"
        elif "oi" in label_lower:
            metric = "oi"
        elif "perception" in label_lower:
            metric = "perception"
        elif "rank" in label_lower:
            metric = "rank"
        elif any(k in label_lower for k in ("distinct", "institutions", "count")):
            metric = "count"

        return metric, stat_type, cohort_sig
