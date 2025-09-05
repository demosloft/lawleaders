from flask import Flask, request, jsonify
import requests
import os
import logging
import re
from datetime import datetime, timezone # <-- add timezone

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Your Zapier webhook endpoint
ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/11662046/uu00807/"

def extract_practice_area(description):
    """Extract practice area from description text - EXPANDED for all legal matters"""
    if not description:
        return "Other"

    description_lower = description.lower()

    # Personal Injury Law
    personal_injury_keywords = [
        "personal injury", "accident", "injury", "hurt", "slip and fall", 
        "car accident", "auto accident", "motor vehicle", "medical malpractice", 
        "wrongful death", "premises liability", "product liability", "dog bite",
        "bicycle accident", "motorcycle accident", "pedestrian accident",
        "nursing home abuse", "construction accident", "workplace injury"
    ]
    for keyword in personal_injury_keywords:
        if keyword in description_lower:
            return "Personal Injury"

    # Family Law
    family_law_keywords = [
        "divorce", "custody", "child support", "alimony", "spousal support",
        "marriage", "separation", "adoption", "family", "spouse", "prenup",
        "prenuptial", "domestic violence", "restraining order", "paternity",
        "visitation", "guardianship", "child custody", "domestic relations"
    ]
    for keyword in family_law_keywords:
        if keyword in description_lower:
            return "Family Law"

    # DUI/DWI - CHECK FIRST (separate from other criminal law)
    dui_keywords = [
        "dui", "dwi", "owi", "drunk driving", "driving under influence", 
        "driving under the influence", "intoxicated driving", "impaired driving"
    ]
    for keyword in dui_keywords:
        if keyword in description_lower:
            return "DUI/DWI"

    # Traffic/Criminal Law - CHECK NEXT for traffic violations
    traffic_keywords = [
        "speeding ticket", "traffic ticket", "speeding", "traffic violation",
        "traffic offense", "moving violation", "reckless driving", "careless driving"
    ]
    for keyword in traffic_keywords:
        if keyword in description_lower:
            return "Traffic Law"

    # Criminal Law (after DUI and Traffic are checked)
    criminal_law_keywords = [
        "criminal", "arrest", "arrested", "charge", "charged", "offense", 
        "crime", "theft", "shoplifting", "stealing", "assault", "battery", 
        "probation", "jail", "prison", "felony", "misdemeanor", "warrant", 
        "drug", "trafficking", "possession", "domestic violence", "fraud",
        "embezzlement", "burglary", "robbery", "homicide", "manslaughter", 
        "larceny", "petty theft", "grand theft", "citation"
    ]
    for keyword in criminal_law_keywords:
        if keyword in description_lower:
            return "Criminal Law"

    # Estate Planning & Probate
    estate_planning_keywords = [
        "estate", "will", "trust", "inheritance", "probate", "executor",
        "beneficiary", "death", "asset", "living will", "power of attorney",
        "estate planning", "succession", "heir", "testamentary", "guardian",
        "conservatorship", "elder law", "medicaid planning"
    ]
    for keyword in estate_planning_keywords:
        if keyword in description_lower:
            return "Estate Planning"

    # Bankruptcy Law (check before Real Estate to avoid foreclosure conflicts)
    bankruptcy_keywords = [
        "bankruptcy", "chapter 7", "chapter 13", "debt", "creditor", 
        "discharge", "filing bankruptcy", "debt relief", "debt settlement"
    ]
    for keyword in bankruptcy_keywords:
        if keyword in description_lower:
            return "Bankruptcy"

    # Real Estate Law
    real_estate_keywords = [
        "real estate", "property", "house", "home", "closing", "deed",
        "title", "mortgage", "foreclosure", "landlord", "tenant", "lease",
        "eviction", "zoning", "easement", "boundary", "construction",
        "homeowners association", "hoa", "purchase agreement"
    ]
    for keyword in real_estate_keywords:
        if keyword in description_lower:
            return "Real Estate"

    # Business Law
    business_law_keywords = [
        "business", "contract", "llc", "corporation", "partnership",
        "employment", "fired", "wrongful termination", "discrimination",
        "harassment", "wage", "overtime", "breach of contract", "lawsuit",
        "commercial", "intellectual property", "trademark", "copyright",
        "non-compete", "partnership dispute", "shareholder"
    ]
    for keyword in business_law_keywords:
        if keyword in description_lower:
            return "Business Law"

    # Immigration Law
    immigration_keywords = [
        "immigration", "visa", "green card", "citizenship", "deportation",
        "asylum", "refugee", "work permit", "naturalization", "ice",
        "immigration court", "removal proceedings", "family petition"
    ]
    for keyword in immigration_keywords:
        if keyword in description_lower:
            return "Immigration"

    # Social Security Disability
    disability_keywords = [
        "disability", "social security", "ssdi", "ssi", "disabled",
        "disability benefits", "social security disability"
    ]
    for keyword in disability_keywords:
        if keyword in description_lower:
            return "Social Security Disability"

    # Workers' Compensation
    workers_comp_keywords = [
        "workers compensation", "workers comp", "work injury", 
        "on the job injury", "workplace accident", "injured at work"
    ]
    for keyword in workers_comp_keywords:
        if keyword in description_lower:
            return "Workers' Compensation"

    # Civil Rights
    civil_rights_keywords = [
        "civil rights", "discrimination", "police brutality", "excessive force",
        "constitutional rights", "section 1983", "civil lawsuit"
    ]
    for keyword in civil_rights_keywords:
        if keyword in description_lower:
            return "Civil Rights"

    # Tax Law
    tax_keywords = [
        "tax", "irs", "tax debt", "tax lien", "tax levy", "audit",
        "tax resolution", "offer in compromise", "innocent spouse"
    ]
    for keyword in tax_keywords:
        if keyword in description_lower:
            return "Tax Law"

    # If no match is found, return "General"
    return "General"

