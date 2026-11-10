"""
Query Validator for NIRF Analytical Plans (Phase 3).
Performs independent, five-stage validation: Structural, Analytical API, Dataset,
Comparability (reusing 103 cohort rules), and Logical consistency.
"""

from typing import Dict, Any, List, Optional
import logging

from src.data.loader import get_data_loader
from src.data.comparability import get_comparability_validator
from src.analytics.utils import get_available_parameters_for_category, expand_institution_query
from src.query_engine.schemas import (
    QueryPlan,
    QueryValidationResult,
    ValidationStatus,
    AnalyticalOperation,
)

logger = logging.getLogger(__name__)

VALID_ANALYTICAL_FUNCTIONS = {
    "get_institution_trend",
    "get_rank_movement",
    "get_category_performance",
    "get_geographic_analysis",
    "get_parameter_correlation",
    "get_parameter_relationship",
    "get_multidimensional_performance",
    "get_score_distribution",
    "get_rank_transitions",
    "get_outlier_analysis",
    "get_category_evolution",
}

CATEGORY_ALIASES = {
    "research": "Research Institutions",
    "research institution": "Research Institutions",
    "research institutions": "Research Institutions",
    "research institute": "Research Institutions",
    "research institutes": "Research Institutions",
    "agriculture": "Agriculture & Allied Sectors",
    "agriculture & allied": "Agriculture & Allied Sectors",
    "agri": "Agriculture & Allied Sectors",
    "architecture": "Architecture & Planning",
    "planning": "Architecture & Planning",
    "architecture and planning": "Architecture & Planning",
    "state university": "State Public University",
    "state universities": "State Public University",
    "state public universities": "State Public University",
    "sdg": "Sustainable Development Goals (SDG)",
    "sustainable development goals": "Sustainable Development Goals (SDG)",
    "colleges": "College",
    "universities": "University",
    "engg": "Engineering",
    "pharma": "Pharmacy",
    "medicine": "Medical",
    "dentistry": "Dental",
}


