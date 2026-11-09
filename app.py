"""
Spam Rectifier - AI Email & Document Spam Detection Web Application
Backend: Python (Flask, NLTK, Scikit-Learn)
Features:
- Multi-format ingestion: Text format, PDF format, Email format (.eml, .msg), Images (.png, .jpg)
- Spam condition evaluations (Financial, Urgency, Phishing, NLP Stemming, ML inference)
- Overall Spam Probability Percentage calculation
- PWA & VS Code ready
"""

import os
import sys
import io
import json
import re
import zipfile
import email
from email import policy
from email.parser import BytesParser
import pypdf
import docx
from flask import Flask, render_template, request, jsonify, make_response, send_file, send_from_directory
from werkzeug.utils import secure_filename

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.predictor import SpamPredictor
from src.document_parser import DocumentParser

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB max file upload size

# Enable CORS for all local development origins (Live Server 5500, localhost, etc.)
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    return response

@app.before_request
def handle_options_preflight():
    if request.method == 'OPTIONS':
        res = make_response()
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        return res, 200

predictor = None

def get_predictor():
    global predictor
    if predictor is None:
        predictor = SpamPredictor()
    return predictor


def evaluate_spam_conditions(text: str, ml_spam_prob: float):
    """
    Evaluates specific spam risk conditions:
    1. Financial / Lottery triggers (₹, $, lakh, crore, lottery, won, prize)
    2. Urgency & Coercion triggers (urgent, account suspended, kyc, 24 hours, immediately)
    3. Phishing links & suspicious contacts (urls, phone numbers, click here)
    Combines them with Machine Learning model output to calculate the overall percentage.
    """
    lower = text.lower()

    # Condition 1: Financial & Prize indicators
    financial_patterns = [
        r'(?:₹|rs\.?|inr|\$|£|€)',
        r'\b(?:lakh|crore|million|billion|lottery|jackpot|prize|cash|winner|bonus|reward|refund|credited)\b',
        r'\b(?:won|win|claim|transfer|payout)\b'
    ]
    fin_matches = sum(len(re.findall(p, lower)) for p in financial_patterns)
    financial_score = min(100.0, fin_matches * 25.0)

    # Condition 2: Urgency & Account Threat indicators
    urgency_patterns = [
        r'\b(?:urgent|immediately|action required|blocked|suspended|expires?|warning|final notice)\b',
        r'\b(?:kyc|pan|verify|unauthorized|freeze|locked)\b',
        r'\b(?:within \d+ hours?|today only|last chance)\b'
    ]
    urg_matches = sum(len(re.findall(p, lower)) for p in urgency_patterns)
    urgency_score = min(100.0, urg_matches * 30.0)

    # Condition 3: Phishing Links & Unsolicited contact indicators
    link_patterns = [
        r'http[s]?://\S+',
        r'www\.\S+',
        r'\b(?:click here|click to|follow link|update details|reply with)\b',
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    ]
    link_matches = sum(len(re.findall(p, lower)) for p in link_patterns)
    link_score = min(100.0, link_matches * 25.0)

    # Weighted Overall Spam Percentage calculation:
    # 70% Weight from calibrated ML probability (SVM / Naive Bayes)
    # 30% Weight from explicit heuristic condition risk factors
    heuristic_avg = (financial_score * 0.45) + (urgency_score * 0.35) + (link_score * 0.20)
    ml_pct = ml_spam_prob * 100.0

    if ml_pct > 80.0 or heuristic_avg > 75.0:
        overall_percentage = max(ml_pct, (ml_pct * 0.70) + (heuristic_avg * 0.30))
    else:
        overall_percentage = (ml_pct * 0.75) + (heuristic_avg * 0.25)

    overall_percentage = round(min(99.9, max(0.1, overall_percentage)), 1)
    is_spam = overall_percentage >= 50.0

    # Risk Level classification
    if overall_percentage >= 85.0:
        risk_level = "CRITICAL SPAM RISK"
    elif overall_percentage >= 60.0:
        risk_level = "HIGH SPAM RISK"
    elif overall_percentage >= 40.0:
        risk_level = "SUSPICIOUS / REVIEW"
    else:
        risk_level = "SAFE / CLEAN EMAIL"

    return {
        "overall_spam_percentage": overall_percentage,
        "overall_ham_percentage": round(100.0 - overall_percentage, 1),
        "verdict": "SPAM" if is_spam else "NOT SPAM",
        "is_spam": is_spam,
        "risk_level": risk_level,
        "condition_scores": {
            "ml_probability": round(ml_pct, 1),
            "financial_risk": round(financial_score, 1),
            "urgency_risk": round(urgency_score, 1),
            "link_risk": round(link_score, 1)
        }
    }


@app.route("/")
def index():
    """Renders Spam Rectifier Web Application."""
    meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass
    return render_template("index.html", metadata=metadata)


@app.route("/sw.js")
def service_worker():
    """Serves the service worker from root scope for native PWA installation."""
    response = make_response(send_from_directory("static", "sw.js"))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route("/manifest.json")
def manifest():
    """Serves web app manifest."""
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


