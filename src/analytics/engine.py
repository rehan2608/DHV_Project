"""
Central NIRF Analytics Engine Facade (Level 3 Analytical Interface).
Exposes a unified, deterministic, and serializable public API for all 10 analytical operations.
"""

from typing import Dict, Any, List, Optional, Tuple, Union

from src.analytics.trends import get_institution_trend
from src.analytics.rankings import get_rank_movement
from src.analytics.performance import get_category_performance, get_multidimensional_performance
from src.analytics.geography import get_geographic_analysis
from src.analytics.correlations import get_parameter_correlation, get_parameter_relationship
from src.analytics.distributions import get_score_distribution
from src.analytics.transitions import get_rank_transitions
from src.analytics.outliers import get_outlier_analysis
from src.analytics.categories import get_category_evolution


class NIRFAnalyticsEngine:
    """
    Central Analytical Engine providing high-level, verified statistical calculations
    grounded strictly in the cleaned NIRF master dataset and comparability rules.
    """

    def get_institution_trend(
        self,
        institution_id_or_name: str,
        category: str,
        start_year: Optional[int] = 2017,
        end_year: Optional[int] = 2025,
        parameters: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """FUNCTION 1: Longitudinal institution trajectory, ranks, and parameter evolutions."""
        return get_institution_trend(
            institution_id_or_name=institution_id_or_name,
            category=category,
            start_year=start_year,
            end_year=end_year,
            parameters=parameters,
        )

    def get_rank_movement(
        self,
        category: str,
        start_year: int,
        end_year: int,
        state: Optional[str] = None,
        top_n: int = 10,
        movement_type: str = "both",
    ) -> Dict[str, Any]:
        """FUNCTION 2: Identifies largest rank gains and declines (start_rank - end_rank)."""
        return get_rank_movement(
            category=category,
            start_year=start_year,
            end_year=end_year,
            state=state,
            top_n=top_n,
            movement_type=movement_type,
        )

    def get_category_performance(
        self,
        category: str,
        year: int,
        state: Optional[str] = None,
        top_n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """FUNCTION 3: Category cohort performance, parameters, and statistical summaries."""
        return get_category_performance(
            category=category,
            year=year,
            state=state,
            top_n=top_n,
        )

    def get_geographic_analysis(
        self,
        category: Optional[str] = None,
        year: Optional[int] = 2025,
        states: Optional[List[str]] = None,
        multi_year_trend: bool = False,
    ) -> Dict[str, Any]:
        """FUNCTION 4: State-wise representation, top-tier institutional density, and zone distribution."""
        return get_geographic_analysis(
            category=category,
            year=year,
            states=states,
            multi_year_trend=multi_year_trend,
        )

    def get_parameter_correlation(
        self,
        category: str,
        year: int,
        parameters: Optional[List[str]] = None,
        method: str = "both",
    ) -> Dict[str, Any]:
        """FUNCTION 5: Pairwise Pearson & Spearman correlation matrices with sample sizes."""
        return get_parameter_correlation(
            category=category,
            year=year,
            parameters=parameters,
            method=method,
        )

    def get_parameter_relationship(
        self,
        category: str,
        year: int,
        param_x: str,
        param_y: str,
        institution_uids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """FUNCTION 6: Bivariate linear regression, trendline, and quadrant divergence points."""
        return get_parameter_relationship(
            category=category,
            year=year,
            param_x=param_x,
            param_y=param_y,
            institution_uids=institution_uids,
        )

    def get_multidimensional_performance(
        self,
        category: str,
        year: int,
        institution_uids: Optional[List[str]] = None,
        institution_names: Optional[List[str]] = None,
        parameters: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """FUNCTION 7: Multidimensional parameter profiles, cohort percentiles, and research/teaching gaps."""
        return get_multidimensional_performance(
            category=category,
            year=year,
            institution_uids=institution_uids,
            institution_names=institution_names,
            parameters=parameters,
            top_n=top_n,
        )

    def get_score_distribution(
        self,
        category: str,
        year: int,
        metric: str = "score",
        state: Optional[str] = None,
        bins_count: int = 10,
    ) -> Dict[str, Any]:
        """FUNCTION 8: Quartiles, IQR, sample std dev, skewness, kurtosis, and histogram bins."""
        return get_score_distribution(
            category=category,
            year=year,
            metric=metric,
            state=state,
            bins_count=bins_count,
        )

    def get_rank_transitions(
        self,
        category: str,
        start_year: int,
        end_year: int,
        custom_bands: Optional[List[Tuple[str, int, int]]] = None,
    ) -> Dict[str, Any]:
        """FUNCTION 9: Ordinal tier transition matrix, mobility percentages, and Top 10/50 turnover."""
        return get_rank_transitions(
            category=category,
            start_year=start_year,
            end_year=end_year,
            custom_bands=custom_bands,
        )

    def get_outlier_analysis(
        self,
        category: str,
        year: int,
        metric: Optional[str] = "score",
        method: str = "iqr",
        threshold: float = 1.5,
        lookback_years: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """FUNCTION 10: Statistical outlier detection, domain divergence, and longitudinal rank volatility."""
        return get_outlier_analysis(
            category=category,
            year=year,
            metric=metric,
            method=method,
            threshold=threshold,
            lookback_years=lookback_years,
        )

    def get_category_evolution(
        self,
        start_year: Optional[int] = 2017,
        end_year: Optional[int] = 2025,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """FUNCTION 11: Longitudinal evolution, availability, introductions, and counts of NIRF categories."""
        return get_category_evolution(
            start_year=start_year,
            end_year=end_year,
            category=category,
        )


def get_analytics_engine() -> NIRFAnalyticsEngine:
    """Returns singleton instance of NIRFAnalyticsEngine."""
    return NIRFAnalyticsEngine()