class QueryValidator:
    """
    Validates QueryPlans against official dataset schema, analytical function signatures,
    institution entity registries, and the 103 cohort comparability rules.
    """

    def __init__(self) -> None:
        self.loader = get_data_loader()
        self.comp_validator = get_comparability_validator()

        self.available_categories = {c.lower(): c for c in self.loader.get_available_categories()}
        self.available_states = {s.lower(): s for s in self.loader.get_available_states()}
        self.available_years = set(self.loader.get_available_years())

    def validate(self, plan: QueryPlan) -> QueryValidationResult:
        """
        Executes comprehensive validation across structural, API, dataset, comparability,
        and logical criteria.

        Args:
            plan: The QueryPlan to validate.

        Returns:
            QueryValidationResult containing validity boolean, status, errors, warnings,
            and resolved entities.
        """
        errors: List[str] = []
        warnings: List[str] = []
        comparability_notes: List[str] = []
        resolved_entities: Dict[str, Any] = {
            "categories": [],
            "states": [],
            "institutions": [],
        }

        # 1. Structural Validation
        if plan.query_type == "unsupported":
            return QueryValidationResult(
                is_valid=False,
                status="UNSUPPORTED",
                warnings=[plan.unsupported_reason or "Requested analysis is unsupported by NIRF dataset."],
                validated_plan=plan,
            )

        if plan.query_type == "clarification_required":
            return QueryValidationResult(
                is_valid=False,
                status="CLARIFICATION_REQUIRED",
                warnings=[plan.clarification_message or "Clarification required from user."],
                validated_plan=plan,
            )

        if not plan.operations:
            errors.append("Query plan contains zero analytical operations.")
            return QueryValidationResult(
                is_valid=False,
                status="INVALID",
                errors=errors,
                validated_plan=plan,
            )

        # 2. Per-Operation Validation
        for op in plan.operations:
            op_errs, op_warns, op_notes, op_resolved = self._validate_operation(op)
            errors.extend(op_errs)
            warnings.extend(op_warns)
            comparability_notes.extend(op_notes)

            for k, v in op_resolved.items():
                if k in resolved_entities and isinstance(v, list):
                    resolved_entities[k].extend(v)
                else:
                    resolved_entities[k] = v

        # Deduplicate resolved entities
        for k in ["categories", "states"]:
            if k in resolved_entities and isinstance(resolved_entities[k], list):
                resolved_entities[k] = sorted(list(set(resolved_entities[k])))

        # Determine overall validation status
        if errors:
            status: ValidationStatus = "INVALID"
            is_valid = False
        elif any("Ambiguous institution" in w for w in warnings):
            status = "CLARIFICATION_REQUIRED"
            is_valid = False
        elif warnings:
            status = "VALID_WITH_WARNINGS"
            is_valid = True
        else:
            status = "VALID"
            is_valid = True

        return QueryValidationResult(
            is_valid=is_valid,
            status=status,
            errors=errors,
            warnings=warnings,
            comparability_notes=comparability_notes,
            resolved_entities=resolved_entities,
            validated_plan=plan,
        )

    def _validate_operation(
        self,
        op: AnalyticalOperation,
    ) -> tuple[List[str], List[str], List[str], Dict[str, Any]]:
        errors: List[str] = []
        warnings: List[str] = []
        comp_notes: List[str] = []
        resolved: Dict[str, Any] = {"categories": [], "states": [], "institutions": []}

        fn = op.function_name
        if fn not in VALID_ANALYTICAL_FUNCTIONS:
            errors.append(f"Function '{fn}' is not a valid Phase 2 analytical function.")
            return errors, warnings, comp_notes, resolved

        # Category Validation
        standard_category: Optional[str] = None
        if op.category:
            cat_clean = op.category.strip().lower()
            if cat_clean in CATEGORY_ALIASES:
                standard_category = CATEGORY_ALIASES[cat_clean]
                op.category = standard_category
                op.applied_defaults["category"] = standard_category
                resolved["categories"].append(standard_category)
            elif cat_clean in self.available_categories:
                standard_category = self.available_categories[cat_clean]
                op.category = standard_category  # Standardize
                resolved["categories"].append(standard_category)
            else:
                errors.append(f"Category '{op.category}' is not a valid NIRF category.")
        elif fn in ("get_geographic_analysis", "get_category_evolution"):
            # Geography and Category Evolution can operate without category
            pass
        else:
            # Operation was missing a category: infer from institution if available, or default to "Overall"
            inferred_cat = None
            if op.institution_names or op.institution_uids:
                inferred_cat = self._infer_institution_category(op.institution_names, op.institution_uids)
            if not inferred_cat:
                inferred_cat = "Overall"

            standard_category = inferred_cat
            op.category = inferred_cat
            op.applied_defaults["category"] = inferred_cat
            resolved["categories"].append(inferred_cat)
            warnings.append(f"No category specified; defaulted to '{inferred_cat}'.")

        # State Validation
        if op.states:
            std_states = []
            for st in op.states:
                st_clean = st.strip().lower()
                if st_clean in self.available_states:
                    std_states.append(self.available_states[st_clean])
                else:
                    warnings.append(f"State '{st}' not recognized in NIRF dataset.")
            op.states = std_states
            resolved["states"].extend(std_states)

        # Year & Temporal Logic
        if op.year:
            if op.year not in self.available_years:
                errors.append(f"Year {op.year} is outside NIRF dataset range (2017–2025).")

        if op.start_year and op.end_year:
            if op.start_year not in self.available_years:
                errors.append(f"Start year {op.start_year} is outside NIRF dataset range (2017–2025).")
            if op.end_year not in self.available_years:
                errors.append(f"End year {op.end_year} is outside NIRF dataset range (2017–2025).")
            if op.start_year > op.end_year:
                errors.append(f"Start year ({op.start_year}) cannot be greater than end year ({op.end_year}).")

        # Function-Specific Argument & Dataset Checks
        if fn == "get_institution_trend":
            if not op.institution_names and not op.institution_uids:
                errors.append("get_institution_trend requires at least one institution name or UID.")
            else:
                # Entity lookup
                inst_resolved, inst_warns = self._resolve_institutions(op.institution_names, op.institution_uids, standard_category)
                warnings.extend(inst_warns)
                resolved["institutions"].extend(inst_resolved)

            # Default years if omitted
            if not op.start_year:
                op.start_year = 2017
                op.applied_defaults["start_year"] = 2017
            if not op.end_year:
                op.end_year = 2025
                op.applied_defaults["end_year"] = 2025

        elif fn == "get_rank_movement":
            if not op.start_year:
                errors.append("get_rank_movement requires start_year.")
            if not op.end_year:
                op.end_year = 2025
                op.applied_defaults["end_year"] = 2025

        elif fn in ("get_category_performance", "get_score_distribution", "get_outlier_analysis", "get_parameter_correlation"):
            if not op.year:
                op.year = 2025
                op.applied_defaults["year"] = 2025

        elif fn == "get_parameter_relationship":
            if not op.year:
                op.year = 2025
                op.applied_defaults["year"] = 2025
            # Ensure two distinct parameters
            if not op.param_x or not op.param_y:
                if op.parameters and len(op.parameters) >= 2:
                    op.param_x = op.parameters[0]
                    op.param_y = op.parameters[1]
                else:
                    errors.append("get_parameter_relationship requires two parameters (param_x and param_y).")
            elif op.param_x.lower() == op.param_y.lower():
                errors.append(f"param_x and param_y must be distinct (got '{op.param_x}' for both).")

        elif fn == "get_multidimensional_performance":
            if not op.year:
                op.year = 2025
                op.applied_defaults["year"] = 2025
            if op.institution_names or op.institution_uids:
                inst_resolved, inst_warns = self._resolve_institutions(op.institution_names, op.institution_uids, standard_category)
                warnings.extend(inst_warns)
                resolved["institutions"].extend(inst_resolved)

        elif fn == "get_rank_transitions":
            if not op.start_year or not op.end_year:
                errors.append("get_rank_transitions requires both start_year and end_year.")

        elif fn == "get_category_evolution":
            if not op.start_year:
                op.start_year = 2017
                op.applied_defaults["start_year"] = 2017
            if not op.end_year:
                op.end_year = 2025
                op.applied_defaults["end_year"] = 2025

        # Top N positive check
        if op.top_n is not None and op.top_n <= 0:
            errors.append(f"top_n must be a positive integer (got {op.top_n}).")

        # Comparability Validation (reusing Phase 1 ComparabilityValidator)
        if standard_category and fn != "get_category_evolution":
            if op.year:
                comp_res = self.comp_validator.validate_single_cohort(
                    standard_category,
                    op.year,
                    requested_metrics=op.parameters or ([op.metric] if op.metric else None)
                )
                if not comp_res.is_comparable:
                    errors.extend(comp_res.errors)
                warnings.extend(comp_res.warnings)
                comp_notes.extend(comp_res.notes)

            elif op.start_year and op.end_year:
                years_list = [op.start_year, op.end_year]
                comp_res = self.comp_validator.validate_multi_year_comparison(
                    standard_category,
                    years_list,
                    requested_metrics=op.parameters or ([op.metric] if op.metric else None)
                )
                if not comp_res.is_comparable:
                    errors.extend(comp_res.errors)
                warnings.extend(comp_res.warnings)
                comp_notes.extend(comp_res.notes)

        return errors, warnings, comp_notes, resolved

    def _infer_institution_category(self, names: List[str], uids: List[str]) -> Optional[str]:
        """Infers the most appropriate NIRF category for an institution if none was specified."""
        df = self.loader.master_df
        found_categories: set[str] = set()
        for uid in uids:
            matches = df[df["institution_uid"].str.lower() == uid.strip().lower()]
            found_categories.update(matches["category"].dropna().unique())
        for name in names:
            for variant in expand_institution_query(name):
                matches = df[df["institute_name_std"].str.lower().str.contains(variant.lower(), na=False, regex=False)]
                found_categories.update(matches["category"].dropna().unique())
        if not found_categories:
            return None
        # Flagship category is "Overall"
        if "Overall" in found_categories:
            return "Overall"
        for pref in ["Engineering", "University", "College", "Management", "Pharmacy", "Medical"]:
            if pref in found_categories:
                return pref
        return sorted(list(found_categories))[0]

    def _resolve_institutions(
        self,
        names: List[str],
        uids: List[str],
        category: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Resolves institution names/acronyms to canonical records in master_df."""
        resolved = []
        warnings = []
        df = self.loader.master_df

        # Handle explicit UIDs
        for uid in uids:
            matches = df[df["institution_uid"].str.lower() == uid.strip().lower()]
            if not matches.empty:
                rec = matches.iloc[0]
                resolved.append({
                    "institution_uid": str(rec["institution_uid"]),
                    "institute_name_std": str(rec["institute_name_std"]),
                    "state": str(rec["state_std"]),
                })
            else:
                warnings.append(f"Institution UID '{uid}' not found in NIRF dataset.")

        # Handle names with acronym expansion
        for name in names:
            matched_uids = set()
            for variant in expand_institution_query(name):
                # Search name std
                m = df[df["institute_name_std"].str.lower().str.contains(variant.lower(), na=False, regex=False)]
                if category:
                    m_cat = m[m["category"].str.lower() == category.lower()]
                    if not m_cat.empty:
                        m = m_cat
                for _, r in m.drop_duplicates(subset=["institution_uid"]).iterrows():
                    matched_uids.add((str(r["institution_uid"]), str(r["institute_name_std"]), str(r["state_std"])))

            if len(matched_uids) == 1:
                u, n, s = list(matched_uids)[0]
                resolved.append({"institution_uid": u, "institute_name_std": n, "state": s})
            elif len(matched_uids) > 1:
                # Disambiguation needed
                cands = [f"{n} ({u}, {s})" for u, n, s in list(matched_uids)[:3]]
                warnings.append(f"Ambiguous institution name '{name}'. Matches: {', '.join(cands)}")
            else:
                warnings.append(f"Institution '{name}' not found in NIRF dataset.")

        return resolved, warnings


def get_query_validator() -> QueryValidator:
    """Returns singleton QueryValidator instance."""
    return QueryValidator()

