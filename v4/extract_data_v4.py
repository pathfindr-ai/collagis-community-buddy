import os, csv
import uuid
from openai import OpenAI
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Literal, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import requests
from requests.adapters import HTTPAdapter, Retry
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from v4.reporting import PipelineResult, log_flow_outcome
import email.utils
load_dotenv()

client = OpenAI()  # Will use OPENAI_API_KEY environment variable
openai_model = os.getenv("OPENAI_MODEL", "gpt-5-mini-2025-08-07")
from v4.mappings_v4 import (
    repair_location,
    issue_loaction,
    common_outside_issue_area,
    common_inside_issue_area,
    home_inside_issue_area,
    issue_type,
    common_outside_access_issues,
    common_inside_access_issues,
    home_inside_access_issues,
    common_outside_cleaning_issues,
    common_inside_cleaning_issues,
    home_inside_cleaning_issues,
    common_outside_electrical_issues,
    common_inside_electrical_issues,
    home_inside_electrical_issues,
    common_outside_gas_issues,
    common_inside_gas_issues,
    home_inside_gas_issues,
    common_outside_water_issues,
    common_inside_water_issues,
    home_inside_water_issues,
    common_outside_something_else_issues,
    common_inside_something_else_issues,
    home_inside_something_else_issues,
    home_outside_access_issues,
    home_outside_cleaning_issues,
    home_outside_electrical_issues,
    home_outside_gas_issues,
    home_outside_issue_area,
    home_outside_something_else_issues,
    home_outside_water_issues
)


