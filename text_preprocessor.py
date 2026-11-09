"""
Module 2: Text Cleaning & Preprocessing
Handles tokenization, regex cleaning, normalization of URLs/emails/currencies,
stopword removal, and stemming using NLTK.
"""

import re
import string
import sys
import unicodedata

# Ensure stdout supports UTF-8 on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

# Built-in fallback stopwords list in case NLTK data path issues occur
FALLBACK_STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    "aren't", 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but',
    'by', 'can', 'couldn', "couldn't", 'd', 'did', 'didn', "didn't", 'do', 'does', 'doesn', "doesn't",
    'doing', 'don', "don't", 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn',
    "hadn't", 'has', 'hasn', "hasn't", 'have', 'haven', "haven't", 'having', 'he', 'her', 'here',
    'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn', "isn't",
    'it', "it's", 'its', 'itself', 'just', 'll', 'm', 'ma', 'me', 'mightn', "mightn't", 'more', 'most',
    'mustn', "mustn't", 'my', 'myself', 'needn', "needn't", 'no', 'nor', 'not', 'now', 'o', 'of', 'off',
    'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 're', 's',
    'same', 'shan', "shan't", 'she', "she's", 'should', "should've", 'shouldn', "shouldn't", 'so',
    'some', 'such', 't', 'than', 'that', "that'll", 'the', 'their', 'theirs', 'them', 'themselves',
    'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up',
    've', 'very', 'was', 'wasn', "wasn't", 'we', 'were', 'weren', "weren't", 'what', 'when', 'where',
    'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'won', "won't", 'wouldn', "wouldn't", 'y',
    'you', "you'd", "you'll", "you're", "you've", 'your', 'yours', 'yourself', 'yourselves'
}

# Preserve certain negation/urgency words from being filtered if needed
PRESERVED_WORDS = {'not', 'no', 'won', 'free', 'urgent', 'claim', 'cash', 'prize', 'winner'}

class TextPreprocessor:
    """
    Cleans raw email/SMS text into standardized, normalized tokens.
    """

    def __init__(self, use_stemming=True, preserve_financial_tokens=True):
        self.use_stemming = use_stemming
        self.preserve_financial_tokens = preserve_financial_tokens
        self.stemmer = PorterStemmer()
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self):
        try:
            sw = set(stopwords.words('english'))
        except Exception:
            try:
                nltk.download('stopwords', quiet=True)
                sw = set(stopwords.words('english'))
            except Exception:
                sw = set(FALLBACK_STOPWORDS)
        # Remove preserved words from stopwords so they remain valuable features
        return sw - PRESERVED_WORDS

    def clean_text(self, text: str) -> str:
        """
        Cleans and normalizes email text.
        Steps:
        1. String conversion & strip whitespace
        2. HTML tag removal
        3. URL replacement -> 'http_url'
        4. Email address replacement -> 'email_addr'
        5. Currency symbol replacement (₹, $, £, €, etc.) -> 'currency_sym'
        6. Phone number / long digit sequences -> 'phone_num'
        7. Numbers -> 'num_token'
        8. Lowercasing & punctuation removal
        9. Tokenization & Stopwords removal
        10. Porter Stemming (optional)
        """
        if not isinstance(text, str):
            text = str(text) if text is not None else ""

        if not text.strip():
            return ""

        # Normalize unicode (handles curly quotes, special spaces, Indian rupee symbol ₹)
        text = unicodedata.normalize('NFKD', text)

        # 1. Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # 2. Normalize URLs
        text = re.sub(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            ' http_url ',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(r'www\.[a-zA-Z0-9.\-_]+', ' http_url ', text, flags=re.IGNORECASE)

        # 3. Normalize Email Addresses
        text = re.sub(r'[\w.-]+@[\w.-]+\.\w+', ' email_addr ', text, flags=re.IGNORECASE)

        # 4. Normalize Currency Symbols (Rupee ₹ / Rs / INR, Dollar $, Euro €, Pound £)
        text = re.sub(r'(?:₹|rs\.?|inr|\$|£|€|¥)', ' currency_sym ', text, flags=re.IGNORECASE)

        # 5. Normalize Phone / Mobile Numbers (e.g. +91 9876543210, 1800-xxx)
        text = re.sub(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', ' phone_num ', text)

        # 6. Normalize Numbers (e.g. 10000, 10, 50k, 10lakh, 1cr)
        text = re.sub(r'\b\d+(?:[.,]\d+)?\b', ' num_token ', text)

        # 7. Convert to lowercase
        text = text.lower()

        # 8. Tokenize
        try:
            tokens = word_tokenize(text)
        except Exception:
            # Fallback regex tokenizer
            tokens = re.findall(r'\b[a-zA-Z_]+\b', text)

        # 9. Clean tokens: remove pure punctuation, remove stopwords, apply stemming
        processed_tokens = []
        for token in tokens:
            # Clean punctuation from ends of token
            token = token.strip(string.punctuation)
            if not token or len(token) <= 1:
                continue

            # Skip if stopword
            if token in self.stopwords:
                continue

            # Stemming
            if self.use_stemming:
                # Do not stem our special synthetic tokens
                if token not in {'http_url', 'email_addr', 'currency_sym', 'phone_num', 'num_token'}:
                    token = self.stemmer.stem(token)

            processed_tokens.append(token)

        return " ".join(processed_tokens)

    def preprocess_series(self, series):
        """Preprocesses a pandas Series of text entries."""
        return series.apply(self.clean_text)


if __name__ == "__main__":
    preprocessor = TextPreprocessor()
    sample = "Congratulations! You won ₹10 lakh. Call +919876543210 or visit http://prize-win.xyz to claim free cash!"
    cleaned = preprocessor.clean_text(sample)
    print("Original:", sample)
    print("Cleaned :", cleaned)
