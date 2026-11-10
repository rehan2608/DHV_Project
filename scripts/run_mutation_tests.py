"""
Comprehensive Mutation Testing Harness for Phase 6.1.3 Reliability Gate (Audit 5).
Executes 8 controlled mutations across src/response/verifier.py and src/response/claim_auditor.py,
confirms that target tests fail specifically when the mutation is active,
restores production code cleanly, and validates full suite recovery.
"""

import sys
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, List

VERIFIER_PATH = Path("src/response/verifier.py")
AUDITOR_PATH = Path("src/response/claim_auditor.py")


def read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_target_test(test_target: str) -> Tuple[bool, str]:
    cmd = ["pytest", test_target, "-q"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return (res.returncode == 0, res.stdout + res.stderr)


MUTATIONS = [
    {
        "id": "MUT-01",
        "name": "Tolerance Inflation (Bypass numerical error rejection)",
        "file": VERIFIER_PATH,
        "target_test": "tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_NUM_02]",
        "expected_failure_desc": "Incorrect float score 76.0 vs 75.324 should be accepted if tolerance is broken",
        "mutate": lambda code: code.replace("self.float_tolerance = float_tolerance", "self.float_tolerance = 50.0"),
    },
    {
        "id": "MUT-02",
        "name": "Remove Ambiguity Guard (Allow multi-candidate acronym matches)",
        "file": VERIFIER_PATH,
        "target_test": "tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_QUAL_08]",
        "expected_failure_desc": "Ambiguous acronym matching multiple entities should not return UNVERIFIED",
        "mutate": lambda code: code.replace("elif len(candidate_uids) > 1:\n                # Ambiguous: multiple distinct institutions match this name\n                return []", "elif len(candidate_uids) > 1:\n                return candidate_recs"),
    },
    {
        "id": "MUT-03",
        "name": "Bypass Causal Prohibition (Allow 'causes' / 'drives')",
        "file": VERIFIER_PATH,
        "target_test": "tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_QUAL_03]",
        "expected_failure_desc": "Correlation with causal assertion 'causes' should not be rejected",
        "mutate": lambda code: code.replace("for pat in self.CAUSAL_PATTERNS:\n                if re.search(pat, full_statement, re.IGNORECASE):", "for pat in []:\n                if False:"),
    },
    {
        "id": "MUT-04",
        "name": "Bypass Zero-Imputation Check (Allow missing data claimed as 0.0)",
        "file": VERIFIER_PATH,
        "target_test": "tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_NUM_12]",
        "expected_failure_desc": "Missing metric claimed as 0.0 should not be marked CONFLICTING",
        "mutate": lambda code: code.replace('if claimed_num == 0.0:\n                        return (\n                            "CONFLICTING",\n                            f"Violation of missing data rule: Missing {metric_name.upper()} was claimed as 0.0.",\n                            None,\n                        )', 'pass'),
    },
    {
        "id": "MUT-05",
        "name": "Allow Missing/NaN Data to Match Positive Values",
        "file": VERIFIER_PATH,
        "target_test": "tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_NUM_16]",
        "expected_failure_desc": "Missing NaN parameter claimed with 80.0 should not be marked UNVERIFIED",
        "mutate": lambda code: code.replace('return (\n                        "UNVERIFIED",\n                        f"Metric \'{metric_name}\' is missing/NaN in record for institution \'{claim.institution_name}\'.",\n                        None,\n                    )', 'return ("VERIFIED", "Forced verify NaN", 80.0)'),
    },
    {
        "id": "MUT-06",
        "name": "Category Mismatch Bypass (Verifier ignores claimed vs record category)",
        "file": VERIFIER_PATH,
        "target_test": "tests/test_audit_generalization.py::test_category_mismatch_rejection",
        "expected_failure_desc": "Claim for Management should falsely verify against Engineering record if category check removed",
        "mutate": lambda code: code.replace('if claim.category and rec.get("category"):\n                    if claim.category.lower().strip() != str(rec["category"]).lower().strip():\n                        continue', 'pass'),
    },
    {
        "id": "MUT-07",
        "name": "Cohort Signature Bypass (Auditor merges distinct cohorts top-10 vs outlier)",
        "file": AUDITOR_PATH,
        "target_test": "tests/test_semantic_deduplication.py::test_different_cohorts_are_never_merged",
        "expected_failure_desc": "Distinct cohorts should be improperly merged if cohort signature check removed",
        "mutate": lambda code: code.replace('found1 = {ck for ck in cohort_keywords if ck in t1}\n        found2 = {ck for ck in cohort_keywords if ck in t2}\n        if found1 and found2 and found1 != found2:\n            return False', 'pass'),
    },
    {
        "id": "MUT-08",
        "name": "Category Deduplication Bypass (Auditor merges distinct categories)",
        "file": AUDITOR_PATH,
        "target_test": "tests/test_semantic_deduplication.py::test_different_categories_are_never_merged",
        "expected_failure_desc": "Engineering and University claims should improperly merge if category check removed",
        "mutate": lambda code: code.replace('cat1 = (c1.category or "").lower().strip()\n        cat2 = (c2.category or "").lower().strip()\n        if cat1 and cat2 and cat1 != cat2:\n            return False', 'pass'),
    },
]


def main():
    orig_verifier = read_file(VERIFIER_PATH)
    orig_auditor = read_file(AUDITOR_PATH)

    print("=" * 80)
    print("STARTING CONTROLLED MUTATION TESTING (8 MUTATIONS)")
    print("=" * 80)

    # Pre-check clean baseline state
    baseline_passed, out = run_target_test("tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_NUM_01]")
    if not baseline_passed:
        print("ERROR: Baseline test failed before mutation testing!")
        print(out)
        sys.exit(1)

    all_passed_mutations = True
    results = []

    for m in MUTATIONS:
        target_path = m["file"]
        orig_content = orig_verifier if target_path == VERIFIER_PATH else orig_auditor

        print(f"\n---> Applying Mutation: {m['id']} - {m['name']}")
        mutated_code = m["mutate"](orig_content)
        if mutated_code == orig_content:
            print(f"FAILED to apply mutation {m['id']}: target string not found in {target_path.name}!")
            all_passed_mutations = False
            continue

        try:
            write_file(target_path, mutated_code)
            passed, out = run_target_test(m["target_test"])

            # For mutation test to be caught, target test MUST FAIL (returncode != 0)
            if not passed:
                print(f"SUCCESS: Test {m['target_test']} correctly FAILED under {m['id']}.")
                status = "CAUGHT"
            else:
                print(f"DEFECT: Test {m['target_test']} PASSED under {m['id']} (mutation escaped!).")
                status = "ESCAPED"
                all_passed_mutations = False

            results.append({
                "mutation_id": m["id"],
                "name": m["name"],
                "file": target_path.name,
                "target_test": m["target_test"],
                "status": status,
            })
        finally:
            # Always restore original code immediately
            write_file(target_path, orig_content)

    # Post-check restoration
    print("\n---> Verifying code restoration...")
    clean_passed_1, _ = run_target_test("tests/test_synthetic_audit.py::test_synthetic_generalization_case[SYNTH_NUM_02]")
    clean_passed_2, _ = run_target_test("tests/test_audit_generalization.py::test_category_mismatch_rejection")
    clean_passed_3, _ = run_target_test("tests/test_semantic_deduplication.py::test_different_categories_are_never_merged")

    if clean_passed_1 and clean_passed_2 and clean_passed_3:
        print("SUCCESS: Codebase successfully restored to baseline clean state across all files.")
    else:
        print("ERROR: Codebase restoration check failed!")
        all_passed_mutations = False

    print("\n" + "=" * 80)
    print("MUTATION TESTING SUMMARY (8 MUTATIONS)")
    print("=" * 80)
    for r in results:
        print(f"[{r['status']}] {r['mutation_id']} ({r['file']}): {r['name']} -> Caught by {r['target_test'].split('::')[-1]}")

    if all_passed_mutations and len(results) == 8:
        print("\nALL 8 MUTATIONS SUCCESSFULLY CAUGHT (100% Mutation Score)!")
        sys.exit(0)
    else:
        print("\nSOME MUTATIONS ESCAPED OR FAILED TO APPLY.")
        sys.exit(1)


if __name__ == "__main__":
    main()
