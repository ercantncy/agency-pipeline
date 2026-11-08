"""Data sources. `get_sources()` is the registry used by the CLI."""

from agency_pipeline.sources.base import Source
from agency_pipeline.sources.synthetic import get_sources

__all__ = ["Source", "get_sources"]
