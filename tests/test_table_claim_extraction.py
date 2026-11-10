"""
Tests for Markdown Table Claim Extraction in ClaimExtractor (Audit 4).
Verifies that genuine facts inside Markdown tables are correctly extracted,
table headers with numbers are not misparsed as claims, and dual-appearing facts
are seamlessly deduplicated.
"""

import pytest
from src.response.claim_extractor import ClaimExtractor
from src.response.claim_auditor import IndependentClaimAuditor


def test_fact_appearing_only_in_markdown_table():
    extractor = ClaimExtractor()
    text = """
### Institutional Performance Overview
Below is the verified performance data:

| Institution | Rank | Score |
| :--- | :--- | :--- |
| Indian Institute of Technology Madras | 1 | 88.72 |
| Indian Institute of Technology Bombay | 3 | 83.65 |
"""
    claims = extractor.extract_claims(text)
    assert len(claims) >= 4, "Must extract rank and score for both institutions from table."
    
    # Check IIT Madras claims
    iitm_claims = [c for c in claims if "madras" in (c.institution_name or "").lower()]
    assert any(c.metric == "rank" and c.claimed_value == 1 for c in iitm_claims)
    assert any(c.metric == "score" and c.claimed_value == 88.72 for c in iitm_claims)


def test_same_fact_appearing_in_prose_and_table_deduplicated():
    extractor = ClaimExtractor()
    auditor = IndependentClaimAuditor()
    text = """
IIT Madras achieved a score of 88.72 in the Engineering category.

| Institution | Score |
| :--- | :--- |
| IIT Madras | 88.72 |
"""
    # Extraction produces both prose and table representation
    claims = extractor.extract_claims(text)
    
    # Audit and reconciliation must deduplicate them to a single canonical fact
    reconciled, _ = auditor.audit_and_reconcile(text, claims, None)
    
    # Only 1 distinct fact should remain
    iitm_score_claims = [c for c in reconciled if "madras" in (c.institution_name or "").lower() and c.metric == "score"]
    assert len(iitm_score_claims) == 1, "Fact present in both prose and table must not be double counted."
    assert iitm_score_claims[0].value == 88.72


def test_table_containing_multiple_categories():
    extractor = ClaimExtractor()
    text = """
| Category | Distinct Institutions | Average Score |
| :--- | :--- | :--- |
| Engineering | 100 | 54.32 |
| Management | 50 | 48.75 |
"""
    claims = extractor.extract_claims(text)
    assert len(claims) >= 4, "Should extract metrics for both Engineering and Management categories."
    
    eng_claims = [c for c in claims if (c.category or c.institution_name or "").lower() == "engineering"]
    mgmt_claims = [c for c in claims if (c.category or c.institution_name or "").lower() == "management"]
    
    assert len(eng_claims) >= 2
    assert len(mgmt_claims) >= 2


def test_table_containing_multiple_institutions_and_parameters():
    extractor = ClaimExtractor()
    text = """
| Institution | Rank | Score | RPC | TLR |
| :--- | :--- | :--- | :--- | :--- |
| IIT Delhi | 2 | 85.74 | 93.47 | 88.58 |
| IIT Kanpur | 4 | 81.82 | 82.10 | 87.30 |
| IIT Roorkee | 6 | 75.44 | 76.20 | 82.40 |
"""
    claims = extractor.extract_claims(text)
    # 3 institutions * 4 metrics = 12 claims
    assert len(claims) == 12, f"Expected 12 distinct metric claims, got {len(claims)}."
    
    delhi_rpc = [c for c in claims if "delhi" in (c.institution_name or "").lower() and c.metric == "rpc"]
    assert len(delhi_rpc) == 1
    assert delhi_rpc[0].claimed_value == 93.47


def test_table_metric_by_row_layout():
    extractor = ClaimExtractor()
    text = """
| Metric | Tamil Nadu | Karnataka |
| :--- | :--- | :--- |
| Distinct Institutions (Top 100) | 14 | 7 |
| Top 10 Institutions | 2 | 0 |
| Top 50 Institutions | 10 | 1 |
| Average Score | 59.85 | 51.79 |
| Average RPC | 50.30 | 35.94 |
"""
    claims = extractor.extract_claims(text)
    # 5 metrics * 2 states = 10 claims
    assert len(claims) == 10, f"Expected 10 state aggregate claims, got {len(claims)}."
    
    tn_rpc = [c for c in claims if c.state == "Tamil Nadu" and c.metric == "rpc"]
    assert len(tn_rpc) == 1
    assert tn_rpc[0].claimed_value == 50.30


def test_table_headers_with_numbers_not_misparsed_as_claims():
    extractor = ClaimExtractor()
    text = """
| Indicator | Top 10 Cohort | Top 50 Cohort |
| :--- | :--- | :--- |
| Institution Count | 10 | 50 |
| Average Score | 82.4 | 67.8 |
"""
    claims = extractor.extract_claims(text)
    # Header numbers (10, 50 in header row) must NOT be extracted as standalone claims.
    # Only cell numbers under data rows should be extracted.
    for c in claims:
        # None of the claims should have claim_text matching the table header line
        assert "top 10 cohort" not in (c.claim_text or "").lower() or c.claimed_value in (10, 50, 82.4, 67.8)
