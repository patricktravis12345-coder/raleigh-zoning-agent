"""
ONE-TIME DISCOVERY SCRIPT
=========================
Raleigh's rezoning case data lives behind an ArcGIS REST FeatureServer, but
we haven't confirmed the exact URL or field names from outside a browser
session. Run this script once, on your machine (it needs real internet
access), to find and confirm it.

What it does:
  1. Tries a list of candidate ArcGIS REST service URLs that are likely
     homes for Raleigh's rezoning/zoning case data.
  2. For each one that responds, prints the service name, layer names,
     and (for likely matches) the field list.
  3. You read the output, pick the correct layer URL, and paste it into
     config/settings.py as ZONING_CASES_LAYER_URL.

Usage:
    python scripts/find_endpoint.py
"""

import json
import sys
import urllib.request
import urllib.error

# Candidate base URLs worth checking. Raleigh hosts services on a couple of
# different ArcGIS Server instances, and also mirrors some as "Hosted"
# services discoverable through the open data Hub's item API.
CANDIDATE_MAPSERVERS = [
    "https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer",
    "https://maps.raleighnc.gov/arcgis/rest/services/Planning/CurrentDevelopmentActivity/MapServer",
    "https://maps.raleighnc.gov/arcgis/rest/services/Planning/RezoningCases/MapServer",
    "https://maps.raleighnc.gov/arcgis/rest/services/Planning/LandUseCases/MapServer",
    "https://mapstest.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer",
]

# The Hub item-search API is a reliable way to find the underlying
# FeatureServer for a dataset shown on data-ral.opendata.arcgis.com.
HUB_SEARCH_URL = (
    "https://www.arcgis.com/sharing/rest/search"
    "?q=Rezoning%20Raleigh%20owner%3Acoraleigh%20OR%20title%3ARezoning"
    "&f=json&num=20"
)
HUB_SEARCH_URL_BACKUP = (
    "https://www.arcgis.com/sharing/rest/search"
    "?q=Rezoning+AND+Raleigh&f=json&num=20"
)


def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"  [error] could not reach {url}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"  [error] response from {url} was not valid JSON")
        return None


def check_mapserver(url):
    print(f"\nChecking {url} ...")
    data = fetch_json(url + "?f=json")
    if not data:
        return
    if "error" in data:
        print(f"  -> error response: {data['error']}")
        return
    name = data.get("documentInfo", {}).get("Title") or data.get("mapName")
    print(f"  -> OK. Service/map name: {name}")
    layers = data.get("layers", [])
    for layer in layers:
        print(f"     layer {layer.get('id')}: {layer.get('name')}")


def inspect_layer_fields(mapserver_url, layer_id):
    layer_url = f"{mapserver_url}/{layer_id}?f=json"
    print(f"\nInspecting fields at {layer_url} ...")
    data = fetch_json(layer_url)
    if not data or "fields" not in data:
        print("  -> no field info returned")
        return
    print(f"  Layer: {data.get('name')}")
    print(f"  Geometry type: {data.get('geometryType')}")
    for f in data["fields"]:
        print(f"    {f['name']:30s} ({f['type']})  alias={f.get('alias')}")


def search_hub_for_rezoning():
    print("\nSearching ArcGIS Hub for Raleigh rezoning items...")
    webmap_ids = []
    for url in (HUB_SEARCH_URL, HUB_SEARCH_URL_BACKUP):
        data = fetch_json(url)
        if not data or "results" not in data:
            continue
        for item in data["results"]:
            title = item.get("title", "")
            if "rezon" in title.lower() or "zoning" in title.lower():
                print(f"  - {title}")
                print(f"      type: {item.get('type')}")
                print(f"      url:  {item.get('url')}")
                print(f"      id:   {item.get('id')}")
                if item.get("type") == "Web Map":
                    webmap_ids.append((title, item.get("id")))
    return webmap_ids


def inspect_webmaps(webmap_ids):
    """
    A 'Web Map' item doesn't expose data directly -- it's a saved map
    config that references the real FeatureServer layers underneath it.
    This pulls that config (item /data) and prints every layer URL it
    references, which is what we actually need.
    """
    seen_urls = set()
    for title, item_id in webmap_ids:
        data_url = f"https://www.arcgis.com/sharing/rest/content/items/{item_id}/data?f=json"
        print(f"\nInspecting web map '{title}' ({item_id}) ...")
        data = fetch_json(data_url)
        if not data:
            continue

        layers = data.get("operationalLayers", [])
        if not layers:
            print("  -> no operationalLayers found in this web map")
            continue

        for layer in layers:
            layer_title = layer.get("title")
            layer_url = layer.get("url")
            if layer_url and layer_url not in seen_urls:
                seen_urls.add(layer_url)
                print(f"  -> layer: {layer_title}")
                print(f"     url:   {layer_url}")

    return seen_urls


def main():
    print("=" * 70)
    print("Raleigh Rezoning Data Source Discovery")
    print("=" * 70)

    for url in CANDIDATE_MAPSERVERS:
        check_mapserver(url)

    webmap_ids = search_hub_for_rezoning()

    if webmap_ids:
        layer_urls = inspect_webmaps(webmap_ids)
        for layer_url in layer_urls:
            # layer_url is typically .../FeatureServer/0 -- fetch its field schema directly
            print(f"\nFetching field schema for {layer_url} ...")
            data = fetch_json(layer_url + "?f=json")
            if not data or "fields" not in data:
                print("  -> no field info returned (may need an access token, or isn't a layer URL)")
                continue
            print(f"  Layer: {data.get('name')}")
            print(f"  Geometry type: {data.get('geometryType')}")
            for f in data["fields"]:
                print(f"    {f['name']:30s} ({f['type']})  alias={f.get('alias')}")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. From the output above, identify the layer that represents REZONING
   CASES (not the static current-zoning-districts layer). Look for field
   names like CASE_NUMBER, CASESTATUS, CASETYPE, REQUEST, DATE_RECEIVED,
   etc. -- attribute fields that describe an application/case, not just a
   zoning code.

2. Once you find it, note the full layer URL, e.g.:
     https://maps.raleighnc.gov/arcgis/rest/services/Planning/X/MapServer/2

3. Open config/settings.py and set:
     ZONING_CASES_LAYER_URL = "<that full URL>"

4. Also note which fields map to:
     - case number / id
     - case status (approved / pending / withdrawn)
     - old zoning -> new zoning (or just "requested zoning")
     - date (received, decision, or effective)
     - address or location text (if present; geometry gives us the shape)

   Put these in config/settings.py as FIELD_MAP so fetch_zoning_cases.py
   knows what to pull.

5. Then run: python scripts/fetch_zoning_cases.py
   to do a real pull and confirm everything end-to-end.
""")


if __name__ == "__main__":
    main()