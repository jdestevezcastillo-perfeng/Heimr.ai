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

    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """
        Parses the file and returns a standardized pandas DataFrame.
        Must ensure the following columns exist:
        - timestamp_dt (datetime)
        - elapsed (float, ms)
        - success (bool)
        """
        pass

    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Returns basic statistics about the test run.
        """
        pass
