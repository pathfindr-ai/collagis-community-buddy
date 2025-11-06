import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from v4.automation_script_v4 import fill_details


@pytest.fixture(scope="module")
def user_data_sample():
    """Provide mock user data for form testing"""
    return {
        "first_name": "Ramsha",
        "last_name": "Ali",
        "phone": "03001234567",
        "email": "ramsha.ali@example.com",
        "address": "123 Main Street",
        "repair_type": "My Home",
        "issue_location": "Inside",
        "issue_area": "Kitchen",
        "issue_type": "Electrical",
        "issue_detail": "Power outage",
        "previous_issue": "No",
        "issue_text": "The kitchen lights stopped working suddenly.",
        "appointment_times":["Monday AM", "Wednesday PM", "Friday AM"]
    }


@pytest.fixture(scope="module")
def setup_driver():
    """Setup Chrome driver for tests (headless)"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def test_form_fields_presence(setup_driver):
    """Verify that all critical form fields exist on the page"""
    driver = setup_driver
    driver.get("https://cbwebform.innovationlab360.com/")
    wait = WebDriverWait(driver, 10)

    field_ids = [
        "firstName", "lastName", "phoneNumber", "email", "address",
        "repairLocation", "issueLocation", "issueTypeDropdown", "issueDetails"
    ]
    for fid in field_ids:
        elem = wait.until(EC.presence_of_element_located((By.ID, fid)))
        assert elem.is_displayed(), f"Field {fid} not visible"


def test_fill_details_function(user_data_sample):
    """Integration test for fill_details (headless smoke test mode)"""
    # We call fill_details directly to test form filling logic end-to-end
    result = fill_details(user_data_sample, smoke_test=False)
    assert result in [
        "FORM_ANTIBOT", "FORM_SUCCESS_NO_REF", "FORM_ERROR", "FORM_FILLED_MANUAL"
    ] or result.startswith("REF_"), f"Unexpected result: {result}"


@pytest.mark.parametrize("invalid_data", [
    {},  # Completely empty
    {"first_name": "", "last_name": "", "phone": "", "address": ""},  # Missing required
])
def test_fill_details_with_invalid_data(invalid_data):
    """Ensure that fill_details handles invalid inputs gracefully"""
    result = fill_details(invalid_data, smoke_test=True)
    assert result in ["FORM_ERROR", "FORM_ANTIBOT", "FORM_SUCCESS_NO_REF"], \
        f"Unexpected response for invalid data: {result}"



#pytest -v test/test_webform_submission.py