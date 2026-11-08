"""CSV importers: typical platform UI exports -> frames in the exact `raw` table shapes.

Each module exposes `parse(path, client_id="audit") -> DataFrame`. The export layouts are based
on typical files and must be verified against real exports from the agency.
"""

from agency_pipeline.sources.csv_exports import ga4, google_ads, gsc, meta_ads
from agency_pipeline.sources.csv_exports._common import ExportError

__all__ = ["ExportError", "ga4", "google_ads", "gsc", "meta_ads"]
