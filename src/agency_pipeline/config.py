"""Client registry and filesystem paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "clients.yml"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
WAREHOUSE_ENV_VAR = "AGENCY_PIPELINE_WAREHOUSE"

GLOBAL_SEED = 42


def warehouse_path() -> Path:
    """Warehouse location; honours AGENCY_PIPELINE_WAREHOUSE at call time (used by tests)."""
    override = os.environ.get(WAREHOUSE_ENV_VAR)
    return Path(override) if override else DATA_DIR / "warehouse.duckdb"


WAREHOUSE_PATH = warehouse_path()


@dataclass(frozen=True)
class AgencyBrand:
    name: str
    primary_color: str
    logo_text: str


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    client_name: str
    agency_brand: AgencyBrand
    currency: str
    google_ads_customer_id: str
    meta_account_id: str
    ga4_property_id: str
    gsc_site_url: str
    scenario: str


def load_clients(path: Path = CONFIG_PATH) -> list[ClientConfig]:
    """Parse clients.yml into ClientConfig objects."""
    raw = yaml.safe_load(Path(path).read_text())
    clients = []
    for entry in raw["clients"]:
        entry = dict(entry)
        entry["agency_brand"] = AgencyBrand(**entry["agency_brand"])
        clients.append(ClientConfig(**entry))
    return clients
