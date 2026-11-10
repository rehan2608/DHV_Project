"""
NIRF Analytics Package providing deterministic, comparability-compliant statistical analysis.
"""

from src.analytics.engine import NIRFAnalyticsEngine, get_analytics_engine
from src.analytics.trends import get_institution_trend
from src.analytics.rankings import get_rank_movement
from src.analytics.performance import get_category_performance, get_multidimensional_performance
from src.analytics.geography import get_geographic_analysis
from src.analytics.correlations import get_parameter_correlation, get_parameter_relationship
from src.analytics.distributions import get_score_distribution
from src.analytics.transitions import get_rank_transitions
from src.analytics.outliers import get_outlier_analysis
from src.analytics.categories import get_category_evolution

__all__ = [
    "NIRFAnalyticsEngine",
    "get_analytics_engine",
    "get_institution_trend",
    "get_rank_movement",
    "get_category_performance",
    "get_multidimensional_performance",
    "get_geographic_analysis",
    "get_parameter_correlation",
    "get_parameter_relationship",
    "get_score_distribution",
    "get_rank_transitions",
    "get_outlier_analysis",
    "get_category_evolution",
]

