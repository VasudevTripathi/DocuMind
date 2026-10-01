from pathlib import Path
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset" / "documents.csv"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

def train():
    print(f"Loading dataset from: {DATASET_PATH}")
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset file not found at {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    print(f"Loaded {len(df)} samples across {df['label'].nunique()} classes:")
    print(df['label'].value_counts())

    X = df["text"]
    y = df["label"]

    # Stratified train/test split for reliable evaluation across all 7 classes
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )

    print(f"\nTraining set size: {len(X_train)}, Test set size: {len(X_test)}")

    # 1. Feature extraction with TF-IDF (unigrams & bigrams, sublinear term frequency)
    eval_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True
    )
    X_train_vec = eval_vectorizer.fit_transform(X_train)
    X_test_vec = eval_vectorizer.transform(X_test)

    # 2. Logistic Regression Classifier with reproducible random state
    eval_classifier = LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42
    )
    eval_classifier.fit(X_train_vec, y_train)

    # 3. Model Evaluation on held-out test data
    y_pred = eval_classifier.predict(X_test_vec)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "="*50)
    print("MODEL EVALUATION ON TEST SET (random_state=42):")
    print("="*50)
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f} (weighted)")
    print(f"Recall:    {recall:.4f} (weighted)")
    print(f"F1-Score:  {f1:.4f} (weighted)")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion Matrix:")
    print(cm)
    print("="*50)

    # 4. Train final production model on the complete curated dataset to maximize vocabulary coverage
    print("\nTraining final classifier on complete dataset...")
    final_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True
    )
    X_all_vec = final_vectorizer.fit_transform(X)

    final_classifier = LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42
    )
    final_classifier.fit(X_all_vec, y)

    # 5. Save model artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    vectorizer_path = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
    classifier_path = ARTIFACTS_DIR / "document_classifier.joblib"

    joblib.dump(final_vectorizer, vectorizer_path)
    joblib.dump(final_classifier, classifier_path)

    print(f"Saved TF-IDF Vectorizer to: {vectorizer_path}")
    print(f"Saved Document Classifier to: {classifier_path}")
    print("\nModel training and artifact persistence complete!")

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

if __name__ == "__main__":
    train()
