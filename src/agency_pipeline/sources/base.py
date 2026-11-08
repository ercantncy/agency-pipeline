"""Abstract source interface; real connectors implement the same contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from agency_pipeline.config import ClientConfig


class Source(ABC):
    """A raw data source that lands one table in the `raw` schema."""

    #: Short identifier, e.g. "google_ads".
    name: str
    #: Target table in schema `raw`, e.g. "google_ads_campaign_daily".
    table: str

    @abstractmethod
    def extract(self, client: ClientConfig, start: date, end: date) -> pd.DataFrame:
        """Return one row per API record for `client` between `start` and `end` (inclusive).

        The frame must contain every source column of `raw.<table>` plus `client_id`.
        """
