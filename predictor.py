"""
Module 5: Spam Detection & Inference
Performs real-time classification on new emails/messages using
the trained Naive Bayes or Support Vector Machine models.
"""

import os
import sys
import joblib
import numpy as np

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

from src.text_preprocessor import TextPreprocessor

DEFAULT_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))


class SpamPredictor:
    """
    Inference engine to classify email content as SPAM or HAM.
    """

    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR, default_algorithm: str = "svm"):
        self.models_dir = models_dir
        self.default_algorithm = default_algorithm.lower()
        self.preprocessor = TextPreprocessor()
        
        self.vectorizer = None
        self.nb_model = None
        self.svm_model = None
        self._load_artifacts()

    def _load_artifacts(self):
        vec_path = os.path.join(self.models_dir, "tfidf_vectorizer.joblib")
        nb_path = os.path.join(self.models_dir, "naive_bayes_model.joblib")
        svm_path = os.path.join(self.models_dir, "svm_model.joblib")

        if not os.path.exists(vec_path):
            raise FileNotFoundError(
                f"Missing vectorizer at {vec_path}. Please run train.py first."
            )

        self.vectorizer = joblib.load(vec_path)

        if os.path.exists(nb_path):
            self.nb_model = joblib.load(nb_path)
        if os.path.exists(svm_path):
            self.svm_model = joblib.load(svm_path)

    def _get_model(self, algorithm: str):
        algo = algorithm.lower()
        if algo in ("svm", "support_vector_machine"):
            if not self.svm_model:
                raise RuntimeError("SVM model not loaded.")
            return self.svm_model, "Support Vector Machine"
        elif algo in ("nb", "naive_bayes", "multinomial_nb"):
            if not self.nb_model:
                raise RuntimeError("Naive Bayes model not loaded.")
            return self.nb_model, "Naive Bayes"
        else:
            # Default fallback
            if self.svm_model:
                return self.svm_model, "Support Vector Machine"
            return self.nb_model, "Naive Bayes"

    def predict(self, email_text: str, algorithm: str = None) -> dict:
        """
        Classifies single email text.
        Returns:
            dict containing:
            - email: original raw email text
            - cleaned_text: preprocessed token sequence
            - prediction: 'SPAM' or 'HAM'
            - is_spam: bool (True if SPAM)
            - confidence: float percentage (e.g. 98.42)
            - spam_probability: float (0.0 to 1.0)
            - ham_probability: float (0.0 to 1.0)
            - algorithm_used: string
            - trigger_words: list of detected spam tokens
        """
        if not email_text or not email_text.strip():
            return {
                "email": email_text,
                "cleaned_text": "",
                "prediction": "HAM",
                "is_spam": False,
                "confidence": 50.0,
                "spam_probability": 0.0,
                "ham_probability": 1.0,
                "algorithm_used": algorithm or self.default_algorithm,
                "trigger_words": []
            }

        algo = algorithm or self.default_algorithm
        model, model_name = self._get_model(algo)

        # Preprocess
        cleaned = self.preprocessor.clean_text(email_text)
        
        # Transform features
        X_vec = self.vectorizer.transform([cleaned])

        # Predict class
        pred_label_idx = model.predict(X_vec)[0]
        is_spam = bool(pred_label_idx == 1)
        prediction_str = "SPAM" if is_spam else "HAM"

        # Predict probabilities
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_vec)[0]
            ham_prob = float(probs[0])
            spam_prob = float(probs[1])
            confidence = (spam_prob if is_spam else ham_prob) * 100.0
        else:
            spam_prob = 1.0 if is_spam else 0.0
            ham_prob = 0.0 if is_spam else 1.0
            confidence = 100.0

        # Identify trigger words / features that contributed
        feature_names = self.vectorizer.get_feature_names_out()
        non_zero_indices = X_vec.nonzero()[1]
        active_tokens = [feature_names[i] for i in non_zero_indices]

        # Common spam keywords to highlight if present
        known_spam_triggers = {
            'won', 'win', 'winner', 'prize', 'cash', 'free', 'claim', 'urgent', 'lakh',
            'crore', 'lottery', 'reward', 'currency_sym', 'phone_num', 'http_url',
            'congratul', 'selected', 'guaranteed', 'refund', 'kyc', 'suspend',
            'jackpot', 'voucher', 'credit', 'transfer', 'offer', 'exclusive'
        }
        trigger_words = [t for t in active_tokens if t in known_spam_triggers or any(k in t for k in known_spam_triggers)]

        return {
            "email": email_text,
            "cleaned_text": cleaned,
            "prediction": prediction_str,
            "is_spam": is_spam,
            "confidence": round(confidence, 2),
            "spam_probability": round(spam_prob, 4),
            "ham_probability": round(ham_prob, 4),
            "algorithm_used": model_name,
            "trigger_words": sorted(list(set(trigger_words)))
        }

    def format_output(self, email_text: str, algorithm: str = None) -> str:
        """
        Formats output according to user specification:
        Email:
        "Congratulations! You won ₹10 lakh"

        Prediction:
        SPAM
        """
        res = self.predict(email_text, algorithm=algorithm)
        output = (
            f'Email:\n"{res["email"]}"\n\n'
            f'Prediction:\n{res["prediction"]}\n\n'
            f'Algorithm: {res["algorithm_used"]}\n'
            f'Confidence: {res["confidence"]}%\n'
            f'Spam Probability: {res["spam_probability"] * 100:.2f}%\n'
            f'Trigger Tokens: {", ".join(res["trigger_words"]) if res["trigger_words"] else "None"}'
        )
        return output


if __name__ == "__main__":
    predictor = SpamPredictor()
    test_email = "Congratulations! You won ₹10 lakh"
    print("=" * 40)
    print(predictor.format_output(test_email, algorithm="svm"))
    print("=" * 40)
    print(predictor.format_output(test_email, algorithm="naive_bayes"))
    print("=" * 40)