def extract_caller_info_from_transcript(transcription):
    """Extract caller name, phone, email from transcript text - handles ALL formats"""
    caller_info = {
        "name": "",
        "phone": "", 
        "email": ""
    }

    logger.info(f"Extracting info from transcript: {transcription[:100] if transcription else 'No transcript'}...")

    if not transcription:
        return caller_info

    # Split into lines for easier processing
    lines = transcription.split('\n')

    # Look for name patterns - EXPANDED to catch direct names
    name_patterns = [
        r"[Mm]y name is ([A-Za-z\s]+)",               # "My name is David Glick"
        r"[Ii]t'?s ([A-Za-z\s]+)",                    # "It's David Glick" 
        r"[Tt]his is ([A-Za-z\s]+)",                  # "This is David Glick"
        r"[Ii]'m ([A-Za-z\s]+)",                      # "I'm David Glick"
        r"[Cc]all me ([A-Za-z\s]+)",                  # "Call me David"
        r"([A-Za-z]+\s+[A-Za-z]+)\.?"                 # "John Smith." or "John Smith" (direct response)
    ]

    # Look for the name in ANY human/caller line
    for line in lines:
        line = line.strip()

        # Check if this is a human/caller line
        is_human_line = (
            line.lower().startswith('human:') or 
            line.lower().startswith('caller:') or
            line.lower().startswith('**caller:') or
            '**caller:**' in line.lower() or
            'caller:**' in line.lower()
        )

        if is_human_line:
            # Clean the line - remove ALL prefixes
            clean_line = line
            clean_line = re.sub(r'^\*+\s*caller:\s*', '', clean_line, flags=re.IGNORECASE)
            clean_line = re.sub(r'^caller:\s*', '', clean_line, flags=re.IGNORECASE)  
            clean_line = re.sub(r'^human:\s*', '', clean_line, flags=re.IGNORECASE)
            clean_line = re.sub(r'^\*+', '', clean_line).strip()

            for pattern in name_patterns:
                match = re.search(pattern, clean_line, re.IGNORECASE)
                if match:
                    potential_name = match.group(1).strip()

                    # Filter out common false positives - EXPANDED
                    false_positives = [
                        'not sure', 'not sure what', 'good', 'fine', 'okay', 'ok',
                        'yes', 'no', 'yeah', 'yep', 'sure', 'right', 'correct',
                        'that', 'this', 'here', 'there', 'help', 'calling',
                        'having trouble', 'trouble with', 'need help', 'looking for',
                        'thank you', 'thanks', 'hello', 'hi', 'bye', 'goodbye',
                        'hold on', 'wait', 'one moment', 'just a', 'let me',
                        'just got', 'got a', 'need help', 'just need'
                    ]

                    is_false_positive = any(fp in potential_name.lower() for fp in false_positives)

                    if not is_false_positive and len(potential_name) > 1:
                        words = potential_name.split()
                        if len(words) >= 1:
                            clean_name = re.sub(r',.*$', '', potential_name).strip()
                            caller_info["name"] = clean_name.title()
                            logger.info(f"✓ Successfully extracted name: {caller_info['name']}")
                            break

            # If we found a name, break out of the outer loop too
            if caller_info["name"]:
                break

    # Look for phone patterns - EXPANDED for spoken numbers
    phone_patterns = [
        r"(\+?1?\s*\(?\d{3}\)?\s*[-.\s]?\d{3}\s*[-.\s]?\d{4})",
        r"(\d{3}\s+\d{3}\s+\d{4})",
        r"(\d{10})"
    ]

    # First try standard digit patterns
    for pattern in phone_patterns:
        match = re.search(pattern, transcription)
        if match:
            phone = match.group(1)
            phone = re.sub(r'[^\d+]', '', phone)
            if phone.startswith('1') and len(phone) == 11:
                phone = phone[1:]
            if len(phone) == 10:
                caller_info["phone"] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                logger.info(f"✓ Extracted phone: {caller_info['phone']}")
                break

    # If no digits found, try spoken number pattern
    if not caller_info["phone"]:
        # More specific pattern for spoken phone numbers (exactly 10 number words)
        spoken_pattern = r"\b((?:zero|one|two|three|four|five|six|seven|eight|nine)\s+){9}(?:zero|one|two|three|four|five|six|seven|eight|nine)\b"
        spoken_match = re.search(spoken_pattern, transcription.lower())
        if spoken_match:
            spoken_numbers = spoken_match.group(0)
            # Convert spoken to digits
            digit_map = {
                'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
            }

            digits = ""
            for word in spoken_numbers.split():
                if word in digit_map:
                    digits += digit_map[word]

            if len(digits) == 10:
                caller_info["phone"] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                logger.info(f"✓ Extracted phone from spoken: {caller_info['phone']}")
            elif len(digits) == 11 and digits.startswith('1'):
                digits = digits[1:]  # Remove country code
                caller_info["phone"] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                logger.info(f"✓ Extracted phone from spoken (removed 1): {caller_info['phone']}")

    # Look for email patterns - EXPANDED for spoken emails
    email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    email_match = re.search(email_pattern, transcription.lower())
    if email_match:
        caller_info["email"] = email_match.group(1)
        logger.info(f"✓ Extracted email: {caller_info['email']}")
    else:
        # Try spoken email patterns like "john smith at gmail dot com"
        spoken_email_patterns = [
            r"([a-zA-Z0-9\s]+)\s+at\s+([a-zA-Z0-9\s]+)\s+dot\s+(com|net|org|edu|gov)",
            r"([a-zA-Z0-9\s]+)\s+@\s+([a-zA-Z0-9\s]+)\s+dot\s+(com|net|org|edu|gov)"
        ]

        # Common domain mappings for spoken emails
        domain_mappings = {
            'gmail': 'gmail.com',
            'g mail': 'gmail.com', 
            'outlook': 'outlook.com',
            'out look': 'outlook.com',
            'hotmail': 'hotmail.com',
            'hot mail': 'hotmail.com',
            'yahoo': 'yahoo.com',
            'aol': 'aol.com',
            'mail': 'mail.com',
            'live': 'live.com',
            'msn': 'msn.com',
            'comcast': 'comcast.net',
            'verizon': 'verizon.net',
            'att': 'att.net',
            'icloud': 'icloud.com',
            'me': 'me.com'
        }

        for pattern in spoken_email_patterns:
            match = re.search(pattern, transcription.lower())
            if match:
                name_part = match.group(1).strip()
                domain_part = match.group(2).strip()
                extension = match.group(3).strip()

                logger.info(f"🔍 Found spoken email parts: '{name_part}' at '{domain_part}' dot '{extension}'")

                # Clean up the name part (remove spaces, make lowercase)
                clean_name = re.sub(r'\s+', '', name_part.lower())

                # Map spoken domain to actual domain
                if domain_part in domain_mappings:
                    email_domain = domain_mappings[domain_part]
                else:
                    # Fallback: construct domain from parts
                    clean_domain = re.sub(r'\s+', '', domain_part.lower())
                    email_domain = f"{clean_domain}.{extension}"

                constructed_email = f"{clean_name}@{email_domain}"

                # Validate the constructed email looks reasonable
                if len(clean_name) > 0 and '.' in email_domain:
                    caller_info["email"] = constructed_email
                    logger.info(f"✓ Extracted spoken email: {caller_info['email']}")
                    break

    logger.info(f"📋 Final extraction results: {caller_info}")
    return caller_info

