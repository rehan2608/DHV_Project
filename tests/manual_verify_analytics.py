"""
Independent Manual Pandas Verification Script for NIRF Analytics Engine (Phase 2).
Executes at least 3 test cases for each of the 10 analytical functions, computing the
expected values independently via direct Pandas/NumPy operations on the master dataset,
and verifying numerical equality within floating-point tolerance.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from scipy import stats

from src.data.loader import get_data_loader
from src.analytics.engine import get_analytics_engine


def run_all_manual_verifications():
    print("=" * 100)
    print("NIRF ANALYTICS ENGINE: INDEPENDENT MANUAL PANDAS VERIFICATION")
    print("=" * 100)

    engine = get_analytics_engine()
    loader = get_data_loader()
    # Independent copy of the master dataframe
    df_raw = loader.master_df.copy()

    total_tests = 0
    passed_tests = 0
    verification_summary = []

    def record_result(func_name, case_desc, actual, expected, match, note=""):
        nonlocal total_tests, passed_tests
        total_tests += 1
        if match:
            passed_tests += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"
        print(f"{status} {func_name} | {case_desc}")
        print(f"       Engine Result   : {actual}")
        print(f"       Pandas Expected : {expected}")
        if note:
            print(f"       Note            : {note}")
        print("-" * 80)
        verification_summary.append({
            "function": func_name,
            "case": case_desc,
            "match": match,
            "status": "PASS" if match else "FAIL"
        })

    # =========================================================================
    # FUNCTION 1: get_institution_trend
    # =========================================================================
    # Case 1: IIT Madras in Engineering 2020-2025 (UID: U-456)
    res1_1 = engine.get_institution_trend("U-456", "Engineering", start_year=2020, end_year=2025)
    # Independent Pandas
    sub = df_raw[(df_raw["institution_uid"] == "U-456") & (df_raw["category"] == "Engineering") & (df_raw["year"].isin(range(2020, 2026)))]
    exp_best_rank = int(sub["rank"].min())
    exp_avg_score = round(float(sub["score"].mean()), 2)
    match1_1 = (res1_1["best_rank"] == exp_best_rank) and np.isclose(res1_1["average_score"], exp_avg_score, atol=0.01)
    record_result("Institution trend", "IIT Madras Engineering 2020-2025", f"best={res1_1['best_rank']}, avg_score={res1_1['average_score']}", f"best={exp_best_rank}, avg_score={exp_avg_score}", match1_1)

    # Case 2: IISc Bangalore in University 2020-2025 (UID: U-220)
    res1_2 = engine.get_institution_trend("U-220", "University", start_year=2020, end_year=2025)
    sub2 = df_raw[(df_raw["institution_uid"] == "U-220") & (df_raw["category"] == "University") & (df_raw["year"].isin(range(2020, 2026)))]
    exp_best2 = int(sub2["rank"].min())
    exp_avg_score2 = round(float(sub2["score"].mean()), 2)
    match1_2 = (res1_2["best_rank"] == exp_best2) and np.isclose(res1_2["average_score"], exp_avg_score2, atol=0.01)
    record_result("Institution trend", "IISc Bangalore University 2020-2025", f"best={res1_2['best_rank']}, avg_score={res1_2['average_score']}", f"best={exp_best2}, avg_score={exp_avg_score2}", match1_2)

    # Case 3: IIM Ahmedabad in Management 2017-2025 (UID: S-8890)
    res1_3 = engine.get_institution_trend("S-8890", "Management", start_year=2017, end_year=2025)
    sub3 = df_raw[(df_raw["institution_uid"] == "S-8890") & (df_raw["category"] == "Management") & (df_raw["year"].isin(range(2017, 2026)))]
    exp_best3 = int(sub3["rank"].min())
    exp_avg_score3 = round(float(sub3["score"].mean()), 2)
    match1_3 = (res1_3["best_rank"] == exp_best3) and np.isclose(res1_3["average_score"], exp_avg_score3, atol=0.01)
    record_result("Institution trend", "IIM Ahmedabad Management 2017-2025", f"best={res1_3['best_rank']}, avg_score={res1_3['average_score']}", f"best={exp_best3}, avg_score={exp_avg_score3}", match1_3)

    # =========================================================================
    # FUNCTION 2: get_rank_movement
    # =========================================================================
    # Case 1: Engineering Karnataka 2020 to 2025
    res2_1 = engine.get_rank_movement("Engineering", 2020, 2025, state="Karnataka", top_n=3)
    s20 = df_raw[(df_raw["category"] == "Engineering") & (df_raw["state_std"] == "Karnataka") & (df_raw["year"] == 2020) & df_raw["rank"].notnull()]
    s25 = df_raw[(df_raw["category"] == "Engineering") & (df_raw["state_std"] == "Karnataka") & (df_raw["year"] == 2025) & df_raw["rank"].notnull()]
    m2 = pd.merge(s20[["institution_uid", "rank"]], s25[["institution_uid", "rank"]], on="institution_uid", suffixes=("_20", "_25"))
    m2["diff"] = m2["rank_20"] - m2["rank_25"]
    top_diff_exp = int(m2["diff"].max())
    top_diff_act = res2_1["gainers"][0]["rank_improvement"] if res2_1["gainers"] else None
    match2_1 = (top_diff_act == top_diff_exp)
    record_result("Rank movement", "Engineering Karnataka 2020-2025 Top Gainer", top_diff_act, top_diff_exp, match2_1)

    # Case 2: Management nationwide 2022 to 2025
    res2_2 = engine.get_rank_movement("Management", 2022, 2025, top_n=1)
    sm22 = df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2022) & df_raw["rank"].notnull()]
    sm25 = df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2025) & df_raw["rank"].notnull()]
    mm = pd.merge(sm22[["institution_uid", "rank"]], sm25[["institution_uid", "rank"]], on="institution_uid")
    mm["diff"] = mm["rank_x"] - mm["rank_y"]
    top_mgmt_diff = int(mm["diff"].max())
    act_mgmt_diff = res2_2["gainers"][0]["rank_improvement"] if res2_2["gainers"] else None
    match2_2 = (act_mgmt_diff == top_mgmt_diff)
    record_result("Rank movement", "Management 2022-2025 Top Gainer", act_mgmt_diff, top_mgmt_diff, match2_2)

    # Case 3: University Tamil Nadu 2020 to 2025
    res2_3 = engine.get_rank_movement("University", 2020, 2025, state="Tamil Nadu", top_n=1)
    su20 = df_raw[(df_raw["category"] == "University") & (df_raw["state_std"] == "Tamil Nadu") & (df_raw["year"] == 2020) & df_raw["rank"].notnull()]
    su25 = df_raw[(df_raw["category"] == "University") & (df_raw["state_std"] == "Tamil Nadu") & (df_raw["year"] == 2025) & df_raw["rank"].notnull()]
    mu = pd.merge(su20[["institution_uid", "rank"]], su25[["institution_uid", "rank"]], on="institution_uid")
    mu["diff"] = mu["rank_x"] - mu["rank_y"]
    top_u_diff = int(mu["diff"].max()) if not mu.empty else None
    act_u_diff = res2_3["gainers"][0]["rank_improvement"] if res2_3["gainers"] else None
    match2_3 = (act_u_diff == top_u_diff)
    record_result("Rank movement", "University Tamil Nadu 2020-2025 Top Gainer", act_u_diff, top_u_diff, match2_3)

    # =========================================================================
    # FUNCTION 3: get_category_performance
    # =========================================================================
    # Case 1: Engineering 2025
    res3_1 = engine.get_category_performance("Engineering", 2025)
    e25 = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)]["score"].dropna()
    exp_mean_3_1 = round(float(e25.mean()), 2)
    exp_count_3_1 = len(e25)
    act_mean_3_1 = res3_1["score_summary"]["mean"]
    act_count_3_1 = res3_1["score_summary"]["count"]
    match3_1 = np.isclose(act_mean_3_1, exp_mean_3_1, atol=0.01) and (act_count_3_1 == exp_count_3_1)
    record_result("Category performance", "Engineering 2025 Score Mean & Count", f"mean={act_mean_3_1}, n={act_count_3_1}", f"mean={exp_mean_3_1}, n={exp_count_3_1}", match3_1)

    # Case 2: College 2024
    res3_2 = engine.get_category_performance("College", 2024)
    c24 = df_raw[(df_raw["category"] == "College") & (df_raw["year"] == 2024)]["score"].dropna()
    exp_mean_3_2 = round(float(c24.mean()), 2)
    act_mean_3_2 = res3_2["score_summary"]["mean"]
    match3_2 = np.isclose(act_mean_3_2, exp_mean_3_2, atol=0.01)
    record_result("Category performance", "College 2024 Score Mean", act_mean_3_2, exp_mean_3_2, match3_2)

    # Case 3: Management 2023
    res3_3 = engine.get_category_performance("Management", 2023)
    m23 = df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2023)]["score"].dropna()
    exp_median_3_3 = round(float(m23.median()), 2)
    act_median_3_3 = res3_3["score_summary"]["median"]
    match3_3 = np.isclose(act_median_3_3, exp_median_3_3, atol=0.01)
    record_result("Category performance", "Management 2023 Score Median", act_median_3_3, exp_median_3_3, match3_3)

    # =========================================================================
    # FUNCTION 4: get_geographic_analysis
    # =========================================================================
    # Case 1: Engineering 2025 State Counts
    res4_1 = engine.get_geographic_analysis("Engineering", 2025)
    e25_geo = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)]
    top_state_exp = e25_geo.groupby("state_std")["institution_uid"].nunique().idxmax()
    top_state_count_exp = int(e25_geo.groupby("state_std")["institution_uid"].nunique().max())
    top_state_act = res4_1["states_analysis"][0]["state"]
    top_state_count_act = res4_1["states_analysis"][0]["distinct_institutions"]
    match4_1 = (top_state_act == top_state_exp) and (top_state_count_act == top_state_count_exp)
    record_result("Geographic analysis", "Engineering 2025 Leading State by Count", f"{top_state_act} ({top_state_count_act})", f"{top_state_exp} ({top_state_count_exp})", match4_1)

    # Case 2: Karnataka Engineering 2025 Top 10 Count
    karn_top10_exp = int(e25_geo[(e25_geo["state_std"] == "Karnataka") & (e25_geo["rank"] <= 10)]["institution_uid"].nunique())
    karn_rec = next(s for s in res4_1["states_analysis"] if s["state"] == "Karnataka")
    karn_top10_act = karn_rec["top_10_institutions"]
    match4_2 = (karn_top10_act == karn_top10_exp)
    record_result("Geographic analysis", "Karnataka Engineering 2025 Top 10 Count", karn_top10_act, karn_top10_exp, match4_2)

    # Case 3: Overall 2024 Tamil Nadu Distinct Count
    res4_3 = engine.get_geographic_analysis("Overall", 2024, states=["Tamil Nadu"])
    ov24_tn = df_raw[(df_raw["category"] == "Overall") & (df_raw["year"] == 2024) & (df_raw["state_std"] == "Tamil Nadu")]["institution_uid"].nunique()
    act_tn = res4_3["states_analysis"][0]["distinct_institutions"]
    match4_3 = (act_tn == int(ov24_tn))
    record_result("Geographic analysis", "Overall 2024 Tamil Nadu Distinct Count", act_tn, int(ov24_tn), match4_3)

    # =========================================================================
    # FUNCTION 5: get_parameter_correlation
    # =========================================================================
    # Case 1: Engineering 2025 TLR vs RPC Pearson r
    res5_1 = engine.get_parameter_correlation("Engineering", 2025, parameters=["tlr", "rpc"])
    paired_5_1 = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)][["tlr", "rpc"]].dropna()
    exp_r_5_1 = round(float(stats.pearsonr(paired_5_1["tlr"], paired_5_1["rpc"])[0]), 4)
    act_r_5_1 = res5_1["pearson_matrix"]["tlr"]["rpc"]
    match5_1 = np.isclose(act_r_5_1, exp_r_5_1, atol=0.001)
    record_result("Parameter correlation", "Engineering 2025 TLR vs RPC Pearson r", act_r_5_1, exp_r_5_1, match5_1)

    # Case 2: Engineering 2025 TLR vs RPC Spearman rho
    exp_rho_5_2 = round(float(stats.spearmanr(paired_5_1["tlr"], paired_5_1["rpc"])[0]), 4)
    act_rho_5_2 = res5_1["spearman_matrix"]["tlr"]["rpc"]
    match5_2 = np.isclose(act_rho_5_2, exp_rho_5_2, atol=0.001)
    record_result("Parameter correlation", "Engineering 2025 TLR vs RPC Spearman rho", act_rho_5_2, exp_rho_5_2, match5_2)

    # Case 3: Management 2024 GO vs Perception Pearson r
    res5_3 = engine.get_parameter_correlation("Management", 2024, parameters=["go", "perception"])
    paired_5_3 = df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2024)][["go", "perception"]].dropna()
    exp_r_5_3 = round(float(stats.pearsonr(paired_5_3["go"], paired_5_3["perception"])[0]), 4)
    act_r_5_3 = res5_3["pearson_matrix"]["go"]["perception"]
    match5_3 = np.isclose(act_r_5_3, exp_r_5_3, atol=0.001)
    record_result("Parameter correlation", "Management 2024 GO vs Perception Pearson r", act_r_5_3, exp_r_5_3, match5_3)

    # =========================================================================
    # FUNCTION 6: get_parameter_relationship
    # =========================================================================
    # Case 1: Engineering 2025 RPC (x) vs TLR (y) Linear Regression Slope
    res6_1 = engine.get_parameter_relationship("Engineering", 2025, param_x="rpc", param_y="tlr")
    p_e25 = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)][["rpc", "tlr"]].dropna()
    reg_exp_1 = stats.linregress(p_e25["rpc"], p_e25["tlr"])
    exp_slope_6_1 = round(float(reg_exp_1.slope), 4)
    exp_r2_6_1 = round(float(reg_exp_1.rvalue ** 2), 4)
    act_slope_6_1 = res6_1["regression"]["slope"]
    act_r2_6_1 = res6_1["regression"]["r_squared"]
    match6_1 = np.isclose(act_slope_6_1, exp_slope_6_1, atol=0.001) and np.isclose(act_r2_6_1, exp_r2_6_1, atol=0.001)
    record_result("Parameter relationship", "Engineering 2025 RPC vs TLR Slope & R2", f"slope={act_slope_6_1}, r2={act_r2_6_1}", f"slope={exp_slope_6_1}, r2={exp_r2_6_1}", match6_1)

    # Case 2: Overall 2024 TLR (x) vs Perception (y) Intercept
    res6_2 = engine.get_parameter_relationship("Overall", 2024, param_x="tlr", param_y="perception")
    p_ov24 = df_raw[(df_raw["category"] == "Overall") & (df_raw["year"] == 2024)][["tlr", "perception"]].dropna()
    reg_exp_2 = stats.linregress(p_ov24["tlr"], p_ov24["perception"])
    exp_intercept_6_2 = round(float(reg_exp_2.intercept), 4)
    act_intercept_6_2 = res6_2["regression"]["intercept"]
    match6_2 = np.isclose(act_intercept_6_2, exp_intercept_6_2, atol=0.001)
    record_result("Parameter relationship", "Overall 2024 TLR vs Perception Intercept", act_intercept_6_2, exp_intercept_6_2, match6_2)

    # Case 3: University 2023 GO (x) vs TLR (y) Sample Size N
    res6_3 = engine.get_parameter_relationship("University", 2023, param_x="go", param_y="tlr")
    p_u23 = df_raw[(df_raw["category"] == "University") & (df_raw["year"] == 2023)][["go", "tlr"]].dropna()
    exp_n_6_3 = len(p_u23)
    act_n_6_3 = res6_3["sample_size"]
    match6_3 = (act_n_6_3 == exp_n_6_3)
    record_result("Parameter relationship", "University 2023 GO vs TLR Sample Size N", act_n_6_3, exp_n_6_3, match6_3)

    # =========================================================================
    # FUNCTION 7: get_multidimensional_performance
    # =========================================================================
    # Case 1: IIT Madras (U-456) in Engineering 2025 Research vs Teaching Gap
    res7_1 = engine.get_multidimensional_performance("Engineering", 2025, institution_uids=["U-456"])
    row_7_1 = df_raw[(df_raw["institution_uid"] == "U-456") & (df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)].iloc[0]
    exp_gap_7_1 = round(float(row_7_1["rpc"] - row_7_1["tlr"]), 2)
    act_gap_7_1 = res7_1["profiles"][0]["research_vs_teaching_gap"]
    match7_1 = np.isclose(act_gap_7_1, exp_gap_7_1, atol=0.01)
    record_result("Multidimensional perf", "IIT Madras Engineering 2025 (RPC - TLR) Gap", act_gap_7_1, exp_gap_7_1, match7_1)

    # Case 2: IIT Bombay (U-306) in Engineering 2025 Research vs Teaching Gap
    res7_2 = engine.get_multidimensional_performance("Engineering", 2025, institution_uids=["U-306"])
    row_7_2 = df_raw[(df_raw["institution_uid"] == "U-306") & (df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)].iloc[0]
    exp_gap_7_2 = round(float(row_7_2["rpc"] - row_7_2["tlr"]), 2)
    act_gap_7_2 = res7_2["profiles"][0]["research_vs_teaching_gap"]
    match7_2 = np.isclose(act_gap_7_2, exp_gap_7_2, atol=0.01)
    record_result("Multidimensional perf", "IIT Bombay Engineering 2025 (RPC - TLR) Gap", act_gap_7_2, exp_gap_7_2, match7_2)

    # Case 3: Management 2024 Top 1 Cohort Percentile for TLR
    res7_3 = engine.get_multidimensional_performance("Management", 2024, top_n=1)
    top1_mgmt = df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2024)].sort_values("rank").iloc[0]
    cohort_tlr = df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2024)]["tlr"].dropna()
    exp_pct_7_3 = round(float(stats.percentileofscore(cohort_tlr, top1_mgmt["tlr"], kind="rank")), 2)
    act_pct_7_3 = res7_3["profiles"][0]["percentiles"]["tlr"]
    match7_3 = np.isclose(act_pct_7_3, exp_pct_7_3, atol=0.01)
    record_result("Multidimensional perf", "Management 2024 Rank 1 TLR Percentile", act_pct_7_3, exp_pct_7_3, match7_3)

    # =========================================================================
    # FUNCTION 8: get_score_distribution
    # =========================================================================
    # Case 1: Engineering 2025 Score Median and IQR
    res8_1 = engine.get_score_distribution("Engineering", 2025, metric="score")
    s_e25 = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)]["score"].dropna()
    exp_med_8_1 = round(float(s_e25.median()), 2)
    exp_iqr_8_1 = round(float(np.percentile(s_e25, 75) - np.percentile(s_e25, 25)), 2)
    act_med_8_1 = res8_1["statistics"]["median"]
    act_iqr_8_1 = res8_1["statistics"]["iqr"]
    match8_1 = np.isclose(act_med_8_1, exp_med_8_1, atol=0.01) and np.isclose(act_iqr_8_1, exp_iqr_8_1, atol=0.01)
    record_result("Score distribution", "Engineering 2025 Score Median & IQR", f"med={act_med_8_1}, iqr={act_iqr_8_1}", f"med={exp_med_8_1}, iqr={exp_iqr_8_1}", match8_1)

    # Case 2: Overall 2024 RPC Sample Standard Deviation
    res8_2 = engine.get_score_distribution("Overall", 2024, metric="rpc")
    rpc_ov24 = df_raw[(df_raw["category"] == "Overall") & (df_raw["year"] == 2024)]["rpc"].dropna()
    exp_std_8_2 = round(float(rpc_ov24.std(ddof=1)), 2)
    act_std_8_2 = res8_2["statistics"]["std_dev_sample"]
    match8_2 = np.isclose(act_std_8_2, exp_std_8_2, atol=0.01)
    record_result("Score distribution", "Overall 2024 RPC Sample Std Dev", act_std_8_2, exp_std_8_2, match8_2)

    # Case 3: University 2023 Skewness on Score
    res8_3 = engine.get_score_distribution("University", 2023, metric="score")
    u23_s = df_raw[(df_raw["category"] == "University") & (df_raw["year"] == 2023)]["score"].dropna()
    exp_skew_8_3 = round(float(stats.skew(u23_s)), 4)
    act_skew_8_3 = res8_3["statistics"]["skewness"]
    match8_3 = np.isclose(act_skew_8_3, exp_skew_8_3, atol=0.001)
    record_result("Score distribution", "University 2023 Score Skewness", act_skew_8_3, exp_skew_8_3, match8_3)

    # =========================================================================
    # FUNCTION 9: get_rank_transitions
    # =========================================================================
    # Case 1: Engineering 2020-2025 Top 10 to Top 10 Stability Count
    res9_1 = engine.get_rank_transitions("Engineering", 2020, 2025)
    e20_all = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2020)]
    e25_all = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)]
    e20_top10 = set(e20_all[(e20_all["rank"] <= 10)]["institution_uid"])
    e25_top10 = set(e25_all[(e25_all["rank"] <= 10)]["institution_uid"])
    exp_stable_top10 = len(e20_top10.intersection(e25_top10))
    act_stable_top10 = res9_1["transition_matrix"]["Top 10"]["Top 10"]
    match9_1 = (act_stable_top10 == exp_stable_top10)
    record_result("Rank transitions", "Engineering 2020-2025 Top 10 Retained Count", act_stable_top10, exp_stable_top10, match9_1)

    # Case 2: Overall 2022-2025 Upward Transitions Count
    res9_2 = engine.get_rank_transitions("Overall", 2022, 2025)
    act_upward_9_2 = res9_2["mobility_summary"]["upward_transitions"]
    # Re-calculate independently
    o22 = df_raw[(df_raw["category"] == "Overall") & (df_raw["year"] == 2022)].set_index("institution_uid")["rank"]
    o25 = df_raw[(df_raw["category"] == "Overall") & (df_raw["year"] == 2025)].set_index("institution_uid")["rank"]
    bands_tier = [(1, 10), (11, 25), (26, 50), (51, 100), (101, 10000)]
    def get_tier(r):
        if pd.isna(r): return 5
        for idx, (low, high) in enumerate(bands_tier):
            if low <= r <= high: return idx
        return 4
    uids_union = set(o22.index).union(set(o25.index))
    exp_upward_9_2 = sum(1 for u in uids_union if get_tier(o25.get(u, np.nan)) < get_tier(o22.get(u, np.nan)) and not pd.isna(o22.get(u, np.nan)))
    match9_2 = (act_upward_9_2 == exp_upward_9_2)
    record_result("Rank transitions", "Overall 2022-2025 Upward Transitions Count", act_upward_9_2, exp_upward_9_2, match9_2)

    # Case 3: Management 2023-2025 Total Tracked Institutions
    res9_3 = engine.get_rank_transitions("Management", 2023, 2025)
    m23_uids = set(df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2023)]["institution_uid"])
    m25_uids = set(df_raw[(df_raw["category"] == "Management") & (df_raw["year"] == 2025)]["institution_uid"])
    exp_total_tracked_9_3 = len(m23_uids.union(m25_uids))
    act_total_tracked_9_3 = res9_3["mobility_summary"]["total_institutions_tracked"]
    match9_3 = (act_total_tracked_9_3 == exp_total_tracked_9_3)
    record_result("Rank transitions", "Management 2023-2025 Total Tracked Count", act_total_tracked_9_3, exp_total_tracked_9_3, match9_3)

    # =========================================================================
    # FUNCTION 10: get_outlier_analysis
    # =========================================================================
    # Case 1: Engineering 2025 IQR Threshold on Score (Expected bounds)
    res10_1 = engine.get_outlier_analysis("Engineering", 2025, metric="score", method="iqr", threshold=1.5)
    e25_s = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)]["score"].dropna()
    q1_exp = float(np.percentile(e25_s, 25))
    q3_exp = float(np.percentile(e25_s, 75))
    iqr_exp = q3_exp - q1_exp
    exp_upper = round(q3_exp + (1.5 * iqr_exp), 2)
    # Check bounds on first outlier if any or compare upper threshold
    outliers_10_1 = res10_1["metric_outliers"]
    if outliers_10_1:
        act_upper = outliers_10_1[0]["expected_range"][1]
        match10_1 = np.isclose(act_upper, exp_upper, atol=0.01)
    else:
        # verify no rows exceeded upper bound
        match10_1 = (e25_s > exp_upper).sum() == 0
    record_result("Outlier analysis", "Engineering 2025 Score IQR Outlier Upper Bound", act_upper if outliers_10_1 else "No outliers", exp_upper, match10_1)

    # Case 2: Engineering 2025 Z-score RPC (|z| >= 2.0 count)
    res10_2 = engine.get_outlier_analysis("Engineering", 2025, metric="rpc", method="z_score", threshold=2.0)
    e25_rpc = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)]["rpc"].dropna()
    z_scores_exp = (e25_rpc - e25_rpc.mean()) / e25_rpc.std(ddof=1)
    exp_z_outliers_count = int((z_scores_exp.abs() >= 2.0).sum())
    act_z_outliers_count = len(res10_2["metric_outliers"])
    match10_2 = (act_z_outliers_count == exp_z_outliers_count)
    record_result("Outlier analysis", "Engineering 2025 RPC Z-Score (>= 2.0) Count", act_z_outliers_count, exp_z_outliers_count, match10_2)

    # Case 3: Engineering 2025 High Research / Low Teaching Divergence Count
    res10_3 = engine.get_outlier_analysis("Engineering", 2025, method="iqr")
    e25_paired = df_raw[(df_raw["category"] == "Engineering") & (df_raw["year"] == 2025)][["rpc", "tlr"]].dropna()
    gaps = e25_paired["rpc"] - e25_paired["tlr"]
    gap_q1 = float(np.percentile(gaps, 25))
    gap_q3 = float(np.percentile(gaps, 75))
    gap_upper = gap_q3 + (1.5 * (gap_q3 - gap_q1))
    exp_divergent_count = int((gaps > gap_upper).sum())
    act_divergent_count = len(res10_3["parameter_divergence_outliers"])
    match10_3 = (act_divergent_count == exp_divergent_count)
    record_result("Outlier analysis", "Engineering 2025 High RPC/Low TLR Divergence Count", act_divergent_count, exp_divergent_count, match10_3)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 100)
    print(f"INDEPENDENT VERIFICATION TOTALS: {passed_tests} / {total_tests} PASSED ({passed_tests/total_tests*100:.1f}%)")
    print("=" * 100)

    if passed_tests < total_tests:
        print("VERIFICATION FAILED: Discrepancies detected between Engine and Pandas!")
        sys.exit(1)
    else:
        print("VERIFICATION SUCCESS: All 10 analytical functions 100% match manual Pandas calculations.")


if __name__ == "__main__":
    run_all_manual_verifications()
