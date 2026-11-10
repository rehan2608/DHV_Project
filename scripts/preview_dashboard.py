"""
Standalone Streamlit Visualization Gallery (Phase 7 Preview).
Allows visual inspection and interactive exploration of all 10 NIRF analytical operations
rendered as interactive Plotly figures using 100% real cleaned NIRF master data.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import json

from src.analytics.engine import get_analytics_engine
from src.execution.result_schema import OperationResult
from src.visualization.visualization_service import get_visualization_service

# Page Configuration
st.set_page_config(
    page_title="NIRF Analytics — Phase 7 Visualization Preview",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished interface
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }
    .badge-real {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_services():
    """Initializes and caches the NIRF analytics engine and visualization service."""
    engine = get_analytics_engine()
    vis_service = get_visualization_service()
    return engine, vis_service


engine, vis_service = load_services()

# Sidebar Navigation
st.sidebar.markdown("## 📊 Phase 7 Gallery")
st.sidebar.markdown(
    '<span class="badge-real">🟢 100% Real NIRF Master Data</span>',
    unsafe_allow_html=True,
)

OPERATIONS = {
    "1. Institution Ranking Trend (Line Chart)": "trend",
    "2. Institution Rank Movement (Horizontal Bar)": "movement",
    "3. Category Performance Comparison (Bar Chart)": "category",
    "4. State-wise Institutional Distribution (Ranked Bar)": "geography",
    "5. Parameter Correlation Heatmap (Heatmap)": "correlation",
    "6. TLR vs. RPC Scatter Plot (Scatter Plot)": "relationship",
    "7. Score Distribution (Histogram)": "distribution",
    "8. Rank Transitions (Transition Heatmap)": "transitions",
    "9. Outlier Analysis (Outliers Bar)": "outliers",
    "10. Multidimensional Performance (Grouped Bar)": "multidimensional",
    "🌟 Complete Gallery View (All 10 Charts)": "all",
}

selected_option = st.sidebar.radio("Select Visualization Preview:", list(OPERATIONS.keys()))
view_mode = OPERATIONS[selected_option]

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ View Controls")
show_table = st.sidebar.checkbox("Show underlying data table", value=True)
show_raw_json = st.sidebar.checkbox("Show raw execution metadata", value=False)
st.sidebar.markdown("---")
st.sidebar.caption("Google Antigravity NIRF Assistant — Phase 7 Visualization Layer")


def render_vis_card(title_label: str, operation_name: str, op_result_data: dict, description: str):
    """Renders a complete visual preview card with Plotly figure, warnings, table, and CSV download."""
    op_res = OperationResult(
        operation_id=f"op_{operation_name}",
        function_name=operation_name,
        status="SUCCESS",
        data=op_result_data,
        metadata=op_result_data.get("metadata", {}),
        warnings=op_result_data.get("metadata", {}).get("warnings", []),
    )

    vis_res = vis_service.visualize_operation(op_res)

    st.markdown(f"### {title_label}")
    st.markdown(f"*{description}*")

    # Comparability / limitation warnings
    if vis_res.warnings:
        for w in vis_res.warnings:
            st.warning(f"⚠️ **Comparability Notice:** {w}")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Chart Type", vis_res.chart_spec.chart_type if vis_res.chart_spec else "Table")
    with col2:
        records_count = len(vis_res.table_data or (vis_res.chart_spec.data if vis_res.chart_spec else []))
        st.metric("Observations Count", records_count)
    with col3:
        st.metric("Category", vis_res.metadata.get("category", "NIRF Cohort"))
    with col4:
        st.metric("Data Grounding", "100% Real NIRF Master")

    # Interactive Plotly Figure
    if vis_res.has_chart and vis_res.figure is not None:
        st.plotly_chart(vis_res.figure, use_container_width=True)
    elif vis_res.status == "FALLBACK_TABLE":
        st.info("ℹ️ Small lookup or single observation: Presented as structured table.")

    # Data Table
    if show_table and vis_res.table_data:
        st.markdown("#### 📋 Underlying Data Table")
        df = pd.DataFrame(vis_res.table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv_str = vis_res.to_csv()
        if csv_str:
            st.download_button(
                label=f"📥 Download {operation_name} Data (CSV)",
                data=csv_str,
                file_name=f"{operation_name}_nirf_data.csv",
                mime="text/csv",
                key=f"csv_{operation_name}",
            )

    # Raw JSON Expander
    if show_raw_json:
        with st.expander("🔍 View Raw Execution Result JSON"):
            st.json(op_result_data)

    st.markdown("---")


# =============================================================================
# Main Application Content
# =============================================================================

st.markdown('<div class="main-header">NIRF Assistant — Phase 7 Visualization Gallery</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Interactive preview verifying all 10 analytical operations rendered via Plotly using 100% real cleaned NIRF historical records (2017–2025).</div>',
    unsafe_allow_html=True,
)

# 1. Institution Trend
if view_mode in ["trend", "all"]:
    raw_trend = engine.get_institution_trend(
        institution_id_or_name="Indian Institute of Technology Madras",
        category="Engineering",
        start_year=2017,
        end_year=2025,
    )
    render_vis_card(
        "1. Institution Ranking Trend (Line Chart with Reversed Rank Axis)",
        "get_institution_trend",
        raw_trend,
        "Longitudinal rank trajectory of IIT Madras in Engineering from 2017 to 2025. Rank 1 is on top.",
    )

# 2. Rank Movement
if view_mode in ["movement", "all"]:
    raw_move = engine.get_rank_movement(
        category="Engineering",
        start_year=2020,
        end_year=2025,
        top_n=8,
    )
    render_vis_card(
        "2. Institution Rank Movement (Horizontal Bar Chart: Gainers & Decliners)",
        "get_rank_movement",
        raw_move,
        "Largest rank gainers (green) and decliners (red) in Engineering from 2020 to 2025.",
    )

# 3. Category Performance
if view_mode in ["category", "all"]:
    raw_cat = engine.get_category_performance(
        category="Engineering",
        year=2025,
        top_n=10,
    )
    render_vis_card(
        "3. Category Performance Comparison (Bar Chart)",
        "get_category_performance",
        raw_cat,
        "Top 10 institutions in Engineering 2025 sorted by overall score with state coloring.",
    )

# 4. Geographic Analysis
if view_mode in ["geography", "all"]:
    raw_geo = engine.get_geographic_analysis(
        category="Engineering",
        year=2025,
        states=["Tamil Nadu", "Karnataka", "Maharashtra", "Delhi", "Uttar Pradesh", "Telangana", "Kerala", "West Bengal"],
    )
    render_vis_card(
        "4. State-wise Institutional Distribution (Ranked Bar Chart)",
        "get_geographic_analysis",
        raw_geo,
        "Distinct ranked institution count per state in Engineering (2025), color-coded by zone.",
    )

# 5. Parameter Correlation
if view_mode in ["correlation", "all"]:
    raw_corr = engine.get_parameter_correlation(
        category="Engineering",
        year=2025,
    )
    render_vis_card(
        "5. Parameter Correlation Heatmap",
        "get_parameter_correlation",
        raw_corr,
        "Pairwise correlation matrix (TLR, RPC, GO, OI, Perception) in Engineering 2025 with annotated values.",
    )

# 6. Parameter Relationship
if view_mode in ["relationship", "all"]:
    raw_rel = engine.get_parameter_relationship(
        category="Engineering",
        year=2025,
        param_x="rpc",
        param_y="tlr",
    )
    render_vis_card(
        "6. TLR vs. RPC Scatter Plot with Regression Trendline",
        "get_parameter_relationship",
        raw_rel,
        "Bivariate scatter plot comparing Research (RPC) vs. Teaching (TLR) in 2025 with regression trendline and medians.",
    )

# 7. Score Distribution
if view_mode in ["distribution", "all"]:
    raw_dist = engine.get_score_distribution(
        category="Engineering",
        year=2025,
        metric="score",
    )
    render_vis_card(
        "7. Score Distribution (Histogram)",
        "get_score_distribution",
        raw_dist,
        "Frequency distribution of overall scores across 10 histogram intervals in Engineering 2025.",
    )

# 8. Rank Transitions
if view_mode in ["transitions", "all"]:
    raw_trans = engine.get_rank_transitions(
        category="Engineering",
        start_year=2020,
        end_year=2025,
    )
    render_vis_card(
        "8. Ordinal Tier Transition Matrix (Transition Heatmap)",
        "get_rank_transitions",
        raw_trans,
        "Mobility across ordinal bands (Top 10, 11–25, 26–50, 51–100, Below 100, Unranked) from 2020 to 2025.",
    )

# 9. Outlier Analysis
if view_mode in ["outliers", "all"]:
    raw_out = engine.get_outlier_analysis(
        category="Engineering",
        year=2025,
        metric="score",
    )
    render_vis_card(
        "9. Statistical Outlier Analysis (Outliers Bar Chart)",
        "get_outlier_analysis",
        raw_out,
        "Institutions whose score falls beyond 1.5x IQR in Engineering 2025.",
    )

# 10. Multidimensional Performance
if view_mode in ["multidimensional", "all"]:
    raw_multi = engine.get_multidimensional_performance(
        category="Engineering",
        year=2025,
        top_n=5,
    )
    render_vis_card(
        "10. Multidimensional Parameter Profiles (Grouped Bar Chart)",
        "get_multidimensional_performance",
        raw_multi,
        "Multi-parameter profile comparison (TLR, RPC, GO, OI, Perception) for top 5 institutions.",
    )