class UserData(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: str
    repair_location: Literal['My Home', 'Common Area']
    issue_location: Literal['Inside', 'Outside']
    issue_area: str
    issue_type: str
    issue_detail: str
    previous_issue: Literal['Yes','No']
    issue_text: str
    appointment_times: Optional[List[str]] = []
    access_instructions: Optional[str] = None


class ExtractionResult(BaseModel):
    success: bool
    user_data: Optional[UserData] = None
    error_reason: Optional[str] = None


def format_mappings_for_prompt() -> str:
    return f"""
    Use ONLY the following mappings to fill variables. 
    Do not invent new values outside these lists. 
    If something does not match, choose the other option.
    
    Following are the mappings for repair_location and issue_location:
    
    repair location : {repair_location}
    
    issue location : {issue_loaction}
    
    
    The following are the mappings to use for extracting the issue_area:
   
    
    Common Outside Issue Area: {common_outside_issue_area}
    Common Inside Issue Area: {common_inside_issue_area}
    Home Inside Issue Area: {home_inside_issue_area}
    Home Outside Issue Area: {home_outside_issue_area}

    The following are the mappings to use for extracting the issue_type

    Issue Type: {issue_type}

    The following are the mappings to use for extracting the issue_detail variable:

    Common Outside Access Issues: {common_outside_access_issues}
    Common Inside Access Issues: {common_inside_access_issues}
    Home Inside Access Issues: {home_inside_access_issues}
    Home Outside Access Issues: {home_outside_access_issues}
    Common Outside Cleaning Issues: {common_outside_cleaning_issues}
    Common Inside Cleaning Issues: {common_inside_cleaning_issues}
    Home Inside Cleaning Issues: {home_inside_cleaning_issues}
    Home Outside Cleaning Issues: {home_outside_cleaning_issues}
    Common Outside Electrical Issues: {common_outside_electrical_issues}
    Common Inside Electrical Issues: {common_inside_electrical_issues}
    Home Inside Electrical Issues: {home_inside_electrical_issues}
    Home Outside Electrical Issues: {home_outside_electrical_issues}
    Common Outside Gas Issues: {common_outside_gas_issues}
    Common Inside Gas Issues: {common_inside_gas_issues}
    Home Inside Gas Issues: {home_inside_gas_issues}
    Home Outside Gas Issues: {home_outside_gas_issues}
    Common Outside Water Issues: {common_outside_water_issues}
    Common Inside Water Issues: {common_inside_water_issues}
    Home Inside Water Issues: {home_inside_water_issues}
    Home Outside Water Issues: {home_outside_water_issues}
    Common Outside Something Else Issues: {common_outside_something_else_issues}
    Common Inside Something Else Issues: {common_inside_something_else_issues}
    Home Inside Something Else Issues: {home_inside_something_else_issues}
    Home Outside Something Else Issues: {home_outside_something_else_issues}
    
    
    The following are the available appointment options for mapping `appointment_times`:
    Appointment Times: 
        ["Monday AM", "Monday PM",
         "Tuesday AM", "Tuesday PM",
         "Wednesday AM", "Wednesday PM",
         "Thursday AM", "Thursday PM",
         "Friday AM", "Friday PM",
         "Saturday AM", "Saturday PM",
         "Sunday AM", "Sunday PM"]

    For `access_instructions`, provide short text like:
        "Leave gate open", "Access via garage", or "Call before entering".
        If any access-related details (e.g., gate, key, door, security, garage, etc.) are mentioned by the user in the transcript,
        extract them exactly as provided and use them for `access_instructions`.
        Only generate a short, relevant instruction — do not invent new details.

    """


# Function to send transcript to GPT and translate it
def translate_improve_transcript(transcript: str):
    print("Cleaning the given transcription...")
    completion = client.chat.completions.create(
        model=openai_model,
        messages=[
            {
                "role": "developer",  
                "content": f"""
           You are an assistant specialized in translating and refining transcripts. **Follow the instructions below precisely** to ensure accurate and consistent outputs.

            **Task Overview**:
            - **Primary Objective**: Translate non-English transcripts to English.
            - **Secondary Objective**: Correct typos, transcription errors, and regional or accent-related mistakes in non-English transcripts.

            **Detailed Instructions**:
            
            1. **Detect Mixed Languages**: The transcript may contain BOTH English and non-English text (Hindi, Vietnamese, Bahasa, etc.)
                 - **Check** if the provided transcript is in English.
                    - **If English**:
                        - **Do Not Alter** the transcript.
                        - **Return** the transcript exactly as provided.
                    - **If Not English or mixed language detected**:
                        - **Proceed** to the Translation and Improvement steps.

            2. **Translation and Improvement steps**:
            - **TRANSLATE** all non-English text (Hindi, Vietnamese, Bahasa, etc.) to English
            - **KEEP** all English text exactly as it appears
            - **PRESERVE** all formatting, JSON structure, tags (like #pleasant, #neutral), field names, and punctuation
            - **DO NOT** translate: English words/phrases, English proper names, English email addresses, English phone numbers, or English technical terms
            - **Correct** any:
                    - **Typos**
                    - **Transcription Mistakes**
                    - **Regional or Accent-Related Errors**


            3. **Examples of What NOT to Translate**:
            - Keep: "ChatGPT", "gmail.com", "#pleasant", "#neutral"
            - Keep: Names already in English like "Ravi Patel"
            - Keep: JSON structure: "Author", "Text", "messages"

            4. **Format Preservation**:
            - Maintain exact JSON structure  (e.g., timestamps, speaker labels, paragraphs).
            - Keep all quotes, brackets, commas, and colons
            - Preserve line breaks and indentation
            - Keep all metadata tags (#pleasant, #neutral, etc.)


            5. **Output Guidelines**:
                - **Respond Only** with the translated and/or improved transcript.
                - **Do Not Include** any additional text, explanations, comments, or examples outside the translated/improved transcript.
                - **Ensure** the output is clean and free from any markup or annotations unless present in the original transcript.
                - **Maintain Exact Format**: The output must strictly follow the same formatting as the input transcript without any deviations.
            """
            },
            {"role": "user", "content": transcript},
        ],
    )
    print("Transcript is cleaned...")
    return completion.choices[0].message.content


# classify transcript
class TranscriptCategory(BaseModel):
    """Transcript classification schema."""
    category: str = Field(
        description="Category of the transcript. One of: 'maintenance_request', 'it_request', 'visitor_check_in', or 'not_found'."
    )

def classify_transcript(transcript: str) -> TranscriptCategory:
    """
    Classify transcript into one of the categories:
    - maintenance_request
    - it_request
    - visitor_check_in
    - not_found
    """
    # Initialize model
    model = ChatOpenAI(model=openai_model)

    # Bind schema using structured output
    structured_model = model.with_structured_output(TranscriptCategory)

    # Classification instructions (system role)
    system_prompt = """
    You are a strict classifier. 

    Classify the transcript into exactly one of these categories:

    1. maintenance_request  
    - Definition: A request related to home, office, or facility maintenance.  
    - Examples: leaking air conditioner, broken door, plumbing issue, electrical outage.  

    2. it_request
    - Definition: An IT-related issue such as hardware, software, login, or connectivity problems.  
    - Examples: laptop not working, password reset, VPN not connecting, email issue.  
    - If chosen, the “Short Description” should be like:  
        • "My laptop is not working"  
        • "I can't connect to Wi-Fi"  
        • "My password is not working"  

    3. visitor_check_in  
    - Definition: A transcript where someone is reporting or recording the arrival of a visitor.  
    - Examples: "I am here to meet Mr. Johnson", "A guest has arrived", "Visitor at reception".  

    If the transcript does not clearly belong to any of these, return `"not_found"`.  
    """

    # Invoke the model
    result = structured_model.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript},
    ])

    # Returns a TranscriptCategory object automatically
    category = result.category  

    # Send acknowledgement (optional logging/print)
    print(f"Acknowledged: category identified as '{category}'")
    return category




