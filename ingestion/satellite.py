"""
Satellite crop-health ingestion — Sentinel Hub Statistics API (NDVI).
Docs: https://docs.sentinel-hub.com/api/latest/api/statistical/
Requires an OAuth client id/secret from a free Sentinel Hub account.
"""
import os
import time
import requests

CLIENT_ID = os.environ.get("SENTINEL_HUB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SENTINEL_HUB_CLIENT_SECRET")
TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"

_token_cache = {"token": None, "expires_at": 0}

NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1 },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(s) {
  let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04);
  return {
    ndvi: [ndvi],
    dataMask: [s.dataMask]
  };
}
"""


def _get_token() -> str | None:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    if not CLIENT_ID or not CLIENT_SECRET:
        return None
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 3000) - 60
        return _token_cache["token"]
    except requests.RequestException:
        return None


def get_ndvi(bbox: list[float], date_from: str, date_to: str) -> dict:
    """
    bbox: [min_lon, min_lat, max_lon, max_lat] for the plot/field boundary.
    date_from/date_to: 'YYYY-MM-DD' — pick a recent ~10 day window
    (Sentinel-2 revisit is ~5 days; wider window avoids cloud gaps).
    """
    token = _get_token()
    if not token:
        return _fallback("missing_credentials_or_auth_failed")

    payload = {
        "input": {
            "bounds": {"bbox": bbox},
            "data": [{"type": "sentinel-2-l2a"}],
        },
        "aggregation": {
            "timeRange": {"from": f"{date_from}T00:00:00Z", "to": f"{date_to}T23:59:59Z"},
            "aggregationInterval": {"of": "P1D"},
            "evalscript": NDVI_EVALSCRIPT,
            "resx": 10,
            "resy": 10,
        },
    }

    try:
        resp = requests.post(
            STATS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if resp.status_code != 200:
         print("SENTINEL ERROR:", resp.text)
         resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return _fallback(f"request_failed: {e}")

    # Take the most recent day with usable (non-cloud-masked) data
    for entry in reversed(data.get("data", [])):
        stats = entry.get("outputs", {}).get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats")
        if stats and stats.get("sampleCount", 0) > 0:
            return {
                "status": "ok",
                "date": entry.get("interval", {}).get("from"),
                "ndvi_mean": round(stats.get("mean", 0), 3),
                "ndvi_min": round(stats.get("min", 0), 3),
                "ndvi_max": round(stats.get("max", 0), 3),
            }

    return _fallback("no_cloud_free_data_in_window")


def _fallback(reason: str) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "date": None,
        "ndvi_mean": None,
        "ndvi_min": None,
        "ndvi_max": None,
    }
