from flask import Flask, request, jsonify
import requests
import os
import logging
import re
from datetime import datetime

app = Flask(__name__)

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ghl_zapier_bridge")

# -----------------------------
# Inline ENV Defaults
# -----------------------------
# You can change these directly here OR override them with real environment vars
ZAPIER_WEBHOOK_URL = os.environ.get(
    "ZAPIER_WEBHOOK_URL",
    "https://hooks.zapier.com/hooks/catch/11662046/uu00807/"  # default fallback
)
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# -----------------------------
# Helpers
# -----------------------------
def extract_practice_area(description: str) -> str:
    if not description:
        return "Other"

    d = description.lower()
    if any(k in d for k in ["accident", "injury", "personal injury", "slip and fall"]):
        return "Personal Injury"
    if any(k in d for k in ["divorce", "custody", "child support", "alimony"]):
        return "Family Law"
    if any(k in d for k in ["dui", "dwi", "drunk driving"]):
        return "DUI/DWI"
    if any(k in d for k in ["traffic ticket", "speeding ticket", "reckless driving", "careless driving"]):
        return "Traffic Law"
    if any(k in d for k in ["criminal", "arrest", "felony", "misdemeanor"]):
        return "Criminal Law"
    if "estate" in d or "will" in d or "trust" in d:
        return "Estate Planning"
    if "bankruptcy" in d or "chapter 7" in d or "chapter 13" in d:
        return "Bankruptcy"
    if "real estate" in d or "mortgage" in d or "foreclosure" in d:
        return "Real Estate"
    if "business" in d or "contract" in d or "llc" in d:
        return "Business Law"
    if "immigration" in d or "visa" in d or "green card" in d:
        return "Immigration"
    if "disability" in d or "ssdi" in d or "ssi" in d:
        return "Social Security Disability"
    if "workers comp" in d or "work injury" in d:
        return "Workers' Compensation"
    if "civil rights" in d or "police brutality" in d:
        return "Civil Rights"
    if "tax" in d or "irs" in d or "audit" in d:
        return "Tax Law"
    return "General"

def format_phone_number(phone: str) -> str:
    if not phone or phone.startswith("("):
        return phone
    clean = re.sub(r"[^\d]", "", phone)
    if clean.startswith("1") and len(clean) == 11:
        clean = clean[1:]
    if len(clean) == 10:
        return f"({clean[:3]}) {clean[3:6]}-{clean[6:]}"
    return phone

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def root():
    if request.method == "GET":
        return "Webhook bridge is running. POST JSON here or visit /health or /ping.", 200

    try:
        data = request.get_json(silent=True) or {}
        logger.info(f"Incoming webhook keys: {list(data.keys())}")

        full_name = data.get("full_name", "")
        email = data.get("email", "")
        phone = format_phone_number(data.get("phone", ""))
        case_description = data.get("case_description", data.get("tags", "Legal consultation request"))

        practice_area = extract_practice_area(case_description)

        outbound_payload = {
            "Full Name": full_name,
            "Email": email,
            "Phone": phone,
            "Case Description": case_description,
            "Practice Area": practice_area,
            "Case Type": practice_area,
            "Contact ID": data.get("contact_id", ""),
            "City": data.get("city", ""),
            "State": data.get("state", ""),
            "Source": "GoHighLevel",
            "Timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"➡ Sending to Zapier: {outbound_payload}")
        response = requests.post(ZAPIER_WEBHOOK_URL, json=outbound_payload, timeout=30)
        logger.info(f"Zapier response: {response.status_code} {response.text}")

        return "OK", 200
    except Exception as e:
        logger.exception("Webhook processing error")
        return "ERROR", 500

@app.route("/ping", methods=["GET"])
def ping():
    return "Webhook is live and ready to receive POSTs.", 200

@app.route("/health", methods=["GET"])
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "zapier_url": ZAPIER_WEBHOOK_URL,
        "host": HOST,
        "port": PORT,
        "debug": DEBUG
    }, 200

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    logger.info(f"Starting webhook bridge on {HOST}:{PORT}")
    logger.info(f"Zapier webhook URL: {ZAPIER_WEBHOOK_URL}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