# ---------------------------------------------------
# Function - Extract form Information from Transcript
# ---------------------------------------------------
def extract_maintenance_info(transcript: str) -> ExtractionResult:
    """
    Extract maintenance request details from transcript.
    Returns:
        - success=True with structured user_data if all required fields present
        - success=False with error_reason if mandatory fields missing
    """
    model = ChatOpenAI(model=openai_model)

    structured_model = model.with_structured_output(UserData)

    mappings_description = format_mappings_for_prompt()

    system_prompt = f"""
    You are an assistant that extracts structured maintenance request details
    from a transcript.

    Rules:
    - Follow the mappings strictly when filling variables.
    - Do not create values that are not in the mappings.
    - If optional fields (email, appointment_times) are missing, leave them empty.
    - Do not guess missing information; only fill what is explicitly mentioned.

    Mandatory fields:
    - first_name
    - last_name
    - phone
    - address
    - repair_location
    - issue_location
    - issue_area
    - issue_type
    - issue_detail
    - previous_issue
    - issue_text

    {mappings_description}
    
    
    **Important Constraints**:
            - **Do Not**:
                - Provide explanations, comments, or additional text outside the JSON object.
                - Infer or assume information not explicitly stated in the transcript.
                - Deviate from the specified response format.

            - **Must**:
                - Ensure the JSON object includes **all** specified fields.
                - Follow the mapping.
                - Use exact field names and structure as specified.

            **Transcript Analysis**:
            Analyze the following transcript and extract the required information **strictly** according to the rules above.
    """

    try:
        result: UserData = structured_model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ])

        mandatory_fields = [
            "first_name", "last_name", "phone", "address",
            "repair_location", "issue_location",
            "issue_type", "issue_detail", "previous_issue", "issue_text"
        ]

        missing = [field for field in mandatory_fields if not getattr(result, field, None)]
        if missing:
            return ExtractionResult(
                success=False,
                error_reason=f"Missing mandatory fields: {', '.join(missing)}"
            )

        return ExtractionResult(success=True, user_data=result)

    except Exception as e:
        return ExtractionResult(success=False, error_reason=str(e))
    
    
class VisitorData(BaseModel):
    full_name: str
    company: str
    purpose: str
    check_in_time: Optional[str]= None
    notes: Optional[str] = None
    host_name: str


class VisitorExtractionResult(BaseModel):
    success: bool
    visitor_data: Optional[VisitorData] = None
    error_reason: Optional[str] = None


