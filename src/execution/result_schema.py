"""
Structured Execution Result Schemas for NIRF Analytics Execution Engine (Phase 4).
Defines predictable Pydantic models for single and multi-operation execution outputs,
performance metadata, and strict JSON serialization handling for Pandas/NumPy types.
"""

from typing import Dict, Any, List, Optional, Literal, Union
import math
import json
import uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict


ExecutionStatus = Literal[
    "SUCCESS",
    "PARTIAL_SUCCESS",
    "FAILED",
    "REJECTED",
    "CLARIFICATION_REQUIRED",
]

OperationStatus = Literal[
    "SUCCESS",
    "FAILED",
    "SKIPPED_DEPENDENCY_FAILED",
]


def clean_for_json(obj: Any) -> Any:
    """
    Recursively converts Pandas DataFrames, Series, NumPy primitives, NaNs,
    and infinities into standard, strictly serializable Python objects.
    """
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return [clean_for_json(row) for row in obj.to_dict(orient="records")]
    if isinstance(obj, pd.Series):
        return clean_for_json(obj.to_dict())
    if isinstance(obj, np.ndarray):
        return [clean_for_json(x) for x in obj.tolist()]
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        if math.isnan(obj) or math.isinf(obj) or np.isnan(obj) or np.isinf(obj):
            return None
        return round(float(obj), 6)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, dict):
        return {str(k): clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean_for_json(x) for x in obj]
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    return obj


class OperationResult(BaseModel):
    """Result of a single executed analytical operation."""
    model_config = ConfigDict(extra="ignore")

    operation_id: str = Field(description="Identifier of the operation from the QueryPlan.")
    function_name: str = Field(description="Phase 2 analytical function invoked.")
    status: OperationStatus = Field(description="Execution standing of this operation.")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured analytical result data.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata returned by the analytical engine.")
    warnings: List[str] = Field(default_factory=list, description="Warnings emitted during execution.")
    execution_duration_seconds: float = Field(default=0.0, description="Latency of this specific operation in seconds.")
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed.")


class ExecutionMetadata(BaseModel):
    """Aggregated execution performance and contextual metadata."""
    category: Optional[str] = None
    year: Optional[int] = None
    year_range: Optional[List[int]] = None
    institution_filters: List[str] = Field(default_factory=list)
    state_filters: List[str] = Field(default_factory=list)
    selected_parameters: List[str] = Field(default_factory=list)
    analytical_methods: List[str] = Field(default_factory=list)
    records_considered: Optional[int] = None
    valid_observations: Optional[int] = None
    output_records: Optional[int] = None
    excluded_observations: Optional[int] = None
    comparability_warnings: List[str] = Field(default_factory=list)
    execution_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_duration_seconds: float = 0.0


class ExecutionResult(BaseModel):
    """Top-level execution result returned by QueryExecutor."""
    model_config = ConfigDict(extra="ignore")

    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:8]}")
    query_id: str = Field(description="Corresponding QueryPlan query_id.")
    original_question: str = Field(description="Original user question.")
    status: ExecutionStatus = Field(description="Overall execution status.")
    query_type: str = Field(description="Query type classification from plan.")
    operations: List[OperationResult] = Field(default_factory=list, description="Results of all operations in the plan.")
    combined_result: Optional[Dict[str, Any]] = Field(default=None, description="Convenience unified result dictionary.")
    validation_status: str = Field(description="Status from independent QueryValidator.")
    warnings: List[str] = Field(default_factory=list, description="All aggregated warnings across validation & execution.")
    errors: List[str] = Field(default_factory=list, description="All aggregated errors if execution failed.")
    metadata: ExecutionMetadata = Field(default_factory=ExecutionMetadata)

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to a clean dictionary safe for JSON serialization."""
        raw = self.model_dump()
        return clean_for_json(raw)

    def to_json(self, indent: int = 2) -> str:
        """Serializes result strictly to JSON string with NaN/Inf handling."""
        cleaned = self.to_dict()
        return json.dumps(cleaned, indent=indent, allow_nan=False)

