# 🛡️ Spam Rectifier — AI Email & Document Spam Analyzer

A multi-modal, installable Progressive Web App (PWA) built with **Python (Flask, NLTK, Scikit-Learn)**, **HTML5**, **CSS3**, and **JavaScript** to detect, verify, and rectify spam across **Text**, **PDF**, **Email (.eml)**, and **Image** formats.

---

## 🚀 Quick Start in Visual Studio Code

### 1. Open in Visual Studio Code
1. Launch **Visual Studio Code**.
2. Go to **File** > **Open Folder...**
3. Select this folder: `Spam Email Classifier`

### 2. Run with One Click (Press F5)
- Press **<kbd>F5</kbd>** on your keyboard (or go to **Run** > **Start Debugging**).
- VS Code automatically uses `.vscode/launch.json` to launch `app.py`.
- Open your browser at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.

Alternatively, in the integrated terminal (<kbd>Ctrl</kbd> + <kbd>`</kbd>):
```bash
python app.py
```

---

## 📲 Installing as an App (APK / Desktop App)

Because Spam Rectifier is built with a **Progressive Web App (PWA)** architecture (`manifest.json` + `sw.js`):
1. Open the website in **Google Chrome**, **Microsoft Edge**, or on an **Android browser**.
2. Click the **"📲 Install App"** button in the top navigation bar (or click the Install icon in the browser URL bar).
3. The app installs directly onto your **Windows Desktop** or **Android Home Screen** just like an APK, opening in its own clean standalone app window without browser tabs or address bars!

---

## 📂 Supported Upload Formats

| Format | Supported Extensions | Parser Engine |
|---|---|---|
| **Text Format** | Direct input, `.txt` | Plain text reader |
| **PDF Format** | `.pdf` | `pypdf` Multi-page extractor |
| **Email Format** | `.eml`, `.msg` | RFC 822 Email parser (`email.parser.BytesParser`) |
| **Image Format** | `.png`, `.jpg`, `.jpeg`, `.webp` | Tesseract.js Client-Side OCR Scanner |

---

## 🔍 Spam Condition Checks & Overall Percentage

When a file or text is uploaded, it undergoes multi-condition evaluations:
1. **Financial & Prize Scams**: Evaluates currency symbols (`₹`, `$`, `£`, `€`, `Rs`, `INR`), amounts (`lakh`, `crore`, `million`), and lottery keywords.
2. **Urgency & Account Coercion**: Detects threats (`urgent`, `account suspended`, `kyc`, `blocked within 24 hours`).
3. **Phishing Links & Contacts**: Identifies suspicious URLs, phone numbers, and call-to-actions.
4. **NLTK NLP Pipeline**: Stopword filtering, punctuation removal, and Porter Stemming.
5. **Machine Learning Model Inference**: Evaluates calibrated **Support Vector Machine (Linear SVM)** and **Multinomial Naive Bayes** trained on 5,960+ emails.
6. **Overall Spam Percentage**: Computes the overall probability score (e.g. **95.5% SPAM**) displayed on an interactive circular dial.

---

## 📁 Clean VS Code Project Structure

```text
Spam Email Classifier/
├── .vscode/
│   ├── launch.json              # VS Code F5 Run & Debug configuration
│   └── settings.json            # VS Code Python environment settings
├── models/
│   ├── tfidf_vectorizer.joblib  # Trained TF-IDF feature extractor
│   ├── svm_model.joblib         # Calibrated Support Vector Machine model (97.91% Acc)
│   ├── naive_bayes_model.joblib # Multinomial Naive Bayes model (96.82% Acc)
│   └── model_metadata.json      # Benchmark metrics
├── src/
│   ├── dataset_loader.py        # Dataset ingestion & curation
│   ├── document_parser.py       # PDF, DOCX, EML, Text parser
│   ├── feature_extractor.py     # TF-IDF extraction
│   ├── model_trainer.py         # Model training & cross-validation
│   ├── predictor.py             # Inference engine
│   └── text_preprocessor.py     # NLTK tokenization & Porter stemmer
├── static/
│   ├── css/style.css            # Dark cyberpunk glassmorphic stylesheet
│   ├── js/app.js                # App logic, PWA installation, OCR, gauge
│   ├── icons/
│   │   ├── icon-192.png         # PWA App Icon (192x192)
│   │   └── icon-512.png         # PWA High-res Icon (512x512)
│   ├── manifest.json            # Web App Manifest for app installation
│   └── sw.js                    # Service Worker for PWA
├── templates/
│   └── index.html               # Main Web App UI with upload format tabs
├── app.py                       # Main Flask web application server
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation
```