# ------------------------------------------------------
# Function - Extract visitor Information from Transcript
# ------------------------------------------------------
def extract_visitor_info(transcript: str) -> VisitorExtractionResult:
    """
    Extract visitor check-in details from transcript.
    Returns:
        - success=True with structured visitor_data if all required fields present
        - success=False with error_reason if mandatory fields missing (especially host_name)
    """
    model = ChatOpenAI(model=openai_model)

    structured_model = model.with_structured_output(VisitorData)

    system_prompt = """
    You are an assistant that extracts visitor check-in details from a transcript.

    Extract the following fields:
    - Visitor's full name
    - Visitor's company
    - Purpose of visit
    - Check-in time (optional)
    - Optional notes (if mentioned, otherwise leave empty)
    - Host name (the person the visitor came to see)

    Rules:
    - Fill all required fields.
    - Do not guess or fabricate values.
    """

    try:
        # Call model
        result: VisitorData = structured_model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ])

        # Validate required fields
        mandatory_fields = [
            "full_name", "company", "purpose", "host_name"
        ]

        missing = [
            field for field in mandatory_fields
            if not getattr(result, field, None) or str(getattr(result, field)).strip() == ""
        ]

        if missing:
            return VisitorExtractionResult(
                success=False,
                error_reason=f"Missing mandatory fields: {', '.join(missing)}"
            )

        return VisitorExtractionResult(success=True, visitor_data=result)

    except Exception as e:
        return VisitorExtractionResult(success=False, error_reason=str(e))
 


# --------------------------------------------
# Function - Send Email using Azure SMTP Relay with CC Support
# --------------------------------------------
def send_visitor_notification(visitor_data: dict, csv_path: str):
    """
    Sends an arrival notification email using Azure Communication Services SMTP relay.
    Supports CC recipients from environment variable.
    Returns a tuple (success: bool, message: str).
    Logging is handled by the caller.
    """
    flow_name = "visitor_check_in"
    host_name = visitor_data.get("host_name", "").strip().lower()
    host_email = None

    try:
        # Read CSV file to find matching host email
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            normalized_host = ' '.join(host_name.split()).lower()
            for row in reader:
                normalized_row_name = ' '.join(row['name'].strip().split()).lower()
                if normalized_row_name == normalized_host:
                    host_email = row['email'].strip()
                    break

        if not host_email:
            error_msg = f"Host '{visitor_data.get('host_name', '')}' not found in CSV."
            print(f"[ERROR] {error_msg}")
            return False, error_msg  

        # Prepare email content
        subject = f"Visitor Arrival Notification – {visitor_data.get('full_name', 'Unknown Visitor')}"
        html_content = f"""
        <p>OFFICIAL</p>
        <p>Hello {visitor_data.get('host_name', 'Host')},</p>
        <p>Your visitor, <strong>{visitor_data.get('full_name', 'Unknown')}</strong> 
        from <strong>{visitor_data.get('company', 'N/A')}</strong>, 
        has arrived for a <strong>{visitor_data.get('purpose', 'visit')}</strong>.</p>
        <p>They checked in at {visitor_data.get('check_in_time', 'Unknown time')} and are waiting in reception.</p>
        <p>{'Notes: ' + visitor_data.get('notes', '') if visitor_data.get('notes') else ''}</p>
        <p>– Reception</p>
        """

        # SMTP configuration
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("SENDER_EMAIL")
        
        # Get CC emails from environment (comma-separated)
        cc_emails_raw = os.getenv("CC_EMAIL", "")
        
        if not all([smtp_server, smtp_username, smtp_password, sender_email]):
            error_msg = "Missing required SMTP configuration in environment variables"
            print(f"[ERROR] {error_msg}")
            return False, error_msg

        # Parse and validate CC emails
        cc_emails = []
        if cc_emails_raw:
            # Split by comma and clean up whitespace
            cc_emails = [email.strip() for email in cc_emails_raw.split(',') if email.strip()]
            # Filter out invalid emails (basic validation)
            # cc_emails = [email for email in cc_emails if '@' in email and '.' in email.split('@')[1]]
        
        # Compose message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = host_email
        
        # Add CC header if CC emails exist
        if cc_emails:
            message["Cc"] = ", ".join(cc_emails)
            print(f"[INFO] CC: {', '.join(cc_emails)}")
        
        message_id = f"<{uuid.uuid4()}@{smtp_server}>"
        message["Message-ID"] = message_id
        message["Date"] = email.utils.formatdate(localtime=True)
        message.attach(MIMEText(html_content, "html"))

        # Build complete recipient list (To + CC)
        all_recipients = [host_email] + cc_emails

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            # send to all recipients (To + CC)
            server.sendmail(sender_email, all_recipients, message.as_string())

        recipients_info = f"to {host_email}"
        if cc_emails:
            recipients_info += f" (CC: {', '.join(cc_emails)})"
        
        success_msg = f"Email sent {recipients_info} – Message ID: {message_id}"
        print(f"[SUCCESS] {success_msg}")
        return True, success_msg  

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        print(f"[ERROR] Failed to send visitor notification: {error_msg}")
        return False, error_msg

    
