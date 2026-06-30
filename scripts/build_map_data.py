"""
Reads data/cases.json (the latest raw pull), compares against
data/seen.json (cases recorded on previous runs), and:
  - adds any new/changed cases to the running history
  - writes docs/data.js, which the Google Map page (docs/index.html) loads
    directly as a <script> tag (simplest possible way to get data into a
    static GitHub Pages site without CORS/fetch complications).

This script is intentionally side-effect-light and re-runnable: running it
twice on the same input won't duplicate data, since cases are keyed by
case_number.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings


def get_field(props, internal_name):
    source_name = settings.FIELD_MAP.get(internal_name)
    if not source_name:
        return None
    return props.get(source_name)


def extract_point(geometry):
    """
    Returns a representative (lat, lng) point for a feature, regardless of
    whether the source geometry is a Point, Polygon, or MultiPolygon.
    For polygons we use the centroid of the first ring (good enough for
    map placement; not a precise centroid for irregular shapes, but Raleigh
    rezoning parcels are small enough this is visually fine).
    """
    if geometry is None:
        return None

    gtype = geometry.get("type")
    coords = geometry.get("coordinates")

    if gtype == "Point":
        lng, lat = coords[0], coords[1]
        return lat, lng

    if gtype == "Polygon":
        ring = coords[0]
        return _centroid_of_ring(ring)

    if gtype == "MultiPolygon":
        ring = coords[0][0]
        return _centroid_of_ring(ring)

    return None


def _centroid_of_ring(ring):
    lats = [pt[1] for pt in ring]
    lngs = [pt[0] for pt in ring]
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


def parse_status_date(raw_value):
    """
    StatusDate from the ArcGIS service comes through as a Unix timestamp in
    milliseconds (e.g. 1431432000000), not an ISO string. Converts to an
    ISO 8601 UTC string for consistent storage/display. Returns None if the
    value is missing or not parseable.
    """
    if raw_value is None:
        return None
    try:
        millis = float(raw_value)
        return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return str(raw_value)


def load_seen():
    if settings.SEEN_CASES_FILE.exists():
        return json.loads(settings.SEEN_CASES_FILE.read_text())
    return {}


def save_seen(seen):
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.SEEN_CASES_FILE.write_text(json.dumps(seen, indent=2))


def build_records(raw_geojson):
    records = []
    for feature in raw_geojson.get("features", []):
        props = feature.get("properties", {})
        point = extract_point(feature.get("geometry"))
        if point is None:
            continue

        case_number = get_field(props, "case_number")
        if not case_number:
            # Fall back to OBJECTID if no case number field was found/mapped
            case_number = props.get("OBJECTID") or props.get("FID")
        if not case_number:
            continue

        record = {
            "case_number": str(case_number),
            "status": get_field(props, "status"),
            "case_type": get_field(props, "case_type"),
            "existing_zoning": get_field(props, "existing_zoning"),
            "requested_zoning": get_field(props, "requested_zoning"),
            "date_received": parse_status_date(get_field(props, "date_received")),
            "address": get_field(props, "address"),
            "lat": point[0],
            "lng": point[1],
        }
        records.append(record)
    return records


def filter_recently_decided(records):
    """
    Keeps only cases that were *decided* (status in DECIDED_STATUSES, per
    settings) within the last RECENCY_WINDOW_DAYS. This is what makes the
    map show actual recent zoning *changes* rather than the full historical
    archive or in-progress applications.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - (
        settings.RECENCY_WINDOW_DAYS * 86400
    )
    kept = []
    for record in records:
        status = (record.get("status") or "").strip().lower()
        if status not in settings.DECIDED_STATUSES:
            continue
        date_str = record.get("date_received")
        if not date_str:
            continue
        try:
            record_ts = datetime.fromisoformat(date_str).timestamp()
        except ValueError:
            continue
        if record_ts >= cutoff:
            kept.append(record)
    return kept


def diff_against_seen(records, seen):
    new_or_changed = []
    updated_seen = dict(seen)

    for record in records:
        key = record["case_number"]
        previous = seen.get(key)

        if previous is None or previous.get("status") != record.get("status"):
            record["first_seen"] = (
                previous["first_seen"] if previous else
                datetime.now(timezone.utc).isoformat()
            )
            record["last_updated"] = datetime.now(timezone.utc).isoformat()
            new_or_changed.append(record)
            updated_seen[key] = record
        else:
            # unchanged -- keep the existing stored record as-is
            updated_seen[key] = previous

    return new_or_changed, updated_seen


def write_map_data_js(all_current_records):
    settings.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "generated_at": generated_at,
        "count": len(all_current_records),
        "cases": all_current_records,
    }

    js_content = (
        "// Auto-generated by scripts/build_map_data.py — do not edit by hand.\n"
        f"const ZONING_DATA = {json.dumps(payload, indent=2)};\n"
    )
    settings.MAP_DATA_JS_FILE.write_text(js_content)
    print(f"Wrote {len(all_current_records)} cases to {settings.MAP_DATA_JS_FILE}")


def main():
    if not settings.RAW_CASES_FILE.exists():
        raise RuntimeError(
            f"{settings.RAW_CASES_FILE} not found. Run "
            "scripts/fetch_zoning_cases.py first."
        )

    raw = json.loads(settings.RAW_CASES_FILE.read_text())
    records = build_records(raw)
    print(f"Parsed {len(records)} usable records from raw data.")

    seen = load_seen()
    new_or_changed, updated_seen = diff_against_seen(records, seen)
    print(f"{len(new_or_changed)} new or changed cases since last run.")

    save_seen(updated_seen)

    # The map only shows recently DECIDED cases (an actual zoning change
    # that happened), not the full historical archive or still-pending
    # applications. seen.json still tracks everything for diffing purposes.
    all_records = list(updated_seen.values())
    map_records = filter_recently_decided(all_records)
    print(
        f"{len(map_records)} cases decided in the last "
        f"{settings.RECENCY_WINDOW_DAYS} days (these go on the map)."
    )
    write_map_data_js(map_records)


if __name__ == "__main__":
    main()
