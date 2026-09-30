"""
AgriWis — Block 1: Data Ingestion Layer.

Endpoint: GET /api/plot-data?plot_code=SEH-14B&lat=23.20&lon=77.08

Combines satellite NDVI + weather forecast + soil health into one JSON
object. Each source degrades independently — if satellite auth isn't set
up yet, weather and soil still return real data. Block 2 reads `status`
per-source and adapts its recommendation logic accordingly.
"""
from datetime import date, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from ingestion import weather, satellite, soil
from recommendation import engine, llm
from disease import inference as disease_inference

app = Flask(__name__)
CORS(app)


@app.route("/")
def serve_landing():
    return send_from_directory("pages", "landing.html")


@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory("pages", "dashboard.html")


@app.route("/policy")
def serve_policy():
    return send_from_directory("pages", "policy-dashboard.html")


@app.route("/docs")
def serve_docs():
    return send_from_directory("pages", "api-docs.html")

PLOT_SIZE_DEG = 0.002  # ~200m box around the point, for the NDVI query


def _build_plot_data(plot_code: str, lat: float, lon: float) -> dict:
    bbox = [lon - PLOT_SIZE_DEG, lat - PLOT_SIZE_DEG, lon + PLOT_SIZE_DEG, lat + PLOT_SIZE_DEG]
    date_to = date.today().isoformat()
    date_from = (date.today() - timedelta(days=10)).isoformat()

    weather_data = weather.get_weather(lat, lon)
    ndvi_data = satellite.get_ndvi(bbox, date_from, date_to)
    soil_data = soil.get_soil_data(plot_code)

    return {
        "plot_code": plot_code,
        "location": {"lat": lat, "lon": lon},
        "satellite": ndvi_data,
        "weather": weather_data,
        "soil": soil_data,
        "data_completeness": _completeness(ndvi_data, weather_data, soil_data),
    }


@app.route("/api/plot-data", methods=["GET"])
def plot_data():
    plot_code = request.args.get("plot_code")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    if not plot_code or lat is None or lon is None:
        return jsonify({"error": "plot_code, lat, lon are required query params"}), 400

    return jsonify(_build_plot_data(plot_code, lat, lon))


@app.route("/api/advisory", methods=["GET"])
def advisory():
    """
    Block 1 + Block 2 chained: fetches raw data, runs it through the rules
    engine, and returns both the structured recommendation and a plain-
    language version. ?language=Hindi to get it phrased in another language.
    """
    plot_code = request.args.get("plot_code")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    language = request.args.get("language", "English")

    if not plot_code or lat is None or lon is None:
        return jsonify({"error": "plot_code, lat, lon are required query params"}), 400

    raw_data = _build_plot_data(plot_code, lat, lon)
    recommendation = engine.generate_recommendation(raw_data)
    plain_language = llm.phrase_advisory(recommendation, language)

    return jsonify({
        "raw_data": raw_data,
        "recommendation": recommendation,
        "advisory_text": plain_language,
    })


def _completeness(ndvi_data, weather_data, soil_data) -> str:
    sources_ok = sum(
        1 for d in (ndvi_data, weather_data, soil_data) if d.get("status") == "ok"
    )
    if sources_ok == 3:
        return "full"
    if sources_ok == 0:
        return "none"
    return "partial"


