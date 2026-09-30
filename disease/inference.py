"""
Disease detection inference — loads the model trained via
train_model_colab.py and predicts on an uploaded leaf image.

Requires two files (produced by the Colab script) in this same folder:
  - agriwis_disease_model.keras
  - class_names.json

Until you've trained and placed those files, this module returns a
clear "model_not_loaded" status rather than crashing — so the rest of
the app keeps working while you finish training.
"""
import os
import json

from .treatment_lookup import get_treatment

MODEL_PATH = os.path.join(os.path.dirname(__file__), "agriwis_disease_model.keras")
CLASS_NAMES_PATH = os.path.join(os.path.dirname(__file__), "class_names.json")
IMG_SIZE = 224

_model = None
_class_names = None


def _load_model():
    global _model, _class_names
    if _model is not None:
        return

    if not os.path.exists(MODEL_PATH) or not os.path.exists(CLASS_NAMES_PATH):
        return  # stays None — handled by predict()

    import tensorflow as tf  # imported lazily so app.py doesn't need TF
    # installed just to run Block 1/2 before the model is ready

    _model = tf.keras.models.load_model(MODEL_PATH)
    with open(CLASS_NAMES_PATH) as f:
        _class_names = json.load(f)


def predict_disease(image_file) -> dict:
    """
    image_file: a file-like object (e.g. Flask's request.files['image']).
    """
    _load_model()

    if _model is None:
        return {
            "status": "model_not_loaded",
            "message": "Disease model not trained/placed yet. Run "
                       "train_model_colab.py and add the output files to "
                       "disease/.",
        }

    import tensorflow as tf
    import numpy as np
    from PIL import Image

    try:
        img = Image.open(image_file).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
        arr = np.array(img)
        arr = tf.keras.applications.mobilenet_v2.preprocess_input(arr)
        arr = np.expand_dims(arr, axis=0)
    except Exception as e:
        return {"status": "invalid_image", "message": str(e)}

    predictions = _model.predict(arr, verbose=0)[0]
    top_idx = int(np.argmax(predictions))
    confidence = float(predictions[top_idx])
    class_name = _class_names[top_idx]

    result = get_treatment(class_name)
    result["confidence"] = round(confidence, 3)
    # Be honest about low-confidence predictions rather than presenting
    # them as certain — this matters more here than in the rules engine,
    # since a wrong disease call could cost a farmer money.
    if confidence < 0.6:
        result["low_confidence_warning"] = (
            "Model isn't confident about this prediction — consider a "
            "second photo or manual inspection."
        )

    return result
