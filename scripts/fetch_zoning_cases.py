"""
Fetches current rezoning case data from Raleigh's ArcGIS REST service and
writes it to data/cases.json.

Requires config/settings.py -> ZONING_CASES_LAYER_URL to be set (see
scripts/find_endpoint.py for how to find it).
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings


def build_query_url():
    if not settings.ZONING_CASES_LAYER_URL:
        raise RuntimeError(
            "ZONING_CASES_LAYER_URL is not set. Run scripts/find_endpoint.py "
            "first, then set it in config/settings.py or your .env file."
        )

    params = {
        "where": settings.EXTRA_WHERE_CLAUSE,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": str(settings.OUTPUT_SPATIAL_REFERENCE),
        "f": "geojson",
    }
    query_string = urllib.parse.urlencode(params)
    return f"{settings.ZONING_CASES_LAYER_URL}/query?{query_string}"


def fetch_cases():
    url = build_query_url()
    print(f"Querying: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    data = json.loads(raw)

    if "error" in data:
        raise RuntimeError(f"ArcGIS service returned an error: {data['error']}")

    features = data.get("features", [])
    print(f"Fetched {len(features)} features.")

    if features:
        sample_props = features[0].get("properties", {})
        print("Sample feature properties (use these to verify FIELD_MAP):")
        for k, v in sample_props.items():
            print(f"    {k}: {v}")

    return data


def main():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = fetch_cases()
    settings.RAW_CASES_FILE.write_text(json.dumps(data, indent=2))
    print(f"\nWrote raw data to {settings.RAW_CASES_FILE}")


if __name__ == "__main__":
    main()