class IncidentData(BaseModel):
    caller_id: str
    short_description: str
    comments: str  # worknotes
    impact: Optional[int] = None  # 1, 2, 3
    urgency: Optional[int] = None  # 1, 2, 3


class IncidentExtractionResult(BaseModel):
    success: bool
    incident_data: Optional[IncidentData] = None
    error_reason: Optional[str] = None


# ---------------------------------------------------------
# Function — Extract incident info from transcript
# ---------------------------------------------------------
def extract_incident_info(transcript: str) -> IncidentExtractionResult:
    """
    Extracts ServiceNow incident creation details from a transcript.
    Mandatory fields: caller_id, short_description, comments
    Optional: impact, urgency
    """
    model = ChatOpenAI(model=openai_model)

    structured_model = model.with_structured_output(IncidentData)

    system_prompt = """
    You are an assistant that extracts ServiceNow incident details from a transcript.

    Extract:
    - caller_id (must be the ServiceNow username, e.g., 'abel.tuter' firstname.lastname)
    - short_description (one-sentence summary of the issue)
    - comments (technician or user notes about the problem)
    - impact (1, 2, or 3) — optional
    - urgency (1, 2, or 3) — optional

    Rules:
    - Do not fabricate data not present in the transcript.
    - If any required field is missing, leave it blank.
    """

    try:
        data: IncidentData = structured_model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ])
        
        # Validate mandatory fields
        mandatory = ["caller_id", "short_description", "comments"]
        missing = [f for f in mandatory if not getattr(data, f, "").strip()]
        if missing:
            return IncidentExtractionResult(
                success=False,
                error_reason=f"Missing mandatory fields: {', '.join(missing)}"
            )

        return IncidentExtractionResult(success=True, incident_data=data)

    except Exception as e:
        return IncidentExtractionResult(success=False, error_reason=str(e))


# ---------------------------------------------------------
# Function  — Send to ServiceNow API
# ---------------------------------------------------------
def create_servicenow_incident(incident_data: dict):
    """
    Creates a new ServiceNow incident using extracted incident data.
    Retries up to 2 times for recoverable errors (connection issues, 5xx responses).
    """
    flow_name = "it_request"
    servicenow_instance = os.getenv("SERVICENOW_URL")
    url = f"{servicenow_instance}/api/now/table/incident"

    username = os.getenv("SERVICENOW_USERNAME")
    password = os.getenv("SERVICENOW_PASSWORD")

    if not username or not password:
        error_msg = "ServiceNow credentials not found in environment variables."
        raise ValueError(error_msg)

    payload = {
            "caller_id": incident_data.get("caller_id") or "abel.tuter",
            "short_description": incident_data.get("short_description") or "No description provided",
            "comments": incident_data.get("comments", "")
    }

    if incident_data.get("impact"):
        payload["impact"] = str(incident_data.get("impact"))
    if incident_data.get("urgency"):
        payload["urgency"] = str(incident_data.get("urgency"))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Configure retries (2 retries → total of 3 attempts)
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=1,  # Wait 1s, then 2s between retries
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))

    try:
        response = session.post(
            url,
            auth=(username, password),
            headers=headers,
            json=payload,
            timeout=10
        )
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text[:500]}") 

        if response.status_code not in (200, 201):
            error_msg = f"ServiceNow API error: {response.status_code} {response.text}"
            raise Exception(f"{error_msg} (caller_id: {incident_data.caller_id})")

        response_data = response.json()
        incident_number = response_data.get("result", {}).get("number", "UNKNOWN_INCIDENT")

        print(f"[SUCCESS] Created ServiceNow incident: {incident_number}")
        return response_data

    except requests.RequestException as e:
        error_msg = f"Request failed after retries: {e}"
        raise Exception(error_msg)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        raise
    
