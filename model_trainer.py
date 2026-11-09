"""
Module 4: Model Training & Evaluation
Trains and compares:
1. Naive Bayes (MultinomialNB)
2. Support Vector Machines (LinearSVC with Calibrated probabilities / SVC)

Computes metrics (Accuracy, Precision, Recall, F1, Confusion Matrix),
compares performance, and persists models to disk.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

# Safe console encoding for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.dataset_loader import DatasetLoader
from src.text_preprocessor import TextPreprocessor
from src.feature_extractor import FeatureExtractor

DEFAULT_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))


class ModelTrainer:
    """
    Trains, evaluates, compares, and saves Naive Bayes and SVM classifiers.
    """

    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self.preprocessor = TextPreprocessor()
        self.feature_extractor = FeatureExtractor(ngram_range=(1, 2), max_features=6000, min_df=2)
        
        self.nb_model = None
        self.svm_model = None
        self.metrics = {}

    def prepare_data(self, df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
        """
        Cleans text, encodes labels (ham=0, spam=1), extracts features,
        and splits into stratified train/test sets.
        """
        print("[ModelTrainer] Cleaning text content...")
        cleaned_texts = [self.preprocessor.clean_text(t) for t in df["text"]]
        
        # Binary target: 1 for spam, 0 for ham
        y = (df["label"].str.lower() == "spam").astype(int).values

        print(f"[ModelTrainer] Extracting TF-IDF features across {len(cleaned_texts)} documents...")
        X = self.feature_extractor.fit_transform(cleaned_texts)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        print(f"[ModelTrainer] Train set: {X_train.shape[0]} samples | Test set: {X_test.shape[0]} samples")
        return X_train, X_test, y_train, y_test

    def train_naive_bayes(self, X_train, y_train, alpha: float = 0.1):
        """Trains Multinomial Naive Bayes."""
        print(f"[ModelTrainer] Training Multinomial Naive Bayes (alpha={alpha})...")
        nb = MultinomialNB(alpha=alpha)
        nb.fit(X_train, y_train)
        self.nb_model = nb
        return nb

    def train_svm(self, X_train, y_train, C: float = 1.0):
        """
        Trains Support Vector Machine (LinearSVC wrapped in CalibratedClassifierCV
        to generate well-calibrated class probability estimates).
        """
        print(f"[ModelTrainer] Training Support Vector Machine (LinearSVC, C={C})...")
        base_svc = LinearSVC(C=C, random_state=42, max_iter=2000)
        calibrated_svm = CalibratedClassifierCV(estimator=base_svc, cv=3)
        calibrated_svm.fit(X_train, y_train)
        self.svm_model = calibrated_svm
        return calibrated_svm

    @staticmethod
    def _evaluate(model, X_test, y_test, model_name: str) -> dict:
        """Calculates comprehensive classification metrics."""
        y_pred = model.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, target_names=["HAM", "SPAM"], output_dict=True)

        return {
            "model_name": model_name,
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "confusion_matrix": {
                "true_negative": cm[0][0],
                "false_positive": cm[0][1],
                "false_negative": cm[1][0],
                "true_positive": cm[1][1]
            },
            "classification_report": report
        }

    def train_and_evaluate_all(self, df: pd.DataFrame = None):
        """Executes full pipeline: data prep, training both NB and SVM, evaluation, and saving."""
        if df is None:
            loader = DatasetLoader()
            df = loader.load_dataset()

        X_train, X_test, y_train, y_test = self.prepare_data(df)

        # 1. Train Naive Bayes
        self.train_naive_bayes(X_train, y_train)
        nb_metrics = self._evaluate(self.nb_model, X_test, y_test, "Naive Bayes (MultinomialNB)")

        # 2. Train SVM
        self.train_svm(X_train, y_train)
        svm_metrics = self._evaluate(self.svm_model, X_test, y_test, "Support Vector Machine (Linear SVM)")

        self.metrics = {
            "naive_bayes": nb_metrics,
            "svm": svm_metrics,
            "dataset_total": len(df),
            "features_count": X_train.shape[1],
            "spam_count": int(np.sum(df["label"].str.lower() == "spam")),
            "ham_count": int(np.sum(df["label"].str.lower() == "ham"))
        }

        self.save_artifacts()
        self.print_comparison_summary()
        return self.metrics

    def save_artifacts(self):
        """Saves models, vectorizer, and evaluation metrics."""
        # Save vectorizer
        vec_path = os.path.join(self.models_dir, "tfidf_vectorizer.joblib")
        self.feature_extractor.save(vec_path)

        # Save Naive Bayes
        nb_path = os.path.join(self.models_dir, "naive_bayes_model.joblib")
        joblib.dump(self.nb_model, nb_path)
        print(f"[ModelTrainer] Naive Bayes model saved to {nb_path}")

        # Save SVM
        svm_path = os.path.join(self.models_dir, "svm_model.joblib")
        joblib.dump(self.svm_model, svm_path)
        print(f"[ModelTrainer] SVM model saved to {svm_path}")

        # Save Metrics metadata
        meta_path = os.path.join(self.models_dir, "model_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)
        print(f"[ModelTrainer] Model metadata saved to {meta_path}")

    def print_comparison_summary(self):
        """Displays side-by-side performance table."""
        nb = self.metrics["naive_bayes"]
        svm = self.metrics["svm"]

        print("\n" + "=" * 65)
        print("          MODEL PERFORMANCE COMPARISON (TEST SET)")
        print("=" * 65)
        print(f"{'Metric':<20} | {'Naive Bayes':<18} | {'Support Vector Machine':<20}")
        print("-" * 65)
        print(f"{'Accuracy':<20} | {nb['accuracy'] * 100:>6.2f}%            | {svm['accuracy'] * 100:>6.2f}%")
        print(f"{'Precision (Spam)':<20} | {nb['precision'] * 100:>6.2f}%            | {svm['precision'] * 100:>6.2f}%")
        print(f"{'Recall (Spam)':<20} | {nb['recall'] * 100:>6.2f}%            | {svm['recall'] * 100:>6.2f}%")
        print(f"{'F1-Score (Spam)':<20} | {nb['f1_score'] * 100:>6.2f}%            | {svm['f1_score'] * 100:>6.2f}%")
        print("-" * 65)
        print("Confusion Matrices:")
        print(f"  Naive Bayes -> TN: {nb['confusion_matrix']['true_negative']}, FP: {nb['confusion_matrix']['false_positive']}, FN: {nb['confusion_matrix']['false_negative']}, TP: {nb['confusion_matrix']['true_positive']}")
        print(f"  SVM         -> TN: {svm['confusion_matrix']['true_negative']}, FP: {svm['confusion_matrix']['false_positive']}, FN: {svm['confusion_matrix']['false_negative']}, TP: {svm['confusion_matrix']['true_positive']}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.train_and_evaluate_all()
