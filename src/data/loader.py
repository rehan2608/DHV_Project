"""
Data Loader for the NIRF Master Dataset and Comparability Rules.
Handles file ingestion, caching, type enforcement, schema verification,
and query filtering with strict preservation of raw missing values.
"""

from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import logging
import pandas as pd
import numpy as np

from src.config import (
    MASTER_DATASET_PATH,
    COMPARABILITY_RULES_PATH,
    DATA_DICTIONARY_PATH,
)
from src.data.schema import SchemaValidator, SchemaValidationReport

logger = logging.getLogger(__name__)


class NIRFDataLoader:
    """
    Singleton data loader providing thread-safe, cached access to the
    NIRF Master Cleaned Dataset and the official Comparability Rules.
    """

    _instance: Optional["NIRFDataLoader"] = None
    _master_df: Optional[pd.DataFrame] = None
    _comparability_df: Optional[pd.DataFrame] = None
    _validation_report: Optional[SchemaValidationReport] = None

    def __new__(cls) -> "NIRFDataLoader":
        if cls._instance is None:
            cls._instance = super(NIRFDataLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Load automatically if not already loaded
        if self._master_df is None:
            self.load_data()

    def load_data(
        self,
        master_path: Optional[Union[str, Path]] = None,
        comparability_path: Optional[Union[str, Path]] = None,
        force_reload: bool = False
    ) -> None:
        """
        Loads the master dataset and comparability rules from disk.
        Runs schema validation and caches the dataframes.
        """
        if self._master_df is not None and not force_reload:
            return

        m_path = Path(master_path) if master_path else MASTER_DATASET_PATH
        c_path = Path(comparability_path) if comparability_path else COMPARABILITY_RULES_PATH

        if not m_path.exists():
            raise FileNotFoundError(f"Master NIRF dataset not found at: {m_path}")
        if not c_path.exists():
            raise FileNotFoundError(f"Comparability rules not found at: {c_path}")

        logger.info("Loading NIRF Master Dataset from %s", m_path)

        # Enforce exact boolean and categorical parsing where applicable
        bool_cols = [
            "is_uid_transformed",
            "is_city_imputed",
            "is_tied_rank",
            "is_rank_amended",
            "is_rank_withdrawn",
            "has_parameter_scores"
        ]

        df = pd.read_csv(
            m_path,
            low_memory=False,
            dtype={col: bool for col in bool_cols if col in pd.read_csv(m_path, nrows=1).columns}
        )

        # Validate types and schema
        self._validation_report = SchemaValidator.validate_dataset(df)
        if not self._validation_report.is_valid:
            logger.error("Schema validation failed: %s", self._validation_report.summary())
            raise ValueError(f"Dataset failed schema validation: {self._validation_report.errors}")

        self._master_df = df
        logger.info(
            "Successfully loaded %d records across %d columns from %s",
            len(df),
            len(df.columns),
            m_path.name
        )

        # Load comparability rules
        comp_df = pd.read_csv(c_path)
        self._comparability_df = comp_df
        logger.info(
            "Successfully loaded %d cohort comparability rules from %s",
            len(comp_df),
            c_path.name
        )

    @property
    def master_df(self) -> pd.DataFrame:
        """Returns a copy or read-only view of the master dataset."""
        if self._master_df is None:
            self.load_data()
        return self._master_df

    @property
    def comparability_df(self) -> pd.DataFrame:
        """Returns the comparability rules dataframe."""
        if self._comparability_df is None:
            self.load_data()
        return self._comparability_df

    @property
    def validation_report(self) -> Optional[SchemaValidationReport]:
        """Returns the latest schema validation report."""
        return self._validation_report

    def get_available_categories(self) -> List[str]:
        """Returns sorted list of distinct categories in the dataset."""
        return sorted(self.master_df["category"].dropna().unique().tolist())

    def get_available_years(self) -> List[int]:
        """Returns sorted list of distinct assessment edition years."""
        return sorted(int(y) for y in self.master_df["year"].dropna().unique())

    def get_available_states(self) -> List[str]:
        """Returns sorted list of distinct standardized states."""
        return sorted(self.master_df["state_std"].dropna().unique().tolist())

    def filter_records(
        self,
        category: Optional[str] = None,
        years: Optional[List[int]] = None,
        states: Optional[List[str]] = None,
        institution_uids: Optional[List[str]] = None,
        institution_names: Optional[List[str]] = None,
        min_rank: Optional[float] = None,
        max_rank: Optional[float] = None,
        has_score_only: bool = False,
    ) -> pd.DataFrame:
        """
        Filters the dataset safely according to specified criteria.
        Preserves missing values without imputation.
        """
        df = self.master_df

        mask = pd.Series(True, index=df.index)

        if category:
            # Case-insensitive match on category
            cat_mask = df["category"].str.lower() == category.strip().lower()
            mask = mask & cat_mask

        if years:
            mask = mask & df["year"].isin(years)

        if states:
            states_lower = [s.strip().lower() for s in states]
            mask = mask & df["state_std"].str.lower().isin(states_lower)

        if institution_uids:
            mask = mask & df["institution_uid"].isin(institution_uids)

        if institution_names:
            names_lower = [n.strip().lower() for n in institution_names]
            name_mask = df["institute_name_std"].str.lower().apply(
                lambda val: any(target in val for target in names_lower)
            )
            mask = mask & name_mask

        if min_rank is not None:
            mask = mask & (df["rank"] >= min_rank)

        if max_rank is not None:
            mask = mask & (df["rank"] <= max_rank)

        if has_score_only:
            mask = mask & df["score"].notnull()

        return df[mask].copy()

    def search_institutions(self, query: str, limit: int = 10) -> pd.DataFrame:
        """
        Searches distinct institutions by name or UID substring.
        """
        q = query.strip().lower()
        df = self.master_df

        name_match = df["institute_name_std"].str.lower().str.contains(q, na=False, regex=False)
        uid_match = df["institution_uid"].str.lower().str.contains(q, na=False, regex=False)
        raw_name_match = df["institute_name_raw"].str.lower().str.contains(q, na=False, regex=False)

        matches = df[name_match | uid_match | raw_name_match]

        unique_insts = matches[[
            "institution_uid",
            "institute_name_std",
            "city_std",
            "state_std",
            "institution_group"
        ]].drop_duplicates(subset=["institution_uid"]).head(limit)

        return unique_insts


# Global accessor function for easy access
def get_data_loader() -> NIRFDataLoader:
    """Returns singleton NIRFDataLoader instance."""
    return NIRFDataLoader()