def summarize_transcript(transcription, max_length=200):
    """Create a concise summary of the transcript for case description"""
    if not transcription or len(transcription) <= max_length:
        return transcription

    # Clean up the transcript and separate human vs bot lines
    lines = transcription.split('\n')
    human_lines = []

    for line in lines:
        if any(prefix in line.lower() for prefix in ['human:', 'caller:', '**caller:']):
            # Remove prefixes and clean
            clean_line = re.sub(r'^(\*+)?(human|caller):\s*', '', line, flags=re.IGNORECASE).strip()
            if clean_line:
                human_lines.append(clean_line)

    # Focus on human lines first - this is where the legal issue will be
    human_text = " ".join(human_lines)

    # Look for the main legal issue from human speech
    legal_issue_patterns = [
        r"(I need help with .+?)[\.\!\?]",
        r"(I want to .+?)[\.\!\?]",
        r"(I was .+?)[\.\!\?]", 
        r"(I have been .+?)[\.\!\?]",
        r"(My .+ and I .+?)[\.\!\?]",
        r"(My .+?)[\.\!\?]",
        r"(There was .+?)[\.\!\?]",
        r"(Someone .+?)[\.\!\?]",
        r"(I got .+?)[\.\!\?]",
        r"(I am .+?)[\.\!\?]"
    ]

    main_issue = ""
    for pattern in legal_issue_patterns:
        match = re.search(pattern, human_text, re.IGNORECASE)
        if match:
            potential_issue = match.group(1).strip()
            # Filter out administrative/contact info statements
            if not any(admin_word in potential_issue.lower() for admin_word in 
                      ['name is', 'phone number', 'email', 'address', 'calling about', 'contact']):
                main_issue = potential_issue
                break

    # If no clear issue found, look for legal keywords in human text
    if not main_issue:
        legal_keywords = {
            'divorce': 'seeking divorce assistance',
            'custody': 'need help with child custody',
            'accident': 'involved in an accident',
            'injured': 'sustained injuries',
            'arrested': 'facing criminal charges',
            'fired': 'employment issue',
            'will': 'estate planning matter',
            'sued': 'involved in litigation',
            'bankruptcy': 'bankruptcy consultation',
            'disability': 'disability benefits matter',
            'immigration': 'immigration issue',
            'tax': 'tax matter',
            'contract': 'contract dispute',
            'real estate': 'real estate matter'
        }

        for keyword, description in legal_keywords.items():
            if keyword in human_text.lower():
                main_issue = description
                break

    # Build the final summary
    summary = main_issue or (human_text[:100] if human_text else "Legal consultation request")

    # If still too long, truncate intelligently
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."

    return summary or "Legal consultation request from GoHighLevel"

