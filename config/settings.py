"""
Central configuration for the Raleigh Zoning Change agent.

Most values here are placeholders until scripts/find_endpoint.py has been
run once and the real ArcGIS layer URL + field names are confirmed.
"""

import os
from pathlib import Path

# Load .env if present (simple manual loader, no extra dependency required)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


# ----------------------------------------------------------------------
# DATA SOURCE — fill this in after running scripts/find_endpoint.py
# ----------------------------------------------------------------------

# Full ArcGIS REST URL to the rezoning-cases FEATURE LAYER (not the parent
# MapServer/FeatureServer -- it must point at a specific layer id).
# Confirmed via scripts/find_endpoint.py by following the "Rezoning Request
# Viewer (Updated)" web map to its underlying data layer.
ZONING_CASES_LAYER_URL = os.environ.get(
    "ZONING_CASES_LAYER_URL",
    "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/"
    "Rezoning_Case_Boundaries_View/FeatureServer/0",
)

# Map of our internal field names -> the actual field names in the source
# layer. Confirmed from the live schema via scripts/find_endpoint.py.
FIELD_MAP = {
    "case_number": "ZONE_CASE",
    "status": "STATUS",
    "case_type": "CASE_TYPE",
    "requested_zoning": "ZON_REQ",
    "existing_zoning": "PrevZoning",
    "date_received": "StatusDate",
    "address": "Location",
}

# Wake County / Raleigh city limits filtering. The data source may already
# be Raleigh-only (most City of Raleigh layers are), in which case no extra
# filter is needed. If the layer covers all of Wake County, set this to a
# WHERE-clause fragment using a jurisdiction field, e.g. "JURISDICTION='RAL'"
EXTRA_WHERE_CLAUSE = os.environ.get("EXTRA_WHERE_CLAUSE", "1=1")

# Only cases whose STATUS (lowercased) is in this set, and whose StatusDate
# falls within RECENCY_WINDOW_DAYS, are shown on the map -- this is what
# makes the map reflect actual recent zoning *changes* rather than the
# full historical archive of every case ever filed (728+ going back to
# at least 2014) or in-progress applications with no outcome yet.
#
# Confirmed real STATUS values seen in the data include "Denied" -- add
# others (e.g. "Approved", "Withdrawn") here as you observe them. Run
# scripts/fetch_zoning_cases.py and check data/cases.json if you want to
# see the full set of distinct STATUS values currently in use.
DECIDED_STATUSES = {"approved", "denied", "withdrawn"}

RECENCY_WINDOW_DAYS = int(os.environ.get("RECENCY_WINDOW_DAYS", "90"))

# Raleigh's local ArcGIS services commonly use NC State Plane feet
# (WKID 2264 / ESRI 102719). We'll request output in WGS84 (4326) directly
# from the API via outSR so Google Maps can use lat/lng with no extra
# reprojection step.
OUTPUT_SPATIAL_REFERENCE = 4326


# ----------------------------------------------------------------------
# GOOGLE MAPS
# ----------------------------------------------------------------------

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

MAP_CENTER_LAT = 35.7796
MAP_CENTER_LNG = -78.6382
MAP_DEFAULT_ZOOM = 11


# ----------------------------------------------------------------------
# FILE PATHS
# ----------------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"

RAW_CASES_FILE = DATA_DIR / "cases.json"
SEEN_CASES_FILE = DATA_DIR / "seen.json"
MAP_DATA_JS_FILE = DOCS_DIR / "data.js"


# ----------------------------------------------------------------------
# GIT / PUBLISHING
# ----------------------------------------------------------------------

GIT_AUTO_COMMIT = os.environ.get("GIT_AUTO_COMMIT", "true").lower() == "true"
GIT_AUTO_PUSH = os.environ.get("GIT_AUTO_PUSH", "true").lower() == "true"
GIT_COMMIT_MESSAGE_PREFIX = "Daily zoning data update"
