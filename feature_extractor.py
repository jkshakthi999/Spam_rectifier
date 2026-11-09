"""
Module 3: Feature Extraction
Extracts features using TF-IDF Vectorizer and Count Vectorizer from Scikit-Learn.
Provides serialization, transformation, and vocabulary introspection.
"""

import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

DEFAULT_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
DEFAULT_TFIDF_PATH = os.path.join(DEFAULT_MODELS_DIR, "tfidf_vectorizer.joblib")


class FeatureExtractor:
    """
    Manages vectorization of preprocessed text into numerical feature matrices.
    """

    def __init__(
        self,
        method: str = "tfidf",
        ngram_range: tuple = (1, 2),
        max_features: int = 6000,
        min_df: int = 2,
        sublinear_tf: bool = True
    ):
        """
        method: 'tfidf' or 'count'
        ngram_range: (1, 2) unigrams + bigrams
        max_features: Maximum vocabulary size
        min_df: Minimum document frequency threshold
        """
        self.method = method.lower()
        self.ngram_range = ngram_range
        self.max_features = max_features
        self.min_df = min_df
        self.sublinear_tf = sublinear_tf
        self.vectorizer = self._init_vectorizer()
        self.is_fitted = False

    def _init_vectorizer(self):
        if self.method == "count":
            return CountVectorizer(
                ngram_range=self.ngram_range,
                max_features=self.max_features,
                min_df=self.min_df
            )
        # Default: TF-IDF
        return TfidfVectorizer(
            ngram_range=self.ngram_range,
            max_features=self.max_features,
            min_df=self.min_df,
            sublinear_tf=self.sublinear_tf
        )

    def fit(self, texts):
        """Fits the vectorizer on a collection of preprocessed text documents."""
        self.vectorizer.fit(texts)
        self.is_fitted = True
        return self

    def transform(self, texts):
        """Transforms preprocessed texts into feature matrix."""
        if not self.is_fitted:
            raise RuntimeError("FeatureExtractor must be fitted before calling transform().")
        return self.vectorizer.transform(texts)

    def fit_transform(self, texts):
        """Fits to data, then transforms it."""
        matrix = self.vectorizer.fit_transform(texts)
        self.is_fitted = True
        return matrix

    def get_feature_names(self):
        """Returns the learned vocabulary features."""
        if not self.is_fitted:
            return []
        return self.vectorizer.get_feature_names_out()

    def save(self, filepath: str = DEFAULT_TFIDF_PATH):
        """Saves fitted vectorizer to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.vectorizer, filepath)
        print(f"[FeatureExtractor] Vectorizer saved to {filepath}")

    @classmethod
    def load(cls, filepath: str = DEFAULT_TFIDF_PATH):
        """Loads a fitted vectorizer from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Vectorizer file not found at {filepath}")
        vectorizer = joblib.load(filepath)
        instance = cls()
        instance.vectorizer = vectorizer
        instance.is_fitted = True
        instance.ngram_range = getattr(vectorizer, "ngram_range", (1, 1))
        instance.max_features = getattr(vectorizer, "max_features", None)
        return instance


if __name__ == "__main__":
    docs = [
        "congratul won currency_sym num_token lakh call claim free cash",
        "hi team review attached report meeting scheduled tomorrow",
        "urgent account suspended click link verify kyc immediately"
    ]
    fe = FeatureExtractor(ngram_range=(1, 2), min_df=1)
    X = fe.fit_transform(docs)
    print(f"Shape: {X.shape}")
    print("Sample features:", fe.get_feature_names()[:10])