@app.route("/api/schema", methods=["GET"])
def schema():
    """
    Machine-readable description of every endpoint — this is what makes
    AgriWis a shareable data layer rather than a closed app. Another
    district, state, or BRICS partner's system can read this and know
    exactly how to plug into AgriWis's data without reading source code.
    """
    return jsonify({
        "name": "AgriWis Open Advisory API",
        "version": "1.0",
        "description": "Regenerative agriculture advisory data — satellite, "
                        "soil, weather, and disease detection, exposed as a "
                        "shared data layer for reuse by other districts, "
                        "states, or national agriculture systems.",
        "endpoints": [
            {
                "path": "/api/plot-data",
                "method": "GET",
                "params": {"plot_code": "string", "lat": "float", "lon": "float"},
                "returns": "Raw satellite (NDVI), soil, and weather data for one plot.",
            },
            {
                "path": "/api/advisory",
                "method": "GET",
                "params": {"plot_code": "string", "lat": "float", "lon": "float",
                           "language": "string (optional, default English)"},
                "returns": "Rules-based recommendation + plain-language advisory for one plot.",
            },
            {
                "path": "/api/district-summary",
                "method": "GET",
                "params": {},
                "returns": "Aggregated advisory data across every registered plot — "
                           "district/block-level trends and critical alerts.",
            },
            {
                "path": "/api/diagnose",
                "method": "POST",
                "params": {"image": "multipart file upload (leaf photo)"},
                "returns": "Disease classification + treatment. Currently supports "
                           "potato and tomato only.",
            },
        ],
        "data_sharing_note": "Any system consuming this API receives the same "
                              "structured schema regardless of region — the intent "
                              "is that a state or BRICS partner replacing the "
                              "underlying data sources (their own soil registry, "
                              "their own satellite provider) can expose the same "
                              "endpoints without changing this contract.",
    })


@app.route("/api/district-summary", methods=["GET"])
def district_summary():
    """
    Aggregates advisory data across every registered plot — this is the
    "digital public good" layer: a policymaker's view of the whole
    district rather than one farmer's field. Slower than a single-plot
    call since it loops through every plot's satellite+soil+weather calls;
    fine for a district of a few hundred plots, would need batching/caching
    at national scale.
    """
    all_plots = soil.get_all_plots()
    plot_results = []

    for plot in all_plots:
        raw_data = _build_plot_data(plot["plot_code"], plot["lat"], plot["lon"])
        recommendation = engine.generate_recommendation(raw_data)
        plot_results.append({
            "plot_code": plot["plot_code"],
            "block": plot["block"],
            "lat": plot["lat"],
            "lon": plot["lon"],
            "ndvi": raw_data["satellite"].get("ndvi_mean"),
            "nitrogen_level": raw_data["soil"].get("nitrogen_level"),
            "organic_carbon_pct": raw_data["soil"].get("organic_carbon_pct"),
            "flags": recommendation["flags"],
            "confidence": recommendation["confidence"],
        })

    # District-level rollups — the numbers a policymaker actually scans for
    ndvi_values = [p["ndvi"] for p in plot_results if p["ndvi"] is not None]
    low_nitrogen_count = sum(1 for p in plot_results if p["nitrogen_level"] == "low")
    critical_flags = [
        {"plot_code": p["plot_code"], "block": p["block"], "flag": f}
        for p in plot_results for f in p["flags"] if f["severity"] == "critical"
    ]

    blocks = {}
    for p in plot_results:
        blocks.setdefault(p["block"], []).append(p)

    block_summary = []
    for block_name, plots in blocks.items():
        block_ndvi = [p["ndvi"] for p in plots if p["ndvi"] is not None]
        block_summary.append({
            "block": block_name,
            "plot_count": len(plots),
            "avg_ndvi": round(sum(block_ndvi) / len(block_ndvi), 3) if block_ndvi else None,
            "low_nitrogen_plots": sum(1 for p in plots if p["nitrogen_level"] == "low"),
        })

    return jsonify({
        "total_plots": len(plot_results),
        "avg_ndvi": round(sum(ndvi_values) / len(ndvi_values), 3) if ndvi_values else None,
        "low_nitrogen_count": low_nitrogen_count,
        "critical_flags": critical_flags,
        "block_summary": block_summary,
        "plots": plot_results,
    })


@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    """
    Upload a leaf photo as multipart form-data under key 'image'.
    Currently supports potato and tomato only (see disease/treatment_lookup.py
    for why — PlantVillage doesn't cover wheat/soybean disease examples).
    """
    if "image" not in request.files:
        return jsonify({"error": "No 'image' file in request"}), 400

    image_file = request.files["image"]
    result = disease_inference.predict_disease(image_file)
    return jsonify(result)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
