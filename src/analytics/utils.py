"""
Shared utilities, serializable metadata builders, and parameter schema resolvers
for the NIRF Analytics Engine.
"""

from typing import Any, Dict, List, Optional, Union
import re
import numpy as np
import pandas as pd

from src.config import STANDARD_PARAMETERS, RESEARCH_PARAMETERS
from src.data.loader import get_data_loader


ACRONYM_EXPANSIONS = {
    r"\biit\b": "indian institute of technology",
    r"\bnit\b": "national institute of technology",
    r"\biim\b": "indian institute of management",
    r"\baiims\b": "all india institute of medical sciences",
    r"\bnlu\b": "national law university",
    r"\biiit\b": "indian institute of information technology",
    r"\biisc\b": "indian institute of science",
    r"\bniper\b": "national institute of pharmaceutical education and research",
    r"\biiser\b": "indian institute of science education and research",
}


def expand_institution_query(query: str) -> List[str]:
    """Expands common institutional acronyms (IIT, NIT, IIM, etc.) to full standardized names."""
    q_clean = query.strip().lower()
    variants = [q_clean]
    for pat, expansion in ACRONYM_EXPANSIONS.items():
        if re.search(pat, q_clean):
            variants.append(re.sub(pat, expansion, q_clean))
    return variants


def shorten_institution_name(name: str) -> str:
    """Shortens verbose official institution names to universally recognized acronyms for clean visualizations."""
    if not name or not isinstance(name, str):
        return str(name) if name else ""
    s = name.strip()

    # Specific known institutions
    s = re.sub(r"Indian Institute of Technology\s*\(\s*Banaras Hindu University\s*\)\s*Varanasi", "IIT (BHU) Varanasi", s, flags=re.I)
    s = re.sub(r"Indian Institute of Technology\s+Banaras Hindu University", "IIT BHU", s, flags=re.I)
    s = re.sub(r"National Institute of Technology\s+Tiruchirappalli", "NIT Trichy", s, flags=re.I)
    s = re.sub(r"National Institute of Technology\s+Karnataka[,\s]+Surathkal", "NIT Surathkal", s, flags=re.I)
    s = re.sub(r"Indian Institute of Science(?!\s+Education)", "IISc Bangalore", s, flags=re.I)
    s = re.sub(r"Birla Institute of Technology\s*(&|and)\s*Science(\s*-\s*Pilani)?", "BITS Pilani", s, flags=re.I)
    s = re.sub(r"Jawaharlal Nehru University", "JNU New Delhi", s, flags=re.I)
    s = re.sub(r"Banaras Hindu University", "BHU Varanasi", s, flags=re.I)
    s = re.sub(r"Jamia Millia Islamia([,\s]+New\s+Delhi)?", "JMI New Delhi", s, flags=re.I)
    s = re.sub(r"Post\s*Graduate Institute of Medical Education\s*(&|and)\s*Research", "PGIMER Chandigarh", s, flags=re.I)
    s = re.sub(r"Jawaharlal Institute of Post\s*Graduate Medical Education\s*(&|and)\s*Research", "JIPMER Puducherry", s, flags=re.I)
    s = re.sub(r"All India Institute of Medical Sciences([,\s]+New\s+Delhi)?", "AIIMS New Delhi", s, flags=re.I)
    s = re.sub(r"Vellore Institute of Technology", "VIT Vellore", s, flags=re.I)
    s = re.sub(r"Manipal Academy of Higher Education([,\s]+Manipal)?", "MAHE Manipal", s, flags=re.I)
    s = re.sub(r"Aligarh Muslim University", "AMU Aligarh", s, flags=re.I)
    s = re.sub(r"Christian Medical College([,\s]+Vellore)?", "CMC Vellore", s, flags=re.I)
    s = re.sub(r"Delhi Technological University", "DTU Delhi", s, flags=re.I)

    # Common prefixes
    s = re.sub(r"Indian Institute of Technology[,\s]*", "IIT ", s, flags=re.I)
    s = re.sub(r"National Institute of Technology[,\s]*", "NIT ", s, flags=re.I)
    s = re.sub(r"Indian Institute of Information Technology[,\s]*", "IIIT ", s, flags=re.I)
    s = re.sub(r"Indian Institute of Management[,\s]*", "IIM ", s, flags=re.I)
    s = re.sub(r"Indian Institute of Science Education and Research[,\s]*", "IISER ", s, flags=re.I)
    s = re.sub(r"National Law University[,\s]*", "NLU ", s, flags=re.I)
    s = re.sub(r"National Institute of Pharmaceutical Education and Research[,\s]*", "NIPER ", s, flags=re.I)

    # Clean redundant spaces and punctuation
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r",\s*$", "", s).strip()
    return s


def matches_institution_name(name_val: str, targets: List[str]) -> bool:
    """Checks if an institution name matches any of the target query strings or their acronym expansions."""
    if not isinstance(name_val, str):
        return False
    name_lower = name_val.lower()
    all_targets = []
    for t in targets:
        all_targets.extend(expand_institution_query(t))
    return any(target in name_lower for target in all_targets)


def clean_numeric(val: Any) -> Optional[Union[int, float]]:
    """Converts numpy / pandas numeric types to standard Python int/float, mapping NaN to None."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return round(float(val), 4)
    return None


def get_available_parameters_for_category(category: str, year: int) -> List[str]:
    """
    Returns the list of valid analytical parameters for a given category and year
    based on the official comparability rules.
    """
    loader = get_data_loader()
    comp_df = loader.comparability_df
    matches = comp_df[
        (comp_df["category"].str.lower() == category.strip().lower()) &
        (comp_df["year"] == year)
    ]
    if matches.empty:
        return []

    schema = str(matches.iloc[0]["metric_schema"])
    if schema == "Standard (5 Parameters)":
        return list(STANDARD_PARAMETERS)
    elif schema == "Research Specific (3 Research + 2 Common)":
        return list(RESEARCH_PARAMETERS)
    else:  # Rank Only
        return []


def build_analysis_metadata(
    query_type: str,
    calculation_method: str,
    records_considered: int,
    valid_observations: int,
    category: Optional[str] = None,
    years: Optional[List[int]] = None,
    parameters: Optional[List[str]] = None,
    missing_data_info: Optional[Dict[str, Any]] = None,
    comparability_status: str = "Fully Comparable",
    warnings: Optional[List[str]] = None,
    limitations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Builds a consistent, JSON-serializable analytical metadata dictionary."""
    return {
        "query_type": query_type,
        "category": category,
        "years": years,
        "parameters": parameters or [],
        "records_considered": int(records_considered),
        "valid_observations": int(valid_observations),
        "excluded_observations": int(records_considered - valid_observations),
        "missing_data_info": missing_data_info or {},
        "comparability_status": comparability_status,
        "warnings": warnings or [],
        "limitations": limitations or [],
        "calculation_method": calculation_method,
    }
