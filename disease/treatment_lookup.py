"""
Treatment lookup — maps model class output to plain-language treatment advice.

Scoped to potato and tomato classes: these are PlantVillage's best-covered
crops that also genuinely grow in Sehore/MP. Wheat and soybean disease
detection is NOT covered by this model — PlantVillage doesn't have
sufficient disease examples for those crops. Say this plainly if asked;
don't let the UI imply otherwise.
"""

TREATMENTS = {
    "Potato___Early_blight": {
        "disease": "Potato Early Blight",
        "treatment": "Remove and destroy infected leaves. Apply a copper-based "
                      "fungicide every 7-10 days. Avoid overhead watering.",
        "severity": "moderate",
    },
    "Potato___Late_blight": {
        "disease": "Potato Late Blight",
        "treatment": "Act fast — this spreads quickly. Remove infected plants "
                      "entirely and apply fungicide (e.g. chlorothalonil) to "
                      "remaining crop immediately.",
        "severity": "critical",
    },
    "Potato___healthy": {
        "disease": "Healthy",
        "treatment": "No action needed. Continue regular monitoring.",
        "severity": "none",
    },
    "Tomato___Bacterial_spot": {
        "disease": "Tomato Bacterial Spot",
        "treatment": "Remove infected leaves. Apply copper-based bactericide. "
                      "Avoid working in the field when plants are wet.",
        "severity": "moderate",
    },
    "Tomato___Early_blight": {
        "disease": "Tomato Early Blight",
        "treatment": "Prune lower leaves touching soil. Apply fungicide "
                      "(mancozeb or chlorothalonil) at first sign.",
        "severity": "moderate",
    },
    "Tomato___Late_blight": {
        "disease": "Tomato Late Blight",
        "treatment": "Remove and destroy infected plants immediately — highly "
                      "contagious. Apply fungicide to remaining healthy plants.",
        "severity": "critical",
    },
    "Tomato___Leaf_Mold": {
        "disease": "Tomato Leaf Mold",
        "treatment": "Improve air circulation, reduce humidity around plants. "
                      "Apply fungicide if it spreads past a few leaves.",
        "severity": "moderate",
    },
    "Tomato___Septoria_leaf_spot": {
        "disease": "Tomato Septoria Leaf Spot",
        "treatment": "Remove affected lower leaves. Apply fungicide, mulch "
                      "soil to prevent spore splash-back.",
        "severity": "moderate",
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "disease": "Spider Mite Infestation",
        "treatment": "Spray with insecticidal soap or neem oil. Increase "
                      "humidity around plants — mites thrive in dry conditions.",
        "severity": "moderate",
    },
    "Tomato___Target_Spot": {
        "disease": "Tomato Target Spot",
        "treatment": "Remove infected foliage. Apply fungicide, ensure proper "
                      "plant spacing for airflow.",
        "severity": "moderate",
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "disease": "Tomato Yellow Leaf Curl Virus",
        "treatment": "No cure — remove and destroy infected plants to stop "
                      "spread. Control whiteflies (the carrier) with sticky "
                      "traps or insecticide.",
        "severity": "critical",
    },
    "Tomato___Tomato_mosaic_virus": {
        "disease": "Tomato Mosaic Virus",
        "treatment": "No cure — remove infected plants. Wash hands/tools "
                      "between plants to avoid spreading.",
        "severity": "critical",
    },
    "Tomato___healthy": {
        "disease": "Healthy",
        "treatment": "No action needed. Continue regular monitoring.",
        "severity": "none",
    },
}

SUPPORTED_CROPS = ["Potato", "Tomato"]


def get_treatment(class_name: str) -> dict:
    result = TREATMENTS.get(class_name)
    if result:
        return {**result, "status": "ok", "raw_class": class_name}
    return {
        "status": "unsupported",
        "disease": None,
        "treatment": f"This crop/disease isn't in AgriWis's current model. "
                      f"Supported crops: {', '.join(SUPPORTED_CROPS)}.",
        "severity": None,
        "raw_class": class_name,
    }
