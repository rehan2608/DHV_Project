"""
Comparability Validation Engine for NIRF Longitudinal Analysis.
Enforces the 103 cohort rules, metric schema boundaries, cohort depth changes,
and parameter structure restrictions to prevent invalid comparisons.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
import logging

from src.data.loader import get_data_loader

logger = logging.getLogger(__name__)


@dataclass
class ComparabilityCheckResult:
    """Result of a comparability validation check."""
    is_comparable: bool
    status: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metric_schema: Optional[str] = None
    recommended_rank_cutoff: Optional[int] = None

    def summary(self) -> str:
        lines = [
            f"Comparability Status: {self.status} (Allowed: {self.is_comparable})"
        ]
        if self.errors:
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  - {e}")
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.notes:
            lines.append("Notes:")
            for n in self.notes:
                lines.append(f"  - {n}")
        if self.recommended_rank_cutoff:
            lines.append(f"Recommended common rank cutoff: Top {self.recommended_rank_cutoff}")
        return "\n".join(lines)


class ComparabilityValidator:
    """
    Validates analytical queries against official NIRF comparability rules.
    Prevents combining incompatible schemas, out-of-range years, or invalid metrics.
    """

    def __init__(self, rules_df: Optional[pd.DataFrame] = None) -> None:
        if rules_df is None:
            self.rules_df = get_data_loader().comparability_df
        else:
            self.rules_df = rules_df

    def get_cohort_rule(self, category: str, year: int) -> Optional[pd.Series]:
        """Retrieves rule record for given category and year."""
        matches = self.rules_df[
            (self.rules_df["category"].str.lower() == category.strip().lower()) &
            (self.rules_df["year"] == year)
        ]
        if len(matches) > 0:
            return matches.iloc[0]
        return None

    def validate_single_cohort(
        self,
        category: str,
        year: int,
        requested_metrics: Optional[List[str]] = None
    ) -> ComparabilityCheckResult:
        """
        Validates whether a single (category, year) cohort exists and supports requested metrics.
        """
        rule = self.get_cohort_rule(category, year)
        if rule is None:
            return ComparabilityCheckResult(
                is_comparable=False,
                status="Non-Existent Cohort",
                errors=[f"Category '{category}' was not published or evaluated in year {year}."]
            )

        warnings: List[str] = []
        errors: List[str] = []
        notes: List[str] = [str(rule["comparability_notes"])]
        metric_schema = str(rule["metric_schema"])
        score_avail = bool(rule["score_available"])
        param_avail = bool(rule["parameter_scores_available"])

        if requested_metrics:
            for m in requested_metrics:
                m_clean = m.strip().lower()
                if m_clean == "score" and not score_avail:
                    errors.append(
                        f"Overall composite score is NOT available for '{category}' in {year} "
                        f"(Rank-Order Only category)."
                    )
                if m_clean in ["tlr", "rpc", "go"] and not param_avail:
                    errors.append(
                        f"Standard parameter '{m.upper()}' is not published for '{category}' in {year}."
                    )
                if m_clean in ["tlr", "rpc", "go"] and metric_schema == "Research Specific (3 Research + 2 Common)":
                    errors.append(
                        f"Category '{category}' in {year} uses Research Specific Schema "
                        f"(SFC, QNR, QLR) and does NOT have standard '{m.upper()}' parameter."
                    )
                if m_clean.startswith("research_") and metric_schema != "Research Specific (3 Research + 2 Common)":
                    errors.append(
                        f"Research metric '{m}' is only available for 'Research Institutions' (2021–2025)."
                    )

        status = str(rule["comparability_status"])
        is_comparable = len(errors) == 0

        return ComparabilityCheckResult(
            is_comparable=is_comparable,
            status=status,
            warnings=warnings,
            errors=errors,
            notes=notes,
            metric_schema=metric_schema
        )

    def validate_multi_year_comparison(
        self,
        category: str,
        years: List[int],
        requested_metrics: Optional[List[str]] = None
    ) -> ComparabilityCheckResult:
        """
        Validates longitudinal comparisons across multiple years for a given category.
        Checks start year, cohort depth expansions, schema consistency, and score availability.
        """
        if not years:
            return ComparabilityCheckResult(
                is_comparable=False,
                status="Invalid Request",
                errors=["At least one year must be specified."]
            )

        sorted_years = sorted(years)
        errors: List[str] = []
        warnings: List[str] = []
        notes: List[str] = []
        schemas: List[str] = []
        max_ranks: List[int] = []

        for yr in sorted_years:
            rule = self.get_cohort_rule(category, yr)
            if rule is None:
                errors.append(f"Category '{category}' was not published or evaluated in {yr}.")
                continue

            schemas.append(str(rule["metric_schema"]))
            max_ranks.append(int(rule["maximum_published_rank"]))
            notes.append(f"{yr}: {rule['comparability_notes']}")

            # Check valid comparison start year
            valid_start = int(rule["valid_comparison_start_year"])
            if yr < valid_start:
                errors.append(
                    f"Category '{category}' has valid comparison start year {valid_start}; {yr} is invalid."
                )

        if errors:
            return ComparabilityCheckResult(
                is_comparable=False,
                status="Incomparable Cohorts",
                errors=errors,
                notes=notes
            )

        # Schema consistency
        unique_schemas = set(schemas)
        if len(unique_schemas) > 1:
            errors.append(
                f"Incompatible metric schemas across years {sorted_years} for '{category}': {unique_schemas}"
            )
            return ComparabilityCheckResult(
                is_comparable=False,
                status="Incompatible Schemas",
                errors=errors,
                notes=notes
            )

        schema = schemas[0]

        # Check requested metrics against schema
        if requested_metrics:
            for m in requested_metrics:
                m_clean = m.strip().lower()
                if m_clean == "score" and schema == "Rank Only":
                    errors.append(
                        f"Category '{category}' publishes Rank Only. Score comparison is invalid."
                    )
                if m_clean in ["tlr", "rpc", "go"] and schema != "Standard (5 Parameters)":
                    errors.append(
                        f"Metric '{m.upper()}' is not supported by schema '{schema}' for '{category}'."
                    )

        if errors:
            return ComparabilityCheckResult(
                is_comparable=False,
                status="Metric Incompatible",
                errors=errors,
                notes=notes,
                metric_schema=schema
            )

        # Check for depth expansions (e.g., Top 50 to Top 100)
        recommended_cutoff: Optional[int] = None
        if len(set(max_ranks)) > 1:
            recommended_cutoff = min(max_ranks)
            warnings.append(
                f"Cohort depth expanded across {sorted_years} (published depths: {max_ranks}). "
                f"For strict longitudinal consistency, restrict comparison to Top {recommended_cutoff} institutions."
            )

        # Longitudinal score warning: NIRF scores are normalized annually
        if requested_metrics and any(m.lower() == "score" for m in requested_metrics):
            warnings.append(
                "Longitudinal score caution: NIRF annual scores reflect year-specific cohort normalization. "
                "Rank improvement is the official longitudinal indicator."
            )

        status = "Comparability Requires Caution" if warnings else "Fully Comparable"

        return ComparabilityCheckResult(
            is_comparable=True,
            status=status,
            warnings=warnings,
            errors=[],
            notes=notes,
            metric_schema=schema,
            recommended_rank_cutoff=recommended_cutoff
        )


def get_comparability_validator() -> ComparabilityValidator:
    """Returns a ComparabilityValidator instance."""
    return ComparabilityValidator()