def format_phone_number(phone):
    """Helper function to format phone numbers consistently"""
    if not phone or phone.startswith('('):
        return phone

    clean_phone = re.sub(r'[^\d]', '', phone)
    if clean_phone.startswith('1') and len(clean_phone) == 11:
        clean_phone = clean_phone[1:]
    if len(clean_phone) == 10:
        return f"({clean_phone[:3]}) {clean_phone[3:6]}-{clean_phone[6:]}"
    return phone

# Webhook handler at the root route
@app.route('/', methods=['POST'])
def webhook_listener():
    try:
        # Log the incoming request details
        client_ip = request.remote_addr
        timestamp = datetime.utcnow().isoformat()
        logger.info(f"=== INCOMING WEBHOOK REQUEST ===")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Content-Type: {request.content_type}")

        # Get and log the raw incoming data
        data = request.json or {}
        logger.info(f"Raw incoming data keys: {list(data.keys())}")

        # Debug: Check what's in customData - FORCE DEBUG
        logger.info(f"🔍 DEBUGGING customData:")
        logger.info(f"'customData' in data: {'customData' in data}")
        if 'customData' in data:
            logger.info(f"customData type: {type(data['customData'])}")
            logger.info(f"customData is dict: {isinstance(data['customData'], dict)}")
            logger.info(f"customData content: {data['customData']}")
        else:
            logger.info("No customData key found")

        # Extract basic fields from webhook
        full_name = data.get("full_name", "")
        email = data.get("email", "")
        phone = data.get("phone", "")
        case_description = data.get("case_description", "")

        # Look for transcript data in multiple locations
        transcription = ""
        if "transcription" in data:
            transcription = data["transcription"]
            logger.info(f"Found transcription in root: {len(transcription)} chars")
        elif "transcript" in data:
            transcription = data["transcript"]
            logger.info(f"Found transcript in root: {len(transcription)} chars")
        elif "customData" in data and isinstance(data["customData"], dict):
            custom_data = data["customData"]
            logger.info(f"🔍 CustomData keys: {list(custom_data.keys())}")

            transcription = (custom_data.get("transcription", "") or 
                           custom_data.get("transcript", "") or 
                           custom_data.get("case_transcript", ""))

            if transcription:
                logger.info(f"✅ Found transcript: {len(transcription)} chars")
            else:
                logger.error(f"❌ No transcript in customData: {custom_data}")

            # Also check for other fields in customData
            if not full_name:
                full_name = custom_data.get("full_name", "")
            if not email:
                email = custom_data.get("email", "")
            if not phone:
                phone = custom_data.get("phone", "")
            if not case_description:
                case_description = custom_data.get("case_description", "")

        # FORCE phone formatting regardless of transcript
        original_phone = phone
        phone = format_phone_number(phone)
        logger.info(f"📞 Phone: '{original_phone}' → '{phone}'")

        logger.info(f"Transcript found: {len(transcription) if transcription else 0} characters")

        # Extract caller info from transcript if available
        if transcription:
            caller_info = extract_caller_info_from_transcript(transcription)

            # Use extracted info if the webhook data is missing
            if not full_name and caller_info["name"]:
                full_name = caller_info["name"]
                logger.info(f"Used transcript name: {full_name}")

            if not phone and caller_info["phone"]:
                phone = caller_info["phone"]
                logger.info(f"Used transcript phone: {phone}")
            else:
                # Format the existing phone number using helper function
                phone = format_phone_number(phone)
                if phone != data.get("phone", ""):
                    logger.info(f"Formatted phone: {phone}")

            if not email and caller_info["email"]:
                email = caller_info["email"]
                logger.info(f"Used transcript email: {email}")

            # Use transcript for case description if none provided
            if not case_description:
                case_description = summarize_transcript(transcription)
                logger.info(f"Generated case description from transcript")

        # Remove the old phone formatting section since we do it above

        # Also check for tags or other description fields
        if not case_description:
            case_description = data.get("tags", "") or "Legal consultation request"

        logger.info(f"Final extracted fields:")
        logger.info(f"  - Full Name: {full_name}")
        logger.info(f"  - Email: {email}")
        logger.info(f"  - Phone: {phone}")
        logger.info(f"  - Case Description: {case_description[:100]}...")

        # Determine practice area - FIX THE BUG
        logger.info(f"🎯 Case description: '{case_description}'")
        logger.info(f"Contains 'careless driv': {'careless driv' in case_description.lower()}")

        practice_area = extract_practice_area(case_description)
        logger.info(f"  - Detected Practice Area: {practice_area}")

        # MANUAL FIX: If we see driving-related terms, force Traffic Law
        if any(term in case_description.lower() for term in ['careless driv', 'reckless driv', 'traffic ticket', 'speeding ticket']):
            if practice_area not in ['Traffic Law', 'DUI/DWI']:
                logger.error(f"🚨 MANUAL FIX: Found driving term but got '{practice_area}' - forcing 'Traffic Law'")
                practice_area = "Traffic Law"

        # Build outbound payload with clean field names for Zapier
        outbound_payload = {
            "Full Name": full_name,
            "Email": email,
            "Phone": phone,
            "Case Description": case_description,
            "Practice Area": practice_area,
            "Case Type": practice_area,  # Alternative field name
            "Contact ID": data.get("contact_id", ""),
            "City": data.get("city", ""),
            "State": data.get("state", ""),
            "Source": "GoHighLevel",
            "Timestamp": timestamp,
            "Has Transcript": bool(transcription),
            "Transcript Length": len(transcription) if transcription else 0
        }

        # Log what we're sending to Zapier
        logger.info(f"=== SENDING TO ZAPIER ===")
        logger.info(f"Zapier URL: {ZAPIER_WEBHOOK_URL}")
        logger.info(f"Outbound payload keys: {list(outbound_payload.keys())}")

        # Send parsed and enriched data to Zapier
        response = requests.post(ZAPIER_WEBHOOK_URL, json=outbound_payload, timeout=30)

        # Log Zapier response
        logger.info(f"=== ZAPIER RESPONSE ===")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response Body: {response.text}")
        logger.info(f"=== END WEBHOOK PROCESSING ===")

        # Return simple "OK" response that GHL expects
        return "OK", 200

    except Exception as e:
        logger.error(f"=== WEBHOOK ERROR ===")
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(f"Request data: {request.get_data()}")
        logger.error(f"=== END ERROR ===")
        # Return simple error response
        return "ERROR", 500

# Optional route to test if app is live
@app.route('/ping', methods=['GET'])
def ping():
    return "Webhook is live and ready to receive POSTs.", 200

# Health check route
@app.route('/health', methods=['GET'])
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zapier_url": ZAPIER_WEBHOOK_URL
    }, 200

# Run the app
if __name__ == '__main__':
    # Get port from environment variable (required for Replit deployment)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting GoHighLevel to Zapier webhook bridge on {host}:{port}")
    logger.info(f"Zapier webhook URL: {ZAPIER_WEBHOOK_URL}")

    app.run(host=host, port=port, debug=debug)



