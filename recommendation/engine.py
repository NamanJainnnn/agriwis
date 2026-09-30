"""
AgriWis — Block 2: Recommendation Engine.

Deterministic rules engine first (defensible, explainable, works with
partial data). An optional LLM phrasing layer sits on top (see llm.py) —
but the actual decision logic lives here, not in a prompt. This matters
for judging: you can explain exactly why a recommendation was made.

Input: the JSON dict produced by Block 1 (app.py's /api/plot-data).
Output: a list of flags + one primary recommendation + confidence level.
"""


def generate_recommendation(plot_data: dict) -> dict:
    satellite = plot_data.get("satellite", {})
    weather = plot_data.get("weather", {})
    soil = plot_data.get("soil", {})

    flags = []
    actions = []

    # --- Soil-based rules ---
    if soil.get("status") == "ok":
        if soil.get("nitrogen_level") == "low":
            flags.append({"type": "soil_nitrogen", "severity": "warning",
                           "message": "Nitrogen is low"})
            actions.append("Apply nitrogen-fixing cover crop (e.g. legumes) next rotation "
                            "instead of synthetic fertiliser alone.")
        if soil.get("organic_carbon_pct", 1) < 0.4:
            flags.append({"type": "organic_carbon", "severity": "warning",
                           "message": "Organic carbon below healthy threshold (0.4%)"})
            actions.append("Add composted organic matter or green manure to rebuild soil carbon.")
        if soil.get("ph", 7) < 6.0 or soil.get("ph", 7) > 8.0:
            flags.append({"type": "soil_ph", "severity": "warning",
                           "message": f"pH ({soil.get('ph')}) is outside optimal 6.0–8.0 range"})
            actions.append("Consider soil amendment (lime if acidic, gypsum if alkaline) "
                            "before next sowing.")

    # --- Satellite (NDVI) rules ---
    if satellite.get("status") == "ok":
        ndvi = satellite.get("ndvi_mean", 0)
        if ndvi < 0.3:
            flags.append({"type": "crop_health", "severity": "critical",
                           "message": f"NDVI ({ndvi}) indicates poor crop vigour"})
            actions.append("Inspect field in person — low NDVI may indicate water stress, "
                            "pest damage, or nutrient deficiency not visible in soil data alone.")
        elif ndvi < 0.5:
            flags.append({"type": "crop_health", "severity": "watch",
                           "message": f"NDVI ({ndvi}) is moderate — monitor over next cycle"})

    # --- Weather-based rules (only if available) ---
    irrigation_advice = None
    if weather.get("status") == "ok":
        rain = weather.get("rain_next_72h_mm", 0)
        if rain and rain > 10:
            irrigation_advice = ("Hold irrigation — "
                                  f"{rain}mm rain expected in the next 72 hours.")
        elif soil.get("status") == "ok" and rain is not None and rain < 5:
            irrigation_advice = "Low rain expected — plan irrigation for the next 2–3 days."
    else:
        flags.append({"type": "weather_unavailable", "severity": "info",
                       "message": "Weather forecast unavailable — irrigation timing not advised"})

    if irrigation_advice:
        actions.append(irrigation_advice)

    # --- Confidence reflects actual data completeness, never overstated ---
    completeness = plot_data.get("data_completeness", "none")
    confidence = {"full": "high", "partial": "medium", "none": "low"}.get(completeness, "low")

    if not actions:
        actions.append("No urgent action flagged — conditions within normal range based on "
                        "available data.")

    return {
        "plot_code": plot_data.get("plot_code"),
        "flags": flags,
        "recommended_actions": actions,
        "confidence": confidence,
        "based_on": {
            "satellite": satellite.get("status"),
            "soil": soil.get("status"),
            "weather": weather.get("status"),
        },
    }
