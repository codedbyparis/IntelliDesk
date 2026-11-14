"""Supervised ticket-category classifier, separate from the RAG retriever."""

from pathlib import Path

import joblib

from src import config


def build_classifier():
    """Create the TF-IDF and Logistic Regression ticket classifier."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                ),
            ),
            (
                "logistic_regression",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=42,
                ),
            ),
        ]
    )


def load_classifier(path=None):
    """Load the locally trained classifier or raise a clear missing-file error."""
    model_path = Path(path) if path is not None else config.CLASSIFIER_MODEL_PATH
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Ticket classifier not found at {model_path}. "
            "Run 'python train_classifier.py' first."
        )

    from sklearn.pipeline import Pipeline

    model = joblib.load(model_path)
    if (
        not isinstance(model, Pipeline)
        or "logistic_regression" not in model.named_steps
        or not hasattr(model, "predict_proba")
    ):
        raise ValueError(f"Invalid ticket classifier artifact: {model_path}")
    return model


def predict_category(question, model=None):
    """Return the predicted configured category and its probability."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("A non-empty issue description is required.")

    classifier = model if model is not None else load_classifier()
    probabilities = classifier.predict_proba([question])[0]
    best_index = int(probabilities.argmax())
    return str(classifier.classes_[best_index]), float(probabilities[best_index])
