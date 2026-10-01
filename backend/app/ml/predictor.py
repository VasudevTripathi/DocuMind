from pathlib import Path
from typing import Dict, Any, Optional
import joblib
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
VECTORIZER_PATH = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
CLASSIFIER_PATH = ARTIFACTS_DIR / "document_classifier.joblib"

_vectorizer = None
_classifier = None

def load_artifacts():
    """Loads TF-IDF vectorizer and classifier once into memory."""
    global _vectorizer, _classifier
    if _vectorizer is not None and _classifier is not None:
        return _vectorizer, _classifier

    if not VECTORIZER_PATH.exists() or not CLASSIFIER_PATH.exists():
        raise FileNotFoundError(
            "Model artifacts missing. Expected artifacts at "
            f"'{VECTORIZER_PATH}' and '{CLASSIFIER_PATH}'. "
            "Please run 'python -m app.ml.train' to train and generate artifacts."
        )

    _vectorizer = joblib.load(VECTORIZER_PATH)
    _classifier = joblib.load(CLASSIFIER_PATH)
    return _vectorizer, _classifier

def predict_category(text: str) -> Dict[str, Any]:
    """
    Predicts document category and associated confidence probability using
    the locally trained TF-IDF + Logistic Regression model.

    Returns:
    {
        "category": str,
        "confidence": float
    }
    """
    if not text or not text.strip():
        return {
            "category": "General",
            "confidence": 0.0
        }

    vectorizer, classifier = load_artifacts()

    vec = vectorizer.transform([text])
    probabilities = classifier.predict_proba(vec)[0]
    best_idx = int(np.argmax(probabilities))

    category = str(classifier.classes_[best_idx])
    confidence = float(probabilities[best_idx])

    return {
        "category": category,
        "confidence": round(confidence, 4)
    }
