"""
Synthetic Generalization Fixture Generator for NIRF Assistant Audit (Phase 6.1.1).
Deterministically generates 60 synthetic analytical test cases using fixed seed (seed=42),
covering numerical, structural, and claim-quality permutations without reusing benchmark entities.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any


def generate_synthetic_cases(seed: int = 42) -> List[Dict[str, Any]]:
    random.seed(seed)
    cases = []

    # -------------------------------------------------------------------------
    # PART 1: NUMERICAL CASES (20 Cases)
    # -------------------------------------------------------------------------
    # NUM-01: Positive float score within rounding tolerance (actual=75.324, claimed=75.32) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_01",
        "category": "NUMERICAL",
        "description": "Positive float score within rounding tolerance",
        "op_data": {"rankings": [{"institution_uid": "SYN-01", "institution_name": "Apex Institute", "score": 75.324}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Apex Institute", "metric": "score", "value": 75.32},
        "expected_status": "VERIFIED"
    })

    # NUM-02: Float score exceeding tolerance (actual=75.324, claimed=76.00) -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_NUM_02",
        "category": "NUMERICAL",
        "description": "Float score exceeding tolerance discrepancy",
        "op_data": {"rankings": [{"institution_uid": "SYN-01", "institution_name": "Apex Institute", "score": 75.324}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Apex Institute", "metric": "score", "value": 76.00},
        "expected_status": "CONFLICTING"
    })

    # NUM-03: Exact integer rank match (actual=14, claimed=14) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_03",
        "category": "NUMERICAL",
        "description": "Exact integer rank match",
        "op_data": {"rankings": [{"institution_uid": "SYN-02", "institution_name": "Beacon University", "rank": 14}]},
        "claim": {"claim_type": "RANK_VALUE", "institution_name": "Beacon University", "metric": "rank", "value": 14},
        "expected_status": "VERIFIED"
    })

    # NUM-04: Integer rank mismatch (actual=14, claimed=15) -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_NUM_04",
        "category": "NUMERICAL",
        "description": "Integer rank off-by-one discrepancy",
        "op_data": {"rankings": [{"institution_uid": "SYN-02", "institution_name": "Beacon University", "rank": 14}]},
        "claim": {"claim_type": "RANK_VALUE", "institution_name": "Beacon University", "metric": "rank", "value": 15},
        "expected_status": "CONFLICTING"
    })

    # NUM-05: Rank improvement positive match (actual=18, claimed=+18) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_05",
        "category": "NUMERICAL",
        "description": "Positive rank improvement match",
        "op_data": {"gainers": [{"institution_uid": "SYN-03", "institute_name_std": "Cascade College", "rank_improvement": 18}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Cascade College", "value": 18},
        "expected_status": "VERIFIED"
    })

    # NUM-06: Rank deterioration negative match (actual=-12, claimed=-12) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_06",
        "category": "NUMERICAL",
        "description": "Rank decline negative match",
        "op_data": {"gainers": [{"institution_uid": "SYN-04", "institute_name_std": "Delta Institute", "rank_improvement": -12}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Delta Institute", "value": -12},
        "expected_status": "VERIFIED"
    })

    # NUM-07: Rank direction reversal (actual=+12, claimed=-12) -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_NUM_07",
        "category": "NUMERICAL",
        "description": "Rank movement direction reversed",
        "op_data": {"gainers": [{"institution_uid": "SYN-04", "institute_name_std": "Delta Institute", "rank_improvement": 12}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Delta Institute", "value": -12},
        "expected_status": "CONFLICTING"
    })

    # NUM-08: Positive correlation coefficient match (r=0.7412, claimed=0.74) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_08",
        "category": "NUMERICAL",
        "description": "Positive Pearson correlation match within tolerance",
        "op_data": {"regression": {"pearson_r": 0.7412}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Correlation was 0.74", "value": 0.74},
        "expected_status": "VERIFIED"
    })

    # NUM-09: Negative correlation coefficient match (r=-0.582, claimed=-0.58) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_09",
        "category": "NUMERICAL",
        "description": "Negative Pearson correlation match within tolerance",
        "op_data": {"regression": {"pearson_r": -0.582}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Correlation was -0.58", "value": -0.58},
        "expected_status": "VERIFIED"
    })

    # NUM-10: Correlation coefficient discrepancy (r=0.7412, claimed=0.45) -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_NUM_10",
        "category": "NUMERICAL",
        "description": "Correlation coefficient mismatch",
        "op_data": {"regression": {"pearson_r": 0.7412}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Correlation was 0.45", "value": 0.45},
        "expected_status": "CONFLICTING"
    })

    # NUM-11: Regression R-squared match (r2=0.549, claimed=0.55) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_11",
        "category": "NUMERICAL",
        "description": "Regression R-squared match",
        "op_data": {"regression": {"r_squared": 0.549}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "R-squared was 0.55", "value": 0.55},
        "expected_status": "VERIFIED"
    })

    # NUM-12: Zero-imputation violation (metric missing/None in data, claimed 0.0) -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_NUM_12",
        "category": "NUMERICAL",
        "description": "Missing parameter claimed as zero",
        "op_data": {"rankings": [{"institution_uid": "SYN-05", "institution_name": "Echo College", "score": 62.0, "rpc": None}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Echo College", "metric": "rpc", "value": 0.0},
        "expected_status": "CONFLICTING"
    })

    # NUM-13: Legitimate zero count match (count=0) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_13",
        "category": "NUMERICAL",
        "description": "Legitimate zero count in cohort",
        "op_data": {"counts": 0},
        "claim": {"claim_type": "COUNT", "value": 0},
        "expected_status": "VERIFIED"
    })

    # NUM-14: Cohort sample size integer match (n=47) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_14",
        "category": "NUMERICAL",
        "description": "Cohort sample size match",
        "op_data": {"sample_size": 47},
        "claim": {"claim_type": "COUNT", "value": 47},
        "expected_status": "VERIFIED"
    })

    # NUM-15: Cohort sample size mismatch (n=47, claimed 50) -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_15",
        "category": "NUMERICAL",
        "description": "Cohort count mismatch against evidence",
        "op_data": {"sample_size": 47},
        "claim": {"claim_type": "COUNT", "value": 50},
        "expected_status": "UNVERIFIED"
    })

    # NUM-16: Missing score parameter (score is NaN in data, claimed 80.0) -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_16",
        "category": "NUMERICAL",
        "description": "Missing parameter claimed with positive value",
        "op_data": {"rankings": [{"institution_uid": "SYN-06", "institution_name": "Foxtrot Institute", "score": float("nan")}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Foxtrot Institute", "metric": "score", "value": 80.0},
        "expected_status": "UNVERIFIED"
    })

    # NUM-17: Spearman rho match (rho=0.684, claimed 0.68) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_17",
        "category": "NUMERICAL",
        "description": "Spearman rank correlation match",
        "op_data": {"regression": {"spearman_rho": 0.684}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Spearman was 0.68", "value": 0.68},
        "expected_status": "VERIFIED"
    })

    # NUM-18: Regression slope match (slope=0.385, claimed 0.38) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_18",
        "category": "NUMERICAL",
        "description": "Regression slope match",
        "op_data": {"regression": {"slope": 0.385}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Slope was 0.38", "value": 0.38},
        "expected_status": "VERIFIED"
    })

    # NUM-19: Parameter value within decimal tolerance (actual=88.45, claimed=88.42) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_NUM_19",
        "category": "NUMERICAL",
        "description": "Small rounding delta <= 0.05",
        "op_data": {"rankings": [{"institution_uid": "SYN-07", "institution_name": "Golf Academy", "parameters": {"tlr": 88.45}}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Golf Academy", "metric": "tlr", "value": 88.42},
        "expected_status": "VERIFIED"
    })

    # NUM-20: Parameter value exceeding decimal tolerance (actual=88.45, claimed=88.35) -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_NUM_20",
        "category": "NUMERICAL",
        "description": "Rounding delta > 0.05 discrepancy",
        "op_data": {"rankings": [{"institution_uid": "SYN-07", "institution_name": "Golf Academy", "parameters": {"tlr": 88.45}}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Golf Academy", "metric": "tlr", "value": 88.35},
        "expected_status": "CONFLICTING"
    })

    # -------------------------------------------------------------------------
    # PART 2: STRUCTURAL CASES (20 Cases)
    # -------------------------------------------------------------------------
    # STRUC-01: Nested scatter points parameter matching (param_x='rpc', point x=65.4) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_01",
        "category": "STRUCTURAL",
        "description": "Scatter plot point X coordinate mapped to param_x",
        "op_data": {
            "param_x": "rpc", "param_y": "tlr",
            "points": [{"institution_uid": "SYN-08", "institute_name_std": "Hotel University", "x": 65.4, "y": 78.2}]
        },
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Hotel University", "metric": "rpc", "value": 65.4},
        "expected_status": "VERIFIED"
    })

    # STRUC-02: Nested scatter points parameter matching Y (param_y='tlr', point y=78.2) -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_02",
        "category": "STRUCTURAL",
        "description": "Scatter plot point Y coordinate mapped to param_y",
        "op_data": {
            "param_x": "rpc", "param_y": "tlr",
            "points": [{"institution_uid": "SYN-08", "institute_name_std": "Hotel University", "x": 65.4, "y": 78.2}]
        },
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Hotel University", "metric": "tlr", "value": 78.2},
        "expected_status": "VERIFIED"
    })

    # STRUC-03: State aggregate average score match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_03",
        "category": "STRUCTURAL",
        "description": "State aggregate average score match",
        "op_data": {"states_analysis": [{"state": "Goa", "average_score": 58.75, "average_rpc": 42.10}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Goa", "metric": "average_score", "value": 58.75},
        "expected_status": "VERIFIED"
    })

    # STRUC-04: State aggregate average RPC match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_04",
        "category": "STRUCTURAL",
        "description": "State aggregate average RPC match",
        "op_data": {"states_analysis": [{"state": "Goa", "average_score": 58.75, "average_rpc": 42.10}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Goa", "metric": "rpc", "value": 42.10},
        "expected_status": "VERIFIED"
    })

    # STRUC-05: State aggregate mismatch -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_STRUC_05",
        "category": "STRUCTURAL",
        "description": "State aggregate value discrepancy",
        "op_data": {"states_analysis": [{"state": "Goa", "average_score": 58.75, "average_rpc": 42.10}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Goa", "metric": "average_score", "value": 64.00},
        "expected_status": "CONFLICTING"
    })

    # STRUC-06: State distinct institution count match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_06",
        "category": "STRUCTURAL",
        "description": "State distinct institution count match",
        "op_data": {"states_analysis": [{"state": "Kerala", "distinct_institutions": 19}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Kerala", "metric": "distinct_institutions", "value": 19},
        "expected_status": "VERIFIED"
    })

    # STRUC-07: State top 10 density match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_07",
        "category": "STRUCTURAL",
        "description": "State top 10 institutions density match",
        "op_data": {"states_analysis": [{"state": "Kerala", "top_10_institutions": 3}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Kerala", "metric": "top_10", "value": 3},
        "expected_status": "VERIFIED"
    })

    # STRUC-08: Head-to-head comparison state metrics match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_08",
        "category": "STRUCTURAL",
        "description": "Head-to-head comparison state metric extraction",
        "op_data": {"head_to_head_comparison": {"metrics": [{"state": "Punjab", "average_score": 52.40}]}},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Punjab", "metric": "score", "value": 52.40},
        "expected_status": "VERIFIED"
    })

    # STRUC-09: Bivariate medians indexing X median match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_09",
        "category": "STRUCTURAL",
        "description": "Generic medians indexing for param_x",
        "op_data": {"param_x": "rpc", "param_y": "tlr", "medians": {"x_median": 63.85, "y_median": 81.20}},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "metric": "rpc", "statistic_type": "median", "value": 63.85},
        "expected_status": "VERIFIED"
    })

    # STRUC-10: Bivariate medians indexing Y median match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_10",
        "category": "STRUCTURAL",
        "description": "Generic medians indexing for param_y",
        "op_data": {"param_x": "rpc", "param_y": "tlr", "medians": {"x_median": 63.85, "y_median": 81.20}},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "metric": "tlr", "statistic_type": "median", "value": 81.20},
        "expected_status": "VERIFIED"
    })

    # STRUC-11: Cohort score distribution mean match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_11",
        "category": "STRUCTURAL",
        "description": "Distribution summary mean score match",
        "op_data": {"distribution": {"mean": 55.45, "median": 52.10}},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "metric": "mean", "value": 55.45},
        "expected_status": "VERIFIED"
    })

    # STRUC-12: Cohort score distribution median match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_12",
        "category": "STRUCTURAL",
        "description": "Distribution summary median score match",
        "op_data": {"distribution": {"mean": 55.45, "median": 52.10}},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "metric": "median", "value": 52.10},
        "expected_status": "VERIFIED"
    })

    # STRUC-13: Empty operation data dictionary handling -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_13",
        "category": "STRUCTURAL",
        "description": "Empty operation data dictionary safely handled",
        "op_data": {},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "India Institute", "metric": "score", "value": 70.0},
        "expected_status": "UNVERIFIED"
    })

    # STRUC-14: Missing optional parameters dictionary in rankings -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_14",
        "category": "STRUCTURAL",
        "description": "Ranking record without parameters dict handles missing gracefully",
        "op_data": {"rankings": [{"institution_uid": "SYN-09", "institution_name": "Juliet College", "score": 60.0}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Juliet College", "metric": "rpc", "value": 50.0},
        "expected_status": "UNVERIFIED"
    })

    # STRUC-15: Unexpected result structure (arbitrary keys) safe handling -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_15",
        "category": "STRUCTURAL",
        "description": "Unexpected keys in analytical result handled safely",
        "op_data": {"custom_payload": [{"name": "Kilo Univ", "val": 99.0}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Kilo Univ", "metric": "score", "value": 99.0},
        "expected_status": "UNVERIFIED"
    })

    # STRUC-16: Transitions rank difference match -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_16",
        "category": "STRUCTURAL",
        "description": "Transitions movement diff match",
        "op_data": {"transitions": [{"institution_uid": "SYN-10", "institution_name": "Lima College", "rank_diff": 15}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Lima College", "value": 15},
        "expected_status": "VERIFIED"
    })

    # STRUC-17: Institution start_rank and end_rank differential calculation -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_17",
        "category": "STRUCTURAL",
        "description": "Calculates rank_diff from start_rank and end_rank if rank_improvement absent",
        "op_data": {"gainers": [{"institution_uid": "SYN-11", "institute_name_std": "Mike Institute", "start_rank": 50, "end_rank": 35}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Mike Institute", "value": 15},
        "expected_status": "VERIFIED"
    })

    # STRUC-18: Outliers record indexing -> VERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_18",
        "category": "STRUCTURAL",
        "description": "Outliers record indexing and metric matching",
        "op_data": {"outliers": [{"institution_uid": "SYN-12", "institution_name": "November Univ", "score": 45.20}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "November Univ", "metric": "score", "value": 45.20},
        "expected_status": "VERIFIED"
    })

    # STRUC-19: Unrecognized state in state aggregate claim -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_19",
        "category": "STRUCTURAL",
        "description": "Unrecognized state in aggregate claim",
        "op_data": {"states_analysis": [{"state": "Assam", "average_score": 48.0}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "NonExistentState", "metric": "average_score", "value": 48.0},
        "expected_status": "UNVERIFIED"
    })

    # STRUC-20: Missing metric in valid state record -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_STRUC_20",
        "category": "STRUCTURAL",
        "description": "Non-existent metric for existing state record",
        "op_data": {"states_analysis": [{"state": "Assam", "average_score": 48.0}]},
        "claim": {"claim_type": "AGGREGATE_STATISTIC", "state": "Assam", "metric": "non_existent_param", "value": 48.0},
        "expected_status": "UNVERIFIED"
    })

    # -------------------------------------------------------------------------
    # PART 3: CLAIM-QUALITY CASES (20 Cases)
    # -------------------------------------------------------------------------
    # QUAL-01: Correct claim matching all fields -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_01",
        "category": "CLAIM_QUALITY",
        "description": "Fully grounded and accurate claim",
        "op_data": {"rankings": [{"institution_uid": "SYN-13", "institution_name": "Oscar Institute", "score": 82.15}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Oscar Institute", "metric": "score", "value": 82.15},
        "expected_status": "VERIFIED"
    })

    # QUAL-02: Correct number but wrong institution -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_QUAL_02",
        "category": "CLAIM_QUALITY",
        "description": "Number matches another institution in cohort, but claimed institution has different score",
        "op_data": {"rankings": [
            {"institution_uid": "SYN-14", "institution_name": "Papa University", "score": 88.0},
            {"institution_uid": "SYN-15", "institution_name": "Quebec College", "score": 72.0}
        ]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Quebec College", "metric": "score", "value": 88.0},
        "expected_status": "CONFLICTING"
    })

    # QUAL-03: Unsupported causal claim attached to correlation -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_QUAL_03",
        "category": "CLAIM_QUALITY",
        "description": "Causal leap 'causes' attached to valid correlation coefficient",
        "op_data": {"regression": {"pearson_r": 0.65}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "RPC causes TLR with r = 0.65", "value": 0.65},
        "expected_status": "CONFLICTING"
    })

    # QUAL-04: Unsupported causal phrase 'drives' attached to correlation -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_QUAL_04",
        "category": "CLAIM_QUALITY",
        "description": "Causal leap 'drives' attached to valid correlation coefficient",
        "op_data": {"regression": {"pearson_r": 0.65}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Research performance drives teaching scores with r = 0.65", "value": 0.65},
        "expected_status": "CONFLICTING"
    })

    # QUAL-05: Non-causal mathematical association accepted -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_05",
        "category": "CLAIM_QUALITY",
        "description": "Grounded non-causal association description",
        "op_data": {"regression": {"pearson_r": 0.65}},
        "claim": {"claim_type": "CORRELATION", "claim_text": "Observed positive mathematical association with r = 0.65", "value": 0.65},
        "expected_status": "VERIFIED"
    })

    # QUAL-06: Institution not present in evidence result -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_06",
        "category": "CLAIM_QUALITY",
        "description": "Institution absent from analytical evidence",
        "op_data": {"rankings": [{"institution_uid": "SYN-16", "institution_name": "Romeo Academy", "score": 70.0}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Sierra University", "metric": "score", "value": 70.0},
        "expected_status": "UNVERIFIED"
    })

    # QUAL-07: Claim specifies no numerical value -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_07",
        "category": "CLAIM_QUALITY",
        "description": "Qualitative assertion with null value",
        "op_data": {"gainers": [{"institution_uid": "SYN-17", "institute_name_std": "Tango College", "rank_improvement": 10}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Tango College", "value": None},
        "expected_status": "UNVERIFIED"
    })

    # QUAL-08: Ambiguous institution query matching multiple institutions -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_08",
        "category": "CLAIM_QUALITY",
        "description": "Ambiguous abbreviation 'IIT' with multiple IITs in cohort",
        "op_data": {"rankings": [
            {"institution_uid": "U-IIT1", "institution_name": "IIT Bombay", "score": 85.0},
            {"institution_uid": "U-IIT2", "institution_name": "IIT Madras", "score": 85.0}
        ]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "IIT", "metric": "score", "value": 85.0},
        "expected_status": "UNVERIFIED"
    })

    # QUAL-09: Unambiguous abbreviation matching single institution in cohort -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_09",
        "category": "CLAIM_QUALITY",
        "description": "Abbreviation 'IIT Bombay' unambiguously matching single record",
        "op_data": {"rankings": [
            {"institution_uid": "U-IIT1", "institution_name": "Indian Institute of Technology Bombay", "score": 85.0},
            {"institution_uid": "U-NIT1", "institution_name": "National Institute of Technology Surathkal", "score": 65.0}
        ]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "IIT Bombay", "metric": "score", "value": 85.0},
        "expected_status": "VERIFIED"
    })

    # QUAL-10: IIM acronym expansion -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_10",
        "category": "CLAIM_QUALITY",
        "description": "IIM acronym correctly expanded to Indian Institute of Management",
        "op_data": {"rankings": [
            {"institution_uid": "U-IIMK", "institution_name": "Indian Institute of Management Kozhikode", "score": 78.4}
        ]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "IIM Kozhikode", "metric": "score", "value": 78.4},
        "expected_status": "VERIFIED"
    })

    # QUAL-11: NIT acronym expansion -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_11",
        "category": "CLAIM_QUALITY",
        "description": "NIT acronym correctly expanded to National Institute of Technology",
        "op_data": {"rankings": [
            {"institution_uid": "U-NITW", "institution_name": "National Institute of Technology Warangal", "score": 67.2}
        ]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "NIT Warangal", "metric": "score", "value": 67.2},
        "expected_status": "VERIFIED"
    })

    # QUAL-12: Complete lack of analytical evidence -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_12",
        "category": "CLAIM_QUALITY",
        "description": "Claim evaluated against null execution result",
        "op_data": None,
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Uniform Univ", "metric": "score", "value": 80.0},
        "expected_status": "UNVERIFIED"
    })

    # QUAL-13: Multiple operations preserving operation context -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_13",
        "category": "CLAIM_QUALITY",
        "description": "Record matched from specific multi-operation data",
        "op_data": {"rankings": [{"institution_uid": "SYN-18", "institution_name": "Victor Institute", "score": 79.5}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Victor Institute", "metric": "score", "value": 79.5},
        "expected_status": "VERIFIED"
    })

    # QUAL-14: Positive rank direction preserved -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_14",
        "category": "CLAIM_QUALITY",
        "description": "Reported improvement of +20 matches actual rank_improvement = 20",
        "op_data": {"gainers": [{"institution_uid": "SYN-19", "institute_name_std": "Whiskey College", "rank_improvement": 20}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Whiskey College", "value": 20},
        "expected_status": "VERIFIED"
    })

    # QUAL-15: Declining institution falsely claimed as improving -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_QUAL_15",
        "category": "CLAIM_QUALITY",
        "description": "Decline of -15 claimed as improvement of +15",
        "op_data": {"gainers": [{"institution_uid": "SYN-20", "institute_name_std": "Xray Academy", "rank_improvement": -15}]},
        "claim": {"claim_type": "RANK_CHANGE", "institution_name": "Xray Academy", "value": 15},
        "expected_status": "CONFLICTING"
    })

    # QUAL-16: Duplicate claim values correctly reconciled -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_16",
        "category": "CLAIM_QUALITY",
        "description": "Duplicate claim text for same institution and metric",
        "op_data": {"rankings": [{"institution_uid": "SYN-21", "institution_name": "Yankee University", "score": 84.0}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Yankee University", "metric": "score", "value": 84.0},
        "expected_status": "VERIFIED"
    })

    # QUAL-17: Generic score alias matching specific parameter score -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_17",
        "category": "CLAIM_QUALITY",
        "description": "Score alias matching rpc in parameters dictionary",
        "op_data": {"rankings": [{"institution_uid": "SYN-22", "institution_name": "Zulu Institute", "parameters": {"rpc": 89.2}}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Zulu Institute", "metric": "rpc", "value": 89.2},
        "expected_status": "VERIFIED"
    })

    # QUAL-18: Non-existent parameter requested for institution -> UNVERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_18",
        "category": "CLAIM_QUALITY",
        "description": "Parameter not present in institution parameters dictionary",
        "op_data": {"rankings": [{"institution_uid": "SYN-22", "institution_name": "Zulu Institute", "parameters": {"rpc": 89.2}}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "Zulu Institute", "metric": "unknown_param", "value": 89.2},
        "expected_status": "UNVERIFIED"
    })

    # QUAL-19: Case insensitive matching for institution name -> VERIFIED
    cases.append({
        "case_id": "SYNTH_QUAL_19",
        "category": "CLAIM_QUALITY",
        "description": "Case insensitive matching for institution name",
        "op_data": {"rankings": [{"institution_uid": "SYN-23", "institution_name": "alpha omega institute", "score": 77.0}]},
        "claim": {"claim_type": "METRIC_VALUE", "institution_name": "ALPHA OMEGA INSTITUTE", "metric": "score", "value": 77.0},
        "expected_status": "VERIFIED"
    })

    # QUAL-20: Integer rank comparison strict equality -> CONFLICTING
    cases.append({
        "case_id": "SYNTH_QUAL_20",
        "category": "CLAIM_QUALITY",
        "description": "Integer rank strict equality prevents fractional tolerance acceptance",
        "op_data": {"rankings": [{"institution_uid": "SYN-24", "institution_name": "Beta Gamma College", "rank": 10}]},
        "claim": {"claim_type": "RANK_VALUE", "institution_name": "Beta Gamma College", "metric": "rank", "value": 11},
        "expected_status": "CONFLICTING"
    })

    return cases


def main():
    cases = generate_synthetic_cases(seed=42)
    output_dir = Path("tests/synthetic_fixtures")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "synthetic_generalization_cases.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    print(f"Generated {len(cases)} synthetic test cases at {out_file}")


if __name__ == "__main__":
    main()

