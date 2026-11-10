"""
Query Router for NIRF Analytics Execution Engine (Phase 4).
Routes validated operations to their deterministic Phase 2 analytical functions
using an explicit, immutable allowlist.
"""

from typing import Callable, Dict, Any, Optional
import logging

from src.analytics.engine import NIRFAnalyticsEngine, get_analytics_engine
from src.execution.exceptions import RouterError

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Resolves analytical function names to concrete Phase 2 callables
    using an explicit allowlist. Prevents dynamic execution or reflection attacks.
    """

    def __init__(self, engine: Optional[NIRFAnalyticsEngine] = None) -> None:
        self.engine = engine or get_analytics_engine()

        # Explicit allowlist mapping function name strings to engine methods
        self._allowlist: Dict[str, Callable[..., Dict[str, Any]]] = {
            "get_institution_trend": self.engine.get_institution_trend,
            "get_rank_movement": self.engine.get_rank_movement,
            "get_category_performance": self.engine.get_category_performance,
            "get_geographic_analysis": self.engine.get_geographic_analysis,
            "get_parameter_correlation": self.engine.get_parameter_correlation,
            "get_parameter_relationship": self.engine.get_parameter_relationship,
            "get_multidimensional_performance": self.engine.get_multidimensional_performance,
            "get_score_distribution": self.engine.get_score_distribution,
            "get_rank_transitions": self.engine.get_rank_transitions,
            "get_outlier_analysis": self.engine.get_outlier_analysis,
            "get_category_evolution": self.engine.get_category_evolution,
        }

    def resolve_function(self, function_name: str) -> Callable[..., Dict[str, Any]]:
        """
        Resolves an analytical function name to its callable.

        Args:
            function_name: Name of the analytical function.

        Returns:
            Callable Phase 2 analytical function.

        Raises:
            RouterError: If function is not in the explicit allowlist.
        """
        fn_clean = function_name.strip()
        if fn_clean not in self._allowlist:
            logger.error("Routing failed: '%s' is not in the allowed analytical functions.", fn_clean)
            raise RouterError(
                f"Unauthorized or unknown analytical function: '{fn_clean}'. "
                f"Allowed functions are: {sorted(list(self._allowlist.keys()))}"
            )

        return self._allowlist[fn_clean]

    def is_allowed(self, function_name: str) -> bool:
        """Returns True if function name is in the allowlist."""
        return function_name.strip() in self._allowlist


def get_query_router(engine: Optional[NIRFAnalyticsEngine] = None) -> QueryRouter:
    """Returns a QueryRouter instance."""
    return QueryRouter(engine=engine)
