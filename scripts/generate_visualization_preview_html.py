"""
HTML Gallery Generator for Phase 7 Visualization Preview.
Generates a standalone, self-contained interactive HTML file containing all 10
analytical visualizations rendered by Plotly using 100% real cleaned NIRF master data.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import plotly.io as pio

from src.analytics.engine import get_analytics_engine
from src.execution.result_schema import OperationResult
from src.visualization.visualization_service import get_visualization_service

OUTPUT_HTML_PATH = Path("docs/visualization_preview.html")


def generate_preview_html():
    engine = get_analytics_engine()
    vis_service = get_visualization_service()

    operations = [
        (
            "1. Institution Ranking Trend (Line Chart with Reversed Rank Axis)",
            "get_institution_trend",
            engine.get_institution_trend("Indian Institute of Technology Madras", "Engineering", 2017, 2025),
            "Longitudinal rank trajectory of IIT Madras in Engineering from 2017 to 2025. Rank 1 is on top.",
        ),
        (
            "2. Institution Rank Movement (Horizontal Bar Chart)",
            "get_rank_movement",
            engine.get_rank_movement("Engineering", 2020, 2025, top_n=8),
            "Largest rank gainers (green) and decliners (red) in Engineering from 2020 to 2025.",
        ),
        (
            "3. Category Performance Comparison (Bar Chart)",
            "get_category_performance",
            engine.get_category_performance("Engineering", 2025, top_n=10),
            "Top 10 institutions in Engineering 2025 sorted by overall score with state coloring.",
        ),
        (
            "4. State-wise Institutional Distribution (Ranked Bar Chart)",
            "get_geographic_analysis",
            engine.get_geographic_analysis("Engineering", 2025, states=["Tamil Nadu", "Karnataka", "Maharashtra", "Delhi", "Uttar Pradesh", "Telangana", "Kerala", "West Bengal"]),
            "Distinct ranked institution count per state in Engineering (2025), color-coded by zone.",
        ),
        (
            "5. Parameter Correlation Heatmap",
            "get_parameter_correlation",
            engine.get_parameter_correlation("Engineering", 2025),
            "Pairwise correlation matrix (TLR, RPC, GO, OI, Perception) in Engineering 2025 with annotated values.",
        ),
        (
            "6. TLR vs. RPC Scatter Plot with Regression Trendline",
            "get_parameter_relationship",
            engine.get_parameter_relationship("Engineering", 2025, "rpc", "tlr"),
            "Bivariate scatter plot comparing Research (RPC) vs. Teaching (TLR) in 2025 with regression trendline and medians.",
        ),
        (
            "7. Score Distribution (Histogram)",
            "get_score_distribution",
            engine.get_score_distribution("Engineering", 2025, "score"),
            "Frequency distribution of overall scores across 10 histogram intervals in Engineering 2025.",
        ),
        (
            "8. Ordinal Tier Transition Matrix (Transition Heatmap)",
            "get_rank_transitions",
            engine.get_rank_transitions("Engineering", 2020, 2025),
            "Mobility across ordinal bands (Top 10, 11–25, 26–50, 51–100, Below 100, Unranked) from 2020 to 2025.",
        ),
        (
            "9. Statistical Outlier Analysis (Outliers Bar Chart)",
            "get_outlier_analysis",
            engine.get_outlier_analysis("Engineering", 2025, "score"),
            "Institutions whose score falls beyond 1.5x IQR in Engineering 2025.",
        ),
        (
            "10. Multidimensional Parameter Profiles (Grouped Bar Chart)",
            "get_multidimensional_performance",
            engine.get_multidimensional_performance("Engineering", 2025, top_n=5),
            "Multi-parameter profile comparison (TLR, RPC, GO, OI, Perception) for top 5 institutions.",
        ),
    ]

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NIRF Assistant — Phase 7 Visualization Gallery</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #1e293b; }
        .header { background: #ffffff; padding: 24px 32px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 24px; border-left: 6px solid #2563eb; }
        .badge { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 9999px; font-size: 13px; font-weight: 600; display: inline-block; margin-top: 8px; }
        .card { background: #ffffff; border-radius: 12px; padding: 24px; margin-bottom: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }
        .card-header { margin-bottom: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; }
        .card-title { font-size: 20px; font-weight: 700; color: #1e3a8a; margin: 0 0 4px 0; }
        .card-desc { font-size: 14px; color: #64748b; margin: 0; }
        .warning-box { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 12px 0; font-size: 13px; color: #92400e; border-radius: 4px; }
        .chart-container { min-height: 480px; width: 100%; margin-bottom: 16px; }
        details { background: #f1f5f9; padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 12px; }
        summary { cursor: pointer; font-weight: 600; color: #334155; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
        th, td { border: 1px solid #cbd5e1; padding: 6px 10px; text-align: left; }
        th { background: #e2e8f0; }
        .nav-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }
        .nav-pill { background: #ffffff; border: 1px solid #cbd5e1; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; text-decoration: none; color: #1e293b; }
        .nav-pill:hover { background: #2563eb; color: #ffffff; border-color: #2563eb; }
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0; color: #1e3a8a;">NIRF Conversational Analytical Assistant — Phase 7 Visualization Gallery</h1>
        <p style="margin: 8px 0 0 0; color: #475569;">Standalone verification preview of all 10 analytical operations rendered via Plotly.</p>
        <div class="badge">🟢 100% Real Cleaned NIRF Master Data (2017–2025)</div>
    </div>

    <div class="nav-pills">
""")

    for idx, (label, fn_name, _, _) in enumerate(operations, 1):
        short_title = label.split(". ")[1].split(" (")[0]
        html_parts.append(f'        <a class="nav-pill" href="#chart_{idx}">{idx}. {short_title}</a>\n')

    html_parts.append("    </div>\n\n")

    for idx, (label, fn_name, raw_data, desc) in enumerate(operations, 1):
        op_res = OperationResult(
            operation_id=f"op_{fn_name}",
            function_name=fn_name,
            status="SUCCESS",
            data=raw_data,
            metadata=raw_data.get("metadata", {}),
            warnings=raw_data.get("metadata", {}).get("warnings", []),
        )
        vis_res = vis_service.visualize_operation(op_res)

        html_parts.append(f'    <div class="card" id="chart_{idx}">\n')
        html_parts.append('        <div class="card-header">\n')
        html_parts.append(f'            <div class="card-title">{label}</div>\n')
        html_parts.append(f'            <div class="card-desc">{desc}</div>\n')
        html_parts.append('        </div>\n')

        if vis_res.warnings:
            for w in vis_res.warnings:
                html_parts.append(f'        <div class="warning-box">⚠️ <b>Comparability Limitation:</b> {w}</div>\n')

        if vis_res.has_chart and vis_res.figure is not None:
            fig_div = pio.to_html(vis_res.figure, full_html=False, include_plotlyjs=False)
            html_parts.append(f'        <div class="chart-container">{fig_div}</div>\n')

        if vis_res.table_data:
            cols = list(vis_res.table_data[0].keys()) if vis_res.table_data else []
            rows_html = []
            for row in vis_res.table_data[:15]:
                cells = "".join([f"<td>{row.get(c, '')}</td>" for c in cols])
                rows_html.append(f"<tr>{cells}</tr>")

            th_html = "".join([f"<th>{c}</th>" for c in cols])
            count_label = f"Showing {min(15, len(vis_res.table_data))} of {len(vis_res.table_data)} records"
            html_parts.append(f"""
        <details>
            <summary>📋 Underlying Data Table ({count_label})</summary>
            <table>
                <thead><tr>{th_html}</tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table>
        </details>
""")

        html_parts.append("    </div>\n\n")

    html_parts.append("""
</body>
</html>
""")

    OUTPUT_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write("".join(html_parts))

    print(f"Generated standalone preview HTML at: {OUTPUT_HTML_PATH.resolve()}")
    return OUTPUT_HTML_PATH


if __name__ == "__main__":
    generate_preview_html()