def extract_user_data(file_data, category, file_name):
    flow_name = f"extract_data_transcript_{category}_data"

    try:
        if category == "maintenance_request":
            extracted_data = extract_maintenance_info(file_data)
            if extracted_data.success:
                user_data = {
                    "first_name": extracted_data.user_data.first_name,
                    "last_name": extracted_data.user_data.last_name,
                    "phone": extracted_data.user_data.phone,
                    "email": extracted_data.user_data.email,
                    "address": extracted_data.user_data.address,
                    "repair_type": extracted_data.user_data.repair_location,
                    "issue_location": extracted_data.user_data.issue_location,
                    "issue_area": extracted_data.user_data.issue_area,
                    "issue_type": extracted_data.user_data.issue_type,
                    "issue_detail": extracted_data.user_data.issue_detail or "Other",
                    "previous_issue": extracted_data.user_data.previous_issue,
                    "issue_text": extracted_data.user_data.issue_text,
                }

                if hasattr(extracted_data.user_data, "appointment_times"):
                    user_data["appointment_times"] = extracted_data.user_data.appointment_times
                if hasattr(extracted_data.user_data, "access_instructions"):
                    user_data["access_instructions"] = extracted_data.user_data.access_instructions

                return user_data
            else:
                msg = f"Maintenance extraction failed: {extracted_data.error_reason}"
                print(f"[ERROR] {msg}")
                result = PipelineResult(flow_name, False, error=msg, file_name=file_name)
                log_flow_outcome(result)
                return {}

        elif category == "it_request":
            extracted_incident = extract_incident_info(file_data)
            if extracted_incident.success:
                return {
                    "caller_id": extracted_incident.incident_data.caller_id,
                    "short_description": extracted_incident.incident_data.short_description,
                    "comments": extracted_incident.incident_data.comments,
                    "impact": extracted_incident.incident_data.impact,
                    "urgency": extracted_incident.incident_data.urgency
                }
            else:
                msg = f"IT extraction failed: {extracted_incident.error_reason}"
                print(f"[ERROR] {msg}")
                result = PipelineResult(flow_name, False, error=msg, file_name=file_name)
                log_flow_outcome(result)
                return {}

        elif category == "visitor_check_in":
            extracted_visitor = extract_visitor_info(file_data)
            if extracted_visitor.success:
                visitor = extracted_visitor.visitor_data
                return {
                    "full_name": visitor.full_name,
                    "company": visitor.company,
                    "purpose": visitor.purpose,
                    "check_in_time": visitor.check_in_time,
                    "notes": visitor.notes,
                    "host_name": visitor.host_name
                }
            else:
                msg = f"Visitor extraction failed: {extracted_visitor.error_reason}"
                print(f"[ERROR] {msg}")
                result = PipelineResult(flow_name, False, error=msg, file_name=file_name)
                log_flow_outcome(result)
                return {}

        else:
            msg = f"Unknown category '{category}'"
            result = PipelineResult(flow_name, False, error=msg, file_name=file_name)
            log_flow_outcome(result)
            return {}

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] Exception during extraction: {error_msg}")
        result = PipelineResult(flow_name, False, error=error_msg,file_name=file_name)
        log_flow_outcome(result)
        return {}