@app.route("/api/install-desktop-app", methods=["POST", "GET"])
def install_desktop_app():
    """
    Creates a native Windows Desktop Shortcut 'Spam Rectifier.lnk' directly on the user's Desktop.
    """
    try:
        import subprocess
        desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")

        shortcut_path = os.path.join(desktop_dir, "Spam Rectifier.lnk")
        target_bat = os.path.join(PROJECT_ROOT, "Start_Web_App.bat")
        icon_path = os.path.join(PROJECT_ROOT, "static", "icons", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(PROJECT_ROOT, "static", "icons", "icon-192.png")

        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut_path}"); '
            f'$s.TargetPath = "{target_bat}"; '
            f'$s.WorkingDirectory = "{PROJECT_ROOT}"; '
            f'$s.IconLocation = "{icon_path}"; '
            f'$s.Description = "Spam Rectifier Application"; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], check=True, timeout=10)

        return jsonify({
            "status": "success",
            "message": "Spam Rectifier shortcut successfully created on your Desktop! You can now launch it anytime.",
            "shortcut_path": shortcut_path
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/download/app")
def download_app():
    """Generates and serves the automated application installer."""
    installer_content = (
        "@echo off\r\n"
        "title Spam Rectifier Application Installer\r\n"
        "color 0A\r\n"
        "echo ================================================================\r\n"
        "echo             INSTALLING SPAM RECTIFIER APPLICATION\r\n"
        "echo ================================================================\r\n"
        "echo.\r\n"
        f"set \"APP_DIR={PROJECT_ROOT}\"\r\n"
        "if not exist \"%APP_DIR%\\app.py\" (\r\n"
        "    if exist \"%USERPROFILE%\\OneDrive\\Desktop\\Spam Email Classifier\\app.py\" (\r\n"
        "        set \"APP_DIR=%USERPROFILE%\\OneDrive\\Desktop\\Spam Email Classifier\"\r\n"
        "    ) else if exist \"%USERPROFILE%\\Desktop\\Spam Email Classifier\\app.py\" (\r\n"
        "        set \"APP_DIR=%USERPROFILE%\\Desktop\\Spam Email Classifier\"\r\n"
        "    )\r\n"
        ")\r\n"
        "echo Target Location: %APP_DIR%\r\n"
        "echo Creating Desktop Shortcut...\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        "\"$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); "
        "$s = $ws.CreateShortcut(\\\"$d\\Spam Rectifier.lnk\\\"); "
        "$s.TargetPath = '%APP_DIR%\\Start_Web_App.bat'; "
        "$s.WorkingDirectory = '%APP_DIR%'; "
        "$s.IconLocation = '%APP_DIR%\\static\\icons\\app_icon.ico'; "
        "$s.Description = 'Spam Rectifier Application'; $s.Save()\"\r\n"
        "echo.\r\n"
        "echo ================================================================\r\n"
        "echo      SUCCESS! SPAM RECTIFIER INSTALLED ON YOUR DESKTOP!\r\n"
        "echo ================================================================\r\n"
        "echo Launching Spam Rectifier now...\r\n"
        "start \"\" \"%APP_DIR%\\Start_Web_App.bat\"\r\n"
        "exit\r\n"
    )

    buf = io.BytesIO(installer_content.encode('utf-8'))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/x-bat",
        as_attachment=True,
        download_name="Install_Spam_Rectifier.bat"
    )


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    Direct Text / Content Analysis Endpoint.
    Payload: { "email": "text content", "algorithm": "svm" | "nb" }
    """
    try:
        data = request.get_json(force=True) or {}
        email_text = data.get("email", "").strip()
        algo = data.get("algorithm", "svm")

        if not email_text:
            return jsonify({"status": "error", "message": "Content cannot be empty"}), 400

        p = get_predictor()
        base_pred = p.predict(email_text, algorithm=algo)

        # Evaluate full condition checks & calculate overall percentage
        cond_res = evaluate_spam_conditions(email_text, base_pred["spam_probability"])

        # Merge results
        result = {
            **base_pred,
            **cond_res,
            "overall_percentage": cond_res["overall_spam_percentage"]
        }

        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    File Upload Endpoint:
    Accepts:
    - Text Format: .txt
    - PDF Format: .pdf
    - Email Format: .eml, .msg
    - Images: .png, .jpg, .jpeg, .webp
    Extracts text and evaluates spam conditions + overall percentage.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded."}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected."}), 400

        filename = secure_filename(file.filename) or "uploaded_file"
        algorithm = request.form.get("algorithm", "svm")
        file_bytes = file.read()

        if not DocumentParser.is_supported(filename):
            return jsonify({
                "status": "error",
                "message": f"Unsupported format. Please upload PDF (.pdf), Email (.eml, .msg), Text (.txt), or Image (.png, .jpg)."
            }), 400

        # Parse text from file
        parse_res = DocumentParser.parse_file(file_bytes, filename)
        extracted_text = parse_res.get('extracted_text', '').strip()
        is_image = parse_res.get('is_image', False)

        # If it's an image and server-side OCR wasn't present, request client OCR
        if is_image and not extracted_text:
            return jsonify({
                "status": "needs_client_ocr",
                "filename": filename,
                "file_type": parse_res.get('file_type', 'Image'),
                "message": "Image received. Client-side OCR will extract text."
            })

        if not extracted_text:
            return jsonify({
                "status": "error",
                "message": f"Could not extract readable text from '{filename}'."
            }), 400

        # Run Prediction
        p = get_predictor()
        base_pred = p.predict(extracted_text, algorithm=algorithm)
        cond_res = evaluate_spam_conditions(extracted_text, base_pred["spam_probability"])

        result = {
            **base_pred,
            **cond_res,
            "overall_percentage": cond_res["overall_spam_percentage"]
        }

        return jsonify({
            "status": "success",
            "data": result,
            "document_info": {
                "filename": filename,
                "file_type": parse_res.get('file_type', 'Document'),
                "metadata": parse_res.get('metadata', {}),
                "extracted_length": len(extracted_text)
            }
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    """Returns model benchmark scores."""
    meta_path = os.path.join(PROJECT_ROOT, "models", "model_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Metadata not found"}), 404


if __name__ == "__main__":
    get_predictor()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==================================================")
    print(f" 🛡️ Spam Rectifier Web Application")
    print(f" Running at: http://127.0.0.1:{port}")
    print(f" Press Ctrl+C to terminate.")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
