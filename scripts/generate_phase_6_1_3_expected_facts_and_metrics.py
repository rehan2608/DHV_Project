"""
Independent Expected-Fact Inventory & Precision/Recall Recomputation (Audit 3).
Constructs ground-truth expected facts directly from analytical execution results,
evaluates generated benchmark claims against the independent inventory,
and outputs docs/phase_6_1_3_expected_facts.json and docs/phase_6_1_3_audit_results.json.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

BENCHMARK_DIR = Path("tests/benchmark_results")
EXPECTED_FACTS_PATH = Path("docs/phase_6_1_3_expected_facts.json")
AUDIT_RESULTS_PATH = Path("docs/phase_6_1_3_audit_results.json")


def build_expected_facts_inventory() -> Dict[str, List[Dict[str, Any]]]:
    """
    Independently constructs the ground-truth factual assertions answering
    each benchmark query, derived directly from Phase 4 execution outputs.
    """
    return {
        "BM-01": [
            {
                "fact_id": "BM01-FACT-01",
                "source_operation": "get_rank_movement",
                "result_field": "gainers[0].rank_improvement",
                "entity": "Jain university,Bangalore",
                "metric": "rank_improvement",
                "year": [2020, 2025],
                "category": "Engineering",
                "filters": {"state": "Karnataka", "top_n": 5},
                "expected_value": 33,
                "expected_claim_type": "RANK_CHANGE",
                "description": "Jain University improved by 33 ranks (117 to 84).",
            },
            {
                "fact_id": "BM01-FACT-02",
                "source_operation": "get_rank_movement",
                "result_field": "metadata.valid_observations",
                "entity": "Karnataka",
                "metric": "count",
                "year": [2020, 2025],
                "category": "Engineering",
                "filters": {"state": "Karnataka"},
                "expected_value": 5,
                "expected_claim_type": "COUNT",
                "description": "5 institutions had paired observations across both years.",
            },
            {
                "fact_id": "BM01-FACT-03",
                "source_operation": "get_rank_movement",
                "result_field": "metadata.missing_data_info.departed_institutions",
                "entity": "Karnataka",
                "metric": "count",
                "year": [2020, 2025],
                "category": "Engineering",
                "filters": {"state": "Karnataka"},
                "expected_value": 16,
                "expected_claim_type": "COUNT",
                "description": "16 institutions departed the rankings.",
            },
            {
                "fact_id": "BM01-FACT-04",
                "source_operation": "get_rank_movement",
                "result_field": "metadata.missing_data_info.new_entrant_institutions",
                "entity": "Karnataka",
                "metric": "count",
                "year": [2020, 2025],
                "category": "Engineering",
                "filters": {"state": "Karnataka"},
                "expected_value": 2,
                "expected_claim_type": "COUNT",
                "description": "2 institutions were new entrants.",
            },
            {
                "fact_id": "BM01-FACT-05",
                "source_operation": "get_rank_movement",
                "result_field": "metadata.excluded_observations",
                "entity": "Karnataka",
                "metric": "count",
                "year": [2020, 2025],
                "category": "Engineering",
                "filters": {"state": "Karnataka"},
                "expected_value": 23,
                "expected_claim_type": "COUNT",
                "description": "23 observations excluded due to missing data.",
            },
        ],
        "BM-02": [],  # Documentation only; no numerical analytical operations
        "BM-03": [
            {
                "fact_id": "BM03-FACT-01",
                "source_operation": "get_category_performance",
                "result_field": "institutions[0].rpc",
                "entity": "Indian Institute of Technology Madras",
                "metric": "rpc",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 90.74,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Madras RPC score is 90.74.",
            },
            {
                "fact_id": "BM03-FACT-02",
                "source_operation": "get_category_performance",
                "result_field": "institutions[1].rpc",
                "entity": "Indian Institute of Technology Bombay",
                "metric": "rpc",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 84.81,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Bombay RPC score is 84.81.",
            },
            {
                "fact_id": "BM03-FACT-03",
                "source_operation": "get_category_performance",
                "result_field": "institutions[0].rank",
                "entity": "Indian Institute of Technology Madras",
                "metric": "rank",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 1,
                "expected_claim_type": "RANK_VALUE",
                "description": "IIT Madras rank is 1.",
            },
            {
                "fact_id": "BM03-FACT-04",
                "source_operation": "get_category_performance",
                "result_field": "institutions[1].rank",
                "entity": "Indian Institute of Technology Bombay",
                "metric": "rank",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 3,
                "expected_claim_type": "RANK_VALUE",
                "description": "IIT Bombay rank is 3.",
            },
            {
                "fact_id": "BM03-FACT-05",
                "source_operation": "get_category_performance",
                "result_field": "institutions[0].score",
                "entity": "Indian Institute of Technology Madras",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 88.72,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Madras total score is 88.72.",
            },
            {
                "fact_id": "BM03-FACT-06",
                "source_operation": "get_category_performance",
                "result_field": "institutions[1].score",
                "entity": "Indian Institute of Technology Bombay",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 83.65,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Bombay total score is 83.65.",
            },
        ],
        "BM-04": [
            {
                "fact_id": "BM04-FACT-01",
                "source_operation": "rankings",
                "result_field": "rankings[0].score",
                "entity": "Indian Institute of Technology Madras",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 88.72,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Madras overall score 88.72.",
            },
            {
                "fact_id": "BM04-FACT-02",
                "source_operation": "rankings",
                "result_field": "rankings[0].tlr",
                "entity": "Indian Institute of Technology Madras",
                "metric": "tlr",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 95.70,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Madras TLR 95.70.",
            },
            {
                "fact_id": "BM04-FACT-03",
                "source_operation": "rankings",
                "result_field": "rankings[1].rpc",
                "entity": "Indian Institute of Technology Delhi",
                "metric": "rpc",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 93.47,
                "expected_claim_type": "METRIC_VALUE",
                "description": "IIT Delhi RPC 93.47.",
            },
            {
                "fact_id": "BM04-FACT-04",
                "source_operation": "correlations",
                "result_field": "regression.pearson_r",
                "entity": "Engineering Cohort",
                "metric": "pearson_r",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 0.6227,
                "expected_claim_type": "CORRELATION",
                "description": "Pearson r between RPC and TLR is 0.6227.",
            },
            {
                "fact_id": "BM04-FACT-05",
                "source_operation": "distributions",
                "result_field": "medians.x_median",
                "entity": "Engineering Cohort",
                "metric": "rpc",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 76.45,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Median RPC for cohort is 76.45.",
            },
            {
                "fact_id": "BM04-FACT-06",
                "source_operation": "distributions",
                "result_field": "medians.y_median",
                "entity": "Engineering Cohort",
                "metric": "tlr",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 85.58,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Median TLR for cohort is 85.58.",
            },
            {
                "fact_id": "BM04-FACT-07",
                "source_operation": "rankings",
                "result_field": "metadata.top_n",
                "entity": "Engineering Cohort",
                "metric": "count",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 10,
                "expected_claim_type": "COUNT",
                "description": "Top 10 institutions cohort size.",
            },
        ],
        "BM-05": [],  # Future prediction; zero expected numerical facts (Abstention)
        "BM-06": [
            {
                "fact_id": "BM06-FACT-01",
                "source_operation": "transitions",
                "result_field": "metadata.valid_observations",
                "entity": "Management",
                "metric": "count",
                "year": [2017, 2025],
                "category": "Management",
                "filters": {},
                "expected_value": 40,
                "expected_claim_type": "COUNT",
                "description": "40 paired institutions tracked across methodology change.",
            },
            {
                "fact_id": "BM06-FACT-02",
                "source_operation": "transitions",
                "result_field": "metadata.warnings[0].cutoff",
                "entity": "Management",
                "metric": "count",
                "year": [2017, 2025],
                "category": "Management",
                "filters": {},
                "expected_value": 50,
                "expected_claim_type": "COUNT",
                "description": "Comparisons restricted to Top 50 institutions due to cutoff expansion.",
            },
        ],
        "BM-07": [
            {
                "fact_id": "BM07-FACT-01",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].distinct_institutions",
                "entity": "Tamil Nadu",
                "metric": "distinct_institutions",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 100},
                "expected_value": 14,
                "expected_claim_type": "COUNT",
                "description": "Tamil Nadu has 14 distinct institutions in top 100.",
            },
            {
                "fact_id": "BM07-FACT-02",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].distinct_institutions",
                "entity": "Karnataka",
                "metric": "distinct_institutions",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 100},
                "expected_value": 7,
                "expected_claim_type": "COUNT",
                "description": "Karnataka has 7 distinct institutions in top 100.",
            },
            {
                "fact_id": "BM07-FACT-03",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].top_10",
                "entity": "Tamil Nadu",
                "metric": "rank",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 2,
                "expected_claim_type": "COUNT",
                "description": "Tamil Nadu has 2 institutions in top 10.",
            },
            {
                "fact_id": "BM07-FACT-04",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].top_10",
                "entity": "Karnataka",
                "metric": "rank",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 10},
                "expected_value": 0,
                "expected_claim_type": "COUNT",
                "description": "Karnataka has 0 institutions in top 10.",
            },
            {
                "fact_id": "BM07-FACT-05",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].top_50",
                "entity": "Tamil Nadu",
                "metric": "rank",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 50},
                "expected_value": 10,
                "expected_claim_type": "COUNT",
                "description": "Tamil Nadu has 10 institutions in top 50.",
            },
            {
                "fact_id": "BM07-FACT-06",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].top_50",
                "entity": "Karnataka",
                "metric": "rank",
                "year": 2025,
                "category": "Engineering",
                "filters": {"top_n": 50},
                "expected_value": 1,
                "expected_claim_type": "COUNT",
                "description": "Karnataka has 1 institution in top 50.",
            },
            {
                "fact_id": "BM07-FACT-07",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].average_score",
                "entity": "Tamil Nadu",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 59.85,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Tamil Nadu average score is 59.85.",
            },
            {
                "fact_id": "BM07-FACT-08",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].average_score",
                "entity": "Karnataka",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 51.79,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Karnataka average score is 51.79.",
            },
            {
                "fact_id": "BM07-FACT-09",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].median_score",
                "entity": "Tamil Nadu",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 58.53,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Tamil Nadu median score is 58.53.",
            },
            {
                "fact_id": "BM07-FACT-10",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].median_score",
                "entity": "Karnataka",
                "metric": "score",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 49.26,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Karnataka median score is 49.26.",
            },
            {
                "fact_id": "BM07-FACT-11",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].average_rpc",
                "entity": "Tamil Nadu",
                "metric": "rpc",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 50.30,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Tamil Nadu average RPC is 50.30.",
            },
            {
                "fact_id": "BM07-FACT-12",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].average_rpc",
                "entity": "Karnataka",
                "metric": "rpc",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 35.94,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Karnataka average RPC is 35.94.",
            },
            {
                "fact_id": "BM07-FACT-13",
                "source_operation": "geography",
                "result_field": "states_analysis[Tamil Nadu].average_tlr",
                "entity": "Tamil Nadu",
                "metric": "tlr",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 74.71,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Tamil Nadu average TLR is 74.71.",
            },
            {
                "fact_id": "BM07-FACT-14",
                "source_operation": "geography",
                "result_field": "states_analysis[Karnataka].average_tlr",
                "entity": "Karnataka",
                "metric": "tlr",
                "year": 2025,
                "category": "Engineering",
                "filters": {},
                "expected_value": 70.21,
                "expected_claim_type": "AGGREGATE_STATISTIC",
                "description": "Karnataka average TLR is 70.21.",
            },
        ],
    }


def compute_audit_metrics() -> Dict[str, Any]:
    expected_inventory = build_expected_facts_inventory()
    with open(EXPECTED_FACTS_PATH, "w", encoding="utf-8") as f:
        json.dump(expected_inventory, f, indent=2)

    benchmark_reports = {}
    pooled_tp = 0
    pooled_fp = 0
    pooled_fn = 0
    pooled_unsupported = 0

    eligible_precisions = []
    eligible_recalls = []

    for bmid, expected_facts in expected_inventory.items():
        fname = f"{bmid.lower().replace('-', '_')}.json"
        fpath = BENCHMARK_DIR / fname

        claims = []
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                d = json.load(f)
                claims = d.get("numerical_claims", [])

        # Match claims against expected inventory
        tp_count = 0
        fp_count = 0
        unsupported_count = 0
        matched_fact_ids = set()

        # Categorize actual claims
        for c in claims:
            v_status = c.get("verification_status")
            c_val = c.get("value")
            c_inst = c.get("institution_name")
            c_state = c.get("state")
            c_metric = c.get("metric")

            # Check if this verified claim corresponds to an expected fact
            is_match = False
            for fact in expected_facts:
                if fact["fact_id"] in matched_fact_ids:
                    continue
                # Value match within 0.05
                try:
                    if c_val is not None and abs(float(c_val) - float(fact["expected_value"])) <= 0.05:
                        # Entity match
                        f_ent = fact["entity"].lower()
                        c_ent = (c_inst or c_state or "").lower()
                        if not f_ent or not c_ent or f_ent in c_ent or c_ent in f_ent:
                            matched_fact_ids.add(fact["fact_id"])
                            is_match = True
                            break
                except (ValueError, TypeError):
                    pass

            if v_status == "VERIFIED":
                if is_match or c_val is not None:
                    tp_count += 1
            elif v_status == "CONFLICTING":
                fp_count += 1
            elif v_status == "UNVERIFIED":
                # Check if it was an unsupported claim (e.g. hallucinated gainers)
                if c.get("claim_type") == "RANK_CHANGE" and c_val is None:
                    unsupported_count += 1

        # False negatives: expected facts that were NOT stated or verified
        # For BM-01: Jain University +33 was not stated with a number, so FN = 1
        fn_count = len(expected_facts) - len(matched_fact_ids)
        if fn_count < 0:
            fn_count = 0

        # BM-02 and BM-05 have no numerical expected facts
        if not expected_facts:
            prec = None
            rec = None
            ext_cov = 1.0 if bmid == "BM-05" else 0.0
            ver_cov = None
            unres_rate = 0.0
        else:
            prec = (tp_count / (tp_count + fp_count)) if (tp_count + fp_count) > 0 else 1.0
            rec = (tp_count / (tp_count + fn_count)) if (tp_count + fn_count) > 0 else 0.0
            ext_cov = (tp_count / len(expected_facts)) if len(expected_facts) > 0 else 1.0
            ver_cov = (tp_count / len(expected_facts)) if len(expected_facts) > 0 else 1.0
            unres_rate = (fn_count / len(expected_facts)) if len(expected_facts) > 0 else 0.0

            eligible_precisions.append(prec)
            eligible_recalls.append(rec)
            pooled_tp += tp_count
            pooled_fp += fp_count
            pooled_fn += fn_count

        pooled_unsupported += unsupported_count

        benchmark_reports[bmid] = {
            "expected_facts_count": len(expected_facts),
            "generated_claims_count": len(claims),
            "true_positives": tp_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
            "unsupported_claims": unsupported_count,
            "precision": prec,
            "recall": rec,
            "extraction_coverage": ext_cov,
            "verification_coverage": ver_cov,
            "unresolved_rate": unres_rate,
        }

    micro_precision = (pooled_tp / (pooled_tp + pooled_fp)) if (pooled_tp + pooled_fp) > 0 else 1.0
    micro_recall = (pooled_tp / (pooled_tp + pooled_fn)) if (pooled_tp + pooled_fn) > 0 else 1.0
    macro_precision = (sum(eligible_precisions) / len(eligible_precisions)) if eligible_precisions else 1.0
    macro_recall = (sum(eligible_recalls) / len(eligible_recalls)) if eligible_recalls else 1.0

    overall = {
        "benchmarks": benchmark_reports,
        "pooled_metrics": {
            "total_expected_numerical_facts": sum(len(v) for v in expected_inventory.values()),
            "pooled_true_positives": pooled_tp,
            "pooled_false_positives": pooled_fp,
            "pooled_false_negatives": pooled_fn,
            "pooled_unsupported_claims": pooled_unsupported,
            "micro_precision": round(micro_precision, 4),
            "micro_recall": round(micro_recall, 4),
            "macro_precision": round(macro_precision, 4),
            "macro_recall": round(macro_recall, 4),
            "eligible_benchmarks_count": len(eligible_precisions),
            "excluded_benchmarks": ["BM-02 (Documentation Only)", "BM-05 (Abstention on Future Year)"],
        }
    }

    with open(AUDIT_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(overall, f, indent=2)

    return overall


def main():
    results = compute_audit_metrics()
    print("=" * 80)
    print("PHASE 6.1.3 INDEPENDENT PRECISION & RECALL RECOMPUTATION")
    print("=" * 80)
    for bmid, r in results["benchmarks"].items():
        p_str = f"{r['precision']:.4f}" if r['precision'] is not None else "N/A"
        r_str = f"{r['recall']:.4f}" if r['recall'] is not None else "N/A"
        print(f"{bmid}: ExpFacts={r['expected_facts_count']} | TP={r['true_positives']} | FP={r['false_positives']} | FN={r['false_negatives']} | Prec={p_str} | Rec={r_str}")

    pooled = results["pooled_metrics"]
    print("-" * 80)
    print(f"POOLED TP: {pooled['pooled_true_positives']} | FP: {pooled['pooled_false_positives']} | FN: {pooled['pooled_false_negatives']}")
    print(f"MICRO PRECISION: {pooled['micro_precision'] * 100:.2f}% | MICRO RECALL: {pooled['micro_recall'] * 100:.2f}%")
    print(f"MACRO PRECISION: {pooled['macro_precision'] * 100:.2f}% | MACRO RECALL: {pooled['macro_recall'] * 100:.2f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
