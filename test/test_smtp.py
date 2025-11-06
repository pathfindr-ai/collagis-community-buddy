import os
import pytest
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from v4.extract_data_v4 import send_visitor_notification

# Load environment variables from .env
load_dotenv()

@pytest.mark.integration
def test_send_visitor_notification_smtp():
    """
    Integration test: Sends a real email using Azure SMTP Relay.
    Requires these environment variables:
      - SMTP_SERVER
      - SMTP_PORT
      - SMTP_USERNAME
      - SMTP_PASSWORD
      - SENDER_EMAIL
      - HOSTS_CSV_PATH
    """

    # --- Environment sanity checks ---
    csv_path = os.getenv("HOSTS_CSV_PATH")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL")

    assert smtp_server, "SMTP_SERVER not found in environment"
    assert smtp_username, "SMTP_USERNAME not found in environment"
    assert smtp_password, "SMTP_PASSWORD not found in environment"
    assert sender_email, "SENDER_EMAIL not found in environment"
    assert os.path.exists(csv_path), f"CSV file not found: {csv_path}"

    # --- Dummy visitor data for test email ---
    visitor_data = {
        "full_name": "Alice Johnson",
        "company": "Innotech Ltd.",
        "purpose": "Project Meeting",
        "check_in_time": "10:30 AM",
        "notes": "Arrived early, waiting in reception.",
        "host_name": "John Smith"  # must exist in your CSV
    }

    print("\n--- Running SMTP email integration test ---")
    print(f"SMTP Server: {smtp_server}")
    print(f"Sender: {sender_email}")
    print(f"CSV Path: {csv_path}")
    print(f"Host Name: {visitor_data['host_name']}")
    print("Expecting email in host's inbox shortly...\n")

    # --- Call actual function ---
    success, message = send_visitor_notification(visitor_data, csv_path)

    # --- Verify ---
    assert success, f"Expected email send success, got failure: {message}"

    print(f"\n✅ SMTP email test passed.\nMessage: {message}\n")



#pytest -v test/test_smtp.py
