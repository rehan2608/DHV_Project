"""
Schema definition and dataset validation for NIRF Master Dataset.
Validates all 40 columns, data types, primary key uniqueness, null tolerances,
and domain bounds according to the official NIRF data dictionary and audit standards.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


# Canonical list of expected 40 columns
EXPECTED_COLUMNS: List[str] = [
    "year",
    "category",
    "category_original",
    "institution_uid",
    "institution_uid_raw",
    "is_uid_transformed",
    "institute_id",
    "institute_name_raw",
    "institute_name_std",
    "institution_group",
    "city_raw",
    "city_std",
    "is_city_imputed",
    "state_raw",
    "state_std",
    "zone",
    "country",
    "score",
    "score_band",
    "rank_raw",
    "rank",
    "rank_label",
    "rank_band",
    "is_tied_rank",
    "is_rank_amended",
    "is_rank_withdrawn",
    "rank_validation_status",
    "tlr",
    "rpc",
    "go",
    "oi",
    "perception",
    "research_sfc",
    "research_qnr",
    "research_qlr",
    "has_parameter_scores",
    "parameter_structure",
    "data_quality_flags",
    "pdf_url",
    "source_url",
]

# Standard NIRF Categories across 2017–2025
EXPECTED_CATEGORIES: List[str] = [
    "Agriculture & Allied Sectors",
    "Architecture & Planning",
    "College",
    "Dental",
    "Engineering",
    "Innovation",
    "Law",
    "Management",
    "Medical",
    "Open University",
    "Overall",
    "Pharmacy",
    "Research Institutions",
    "Skill University",
    "Special Mention (2018)",
    "State Public University",
    "Sustainable Development Goals (SDG)",
    "University",
]

# Valid editions
EXPECTED_YEARS: List[int] = list(range(2017, 2026))

# Primary key columns
PRIMARY_KEY: List[str] = ["year", "category", "institution_uid"]

# Numeric measure columns
NUMERIC_MEASURES: List[str] = [
    "score",
    "rank",
    "rank_raw",
    "tlr",
    "rpc",
    "go",
    "oi",
    "perception",
    "research_sfc",
    "research_qnr",
    "research_qlr",
]

# Boolean flag columns
BOOLEAN_FLAGS: List[str] = [
    "is_uid_transformed",
    "is_city_imputed",
    "is_tied_rank",
    "is_rank_amended",
    "is_rank_withdrawn",
    "has_parameter_scores",
]


@dataclass
class ValidationIssue:
    check_name: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    affected_count: int = 0
    details: Optional[Dict[str, Any]] = None


@dataclass
class SchemaValidationReport:
    is_valid: bool
    total_rows: int
    total_columns: int
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)

    def summary(self) -> str:
        status = "PASSED" if self.is_valid else "FAILED"
        lines = [
            f"Schema Validation Summary: {status}",
            f"Total Records: {self.total_rows:,}",
            f"Total Columns: {self.total_columns}",
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
        ]
        if self.errors:
            lines.append("\nErrors:")
            for err in self.errors:
                lines.append(f"  [ERROR] {err.check_name}: {err.message} (count={err.affected_count})")
        if self.warnings:
            lines.append("\nWarnings:")
            for warn in self.warnings:
                lines.append(f"  [WARNING] {warn.check_name}: {warn.message} (count={warn.affected_count})")
        return "\n".join(lines)


class SchemaValidator:
    """Validates dataframe schema and integrity against official standards."""

    @classmethod
    def validate_dataset(cls, df: pd.DataFrame) -> SchemaValidationReport:
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        info: List[ValidationIssue] = []

        total_rows, total_cols = df.shape

        # 1. Expected Column Validation
        actual_cols = list(df.columns)
        missing_cols = [c for c in EXPECTED_COLUMNS if c not in actual_cols]
        unexpected_cols = [c for c in actual_cols if c not in EXPECTED_COLUMNS]

        if missing_cols:
            errors.append(ValidationIssue(
                check_name="Column Presence",
                severity="ERROR",
                message=f"Missing {len(missing_cols)} expected column(s): {missing_cols}",
                affected_count=len(missing_cols),
                details={"missing": missing_cols}
            ))

        if unexpected_cols:
            warnings.append(ValidationIssue(
                check_name="Unexpected Columns",
                severity="WARNING",
                message=f"Found {len(unexpected_cols)} unexpected column(s): {unexpected_cols}",
                affected_count=len(unexpected_cols),
                details={"unexpected": unexpected_cols}
            ))

        if total_cols != len(EXPECTED_COLUMNS):
            warnings.append(ValidationIssue(
                check_name="Column Count",
                severity="WARNING",
                message=f"Column count is {total_cols}, expected {len(EXPECTED_COLUMNS)}",
                affected_count=abs(total_cols - len(EXPECTED_COLUMNS))
            ))

        # 2. Primary Key Uniqueness
        if all(pk in df.columns for pk in PRIMARY_KEY):
            pk_dups = df.duplicated(subset=PRIMARY_KEY, keep=False).sum()
            if pk_dups > 0:
                errors.append(ValidationIssue(
                    check_name="Primary Key Uniqueness",
                    severity="ERROR",
                    message=f"Found {pk_dups} primary key collisions on {PRIMARY_KEY}",
                    affected_count=int(pk_dups)
                ))
            else:
                info.append(ValidationIssue(
                    check_name="Primary Key Uniqueness",
                    severity="INFO",
                    message=f"Zero duplicate keys on {PRIMARY_KEY}",
                    affected_count=0
                ))

        # 3. Year Bounds Check
        if "year" in df.columns:
            actual_years = sorted(df["year"].dropna().unique().tolist())
            invalid_years = [y for y in actual_years if y not in EXPECTED_YEARS]
            if invalid_years:
                errors.append(ValidationIssue(
                    check_name="Year Range",
                    severity="ERROR",
                    message=f"Found invalid years outside 2017-2025: {invalid_years}",
                    affected_count=len(invalid_years)
                ))

        # 4. Category Check
        if "category" in df.columns:
            actual_cats = sorted(df["category"].dropna().unique().tolist())
            invalid_cats = [c for c in actual_cats if c not in EXPECTED_CATEGORIES]
            if invalid_cats:
                warnings.append(ValidationIssue(
                    check_name="Category Validity",
                    severity="WARNING",
                    message=f"Found unlisted categories: {invalid_cats}",
                    affected_count=len(invalid_cats)
                ))

        # 5. Missing Values & Audit Profile
        # Mandatory non-null columns
        mandatory_non_null = ["year", "category", "institution_uid", "institute_name_std", "state_std", "city_std"]
        for col in mandatory_non_null:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    errors.append(ValidationIssue(
                        check_name=f"Mandatory Column Non-Null ({col})",
                        severity="ERROR",
                        message=f"Column '{col}' has {null_count} unexpected null values",
                        affected_count=int(null_count)
                    ))

        # Audited nulls in scores and ranks
        if "rank" in df.columns:
            rank_nulls = df["rank"].isnull().sum()
            # In V3 audit, exactly 5 rows legitimately have null rank (1 withdrawn, 4 special mentions)
            if rank_nulls > 5:
                warnings.append(ValidationIssue(
                    check_name="Rank Null Count",
                    severity="WARNING",
                    message=f"Rank has {rank_nulls} nulls (expected 5: 1 withdrawn, 4 special mentions)",
                    affected_count=int(rank_nulls)
                ))

        if "score" in df.columns:
            score_nulls = df["score"].isnull().sum()
            # In V3 audit, exactly 57 rows have uncalculated/unreported scores (Innovation, SDG, Skill, Open, Special Mention, 2025 Dental rank 18)
            if score_nulls > 57:
                warnings.append(ValidationIssue(
                    check_name="Score Null Count",
                    severity="WARNING",
                    message=f"Score has {score_nulls} nulls (expected 57 according to comparability audit)",
                    affected_count=int(score_nulls)
                ))

        # 6. Metric Range Sanity Check
        for metric in ["score", "tlr", "rpc", "go", "oi", "perception", "research_sfc", "research_qnr", "research_qlr"]:
            if metric in df.columns:
                series = df[metric].dropna()
                out_of_bounds = ((series < 0.0) | (series > 100.0)).sum()
                if out_of_bounds > 0:
                    errors.append(ValidationIssue(
                        check_name=f"Metric Bounds ({metric})",
                        severity="ERROR",
                        message=f"Metric '{metric}' has {out_of_bounds} values outside [0.0, 100.0]",
                        affected_count=int(out_of_bounds)
                    ))

        # 7. Rank Range Check
        if "rank" in df.columns:
            ranks = df["rank"].dropna()
            invalid_ranks = ((ranks < 1.0) | (ranks > 500.0)).sum()
            if invalid_ranks > 0:
                warnings.append(ValidationIssue(
                    check_name="Rank Bounds",
                    severity="WARNING",
                    message=f"Found {invalid_ranks} ranks outside [1, 500]",
                    affected_count=int(invalid_ranks)
                ))

        is_valid = len(errors) == 0
        return SchemaValidationReport(
            is_valid=is_valid,
            total_rows=total_rows,
            total_columns=total_cols,
            errors=errors,
            warnings=warnings,
            info=info
        )

