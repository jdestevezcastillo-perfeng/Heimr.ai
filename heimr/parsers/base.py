# Copyright (c) 2025 Juan Estevez Castillo
# Licensed under AGPL v3. Commercial licenses available.
# See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class BaseParser(ABC):
    """
    Abstract base class for all load test result parsers.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = None

    UNIFIED_COLUMNS = {
        'timestamp_dt': 'datetime64[ns, UTC]',  # Standard UTC timestamp
        'elapsed': 'float64',    # Response time in milliseconds
        'success': 'bool',       # True/False status
        'response_code': 'str',  # HTTP Status code (cast to str for consistency)
        'bytes_recv': 'float64',  # Bytes received (response size)
        'bytes_sent': 'float64',  # Bytes sent (request size)
        'vus': 'int64',          # Virtual Users count
        'endpoint': 'str',       # Endpoint name/URL
        'method': 'str'          # HTTP Method
    }

    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """
        Parses the file and returns a standardized pandas DataFrame.
        Must return a DataFrame with columns matching UNIFIED_COLUMNS.
        Missing optional columns should be filled with defaults (NaN or appropriate zero).
        """
        pass

    def _normalize_dataframe(self, df: pd.DataFrame, keep_extra: bool = True) -> pd.DataFrame:
        """
        Helper to ensure DataFrame conforms to UnifiedSchema.
        Should be called by subclasses at the end of parse().
        """
        # Ensure all columns exist
        for col, dtype in self.UNIFIED_COLUMNS.items():
            if col not in df.columns:
                if col == 'vus':
                    df[col] = 1  # Default concurrency if missing
                elif 'bytes' in col or 'elapsed' in col:
                    df[col] = 0.0
                elif col == 'success':
                    df[col] = True
                else:
                    df[col] = None  # Strings

            # Enforce types
            try:
                if dtype == 'datetime64[ns, UTC]':
                    df[col] = pd.to_datetime(df[col], utc=True)
                else:
                    df[col] = df[col].astype(dtype)
            except Exception:
                # Fallback for tough casting
                pass

        unified_cols = list(self.UNIFIED_COLUMNS.keys())
        if not keep_extra:
            return df[unified_cols]

        # Preserve extra raw columns, but keep unified columns first.
        extra_cols = [c for c in df.columns if c not in unified_cols]
        return df[unified_cols + extra_cols]

    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Returns basic statistics about the test run.
        """
        pass
