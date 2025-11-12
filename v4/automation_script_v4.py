import time
from v4.extract_data_v4 import translate_improve_transcript, classify_transcript, extract_user_data, extract_incident_info, create_servicenow_incident,send_visitor_notification
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import os,sys,platform,glob
from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException
from v4.reporting import PipelineResult, log_flow_outcome
from v4.ledger_db import load_ledger, save_ledger, auto_cleanup, is_processed
import fcntl, tempfile
# import msvcrt  # For single instance lock
import shutil
import hashlib
import json
from dotenv import load_dotenv

load_dotenv()



def setup_webdriver():
    driver = webdriver.Chrome()
    return driver

# def setup_webdriver():
#     options = Options()
#     options.add_argument("--headless=new")  # headless mode
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     driver = webdriver.Chrome(options=options)
#     return driver

def fill_details(user_data, smoke_test, file_name, screenshots_dir="./assets/screenshots"):
    # driver = setup_webdriver()
    driver = webdriver.Chrome() # for testing purposes 
    flow_name = "maintenance_request"
    screenshot_path=None
    driver.get("https://cbwebform.innovationlab360.com/")

    wait = WebDriverWait(driver, 10)

    try:
        # ------------------- CONTACT DETAILS -------------------
        wait.until(EC.presence_of_element_located((By.ID, "firstName"))).send_keys(user_data["first_name"])
        driver.find_element(By.ID, "lastName").send_keys(user_data["last_name"])
        driver.find_element(By.ID, "phoneNumber").send_keys(user_data["phone"])
        if user_data.get("email"):
             driver.find_element(By.ID, "email").send_keys(user_data["email"])
        driver.find_element(By.ID, "address").send_keys(user_data["address"])

        # ------------------- REPAIR DETAILS -------------------
        Select(driver.find_element(By.ID, "repairLocation")).select_by_visible_text(user_data["repair_type"])
        Select(driver.find_element(By.ID, "issueLocation")).select_by_visible_text(user_data["issue_location"])

        # Handle Inside / Outside branching
        if user_data["repair_type"] == "My Home":
            if user_data["issue_location"] == "Inside":
                Select(driver.find_element(By.ID, "insideArea")).select_by_visible_text(user_data["issue_area"])
            else:
                Select(driver.find_element(By.ID, "outsideArea")).select_by_visible_text(user_data["issue_area"])
        else:  # Common Area
            if user_data["issue_location"] == "Inside":
                Select(driver.find_element(By.ID, "commonInsideArea")).select_by_visible_text(user_data["issue_area"])
            else:
                Select(driver.find_element(By.ID, "commonOutsideArea")).select_by_visible_text(user_data["issue_area"])

        # Issue Type
        Select(driver.find_element(By.ID, "issueTypeDropdown")).select_by_visible_text(user_data["issue_type"])

        # Issue Detail (populated dynamically – wait for it)
        try:
            issue_detail_dropdown = wait.until(EC.presence_of_element_located((By.ID, "issueDetailDropdown")))
            # Wait for the correct option text to appear
            wait.until(lambda d: any(opt.text == user_data["issue_detail"] for opt in issue_detail_dropdown.find_elements(By.TAG_NAME, "option")))
            Select(issue_detail_dropdown).select_by_visible_text(user_data["issue_detail"])
        except TimeoutException:
            print(f"Warning: issue detail '{user_data['issue_detail']}' not found in dropdown.")

        # Raised in last 6 months
        if user_data.get("previous_issue", "No") == "Yes":
            driver.find_element(By.ID, "previousIssue").click()

        # Extra Details
        driver.find_element(By.ID, "issueDetails").send_keys(user_data["issue_text"])

        # ------------------- APPOINTMENT -------------------
        if user_data.get("appointment_times"):   # only run if list is present & not None
            for slot in user_data["appointment_times"]:
                xpath = f"//input[@type='checkbox' and @value='{slot}']"
                try:
                    driver.find_element(By.XPATH, xpath).click()
                except Exception as e:
                    print(f"Could not click appointment slot: {slot} error {e}")
                    
        if user_data.get("access_instructions"):
            try:
                access_field = driver.find_element(By.ID, "accessInstructions")
                access_field.clear()
                access_field.send_keys(user_data["access_instructions"])
                print(f"Access instructions filled: {user_data['access_instructions']}")
            except Exception as e:
                print(f"Warning: Could not fill access instructions: {e}")


        # ------------------- SUBMIT -------------------
        if smoke_test:
            print(" Running smoke test (headless submission)...")

            # Wait until the 'Submit Request' button is clickable
            submit_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-primary[type='submit']"))
            )
            submit_button.click()

            try:
                # Wait for success or antibot screen
                success_selector = (By.XPATH, "//*[contains(text(),'Reference') or contains(text(),'successfully') or contains(text(),'request has been submitted')]")
                antibot_selector = (By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'robot') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'captcha')]")

                wait.until(lambda d: d.find_elements(*success_selector) or d.find_elements(*antibot_selector))

                if driver.find_elements(*antibot_selector):
                    print("Anti-bot page or CAPTCHA detected. Returning FORM_ANTIBOT.")
                    return "FORM_ANTIBOT"

                # Try to get confirmation text
                success_elements = driver.find_elements(*success_selector)
                if success_elements:
                    ref_text = success_elements[0].text
                    import re
                    match = re.search(r"\b[A-Z0-9]{6,}\b", ref_text)
                    reference = match.group(0) if match else "UNKNOWN_REF"
                    print(f"Form submitted successfully. Reference: {reference}")
                    result = PipelineResult(flow_name, True, reference=reference, file_name=file_name)
                    log_flow_outcome(result)
                    return reference

                print("Submission completed but no reference text found.")
                return "FORM_SUCCESS_NO_REF"

            except TimeoutException:
                print("No success or antibot screen detected within timeout. Possibly blocked or failed.")
                result = PipelineResult(flow_name, True, reference="FORM_ANTIBOT", file_name=file_name)
                log_flow_outcome(result)
                return "FORM_ANTIBOT"

        else:
            # Manual testing mode (non-headless)
            print("Manual testing mode active — form will stay open for 2 minutes for inspection.")
            result = PipelineResult(flow_name, True, reference="FORM_FILLED_MANUAL", file_name=file_name)
            log_flow_outcome(result)
            time.sleep(120)
            print("Form filled successfully (not submitted).")
            return "FORM_FILLED_MANUAL"

        

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] {flow_name} failed: {error_msg}")
        screenshot_path = os.path.join(screenshots_dir, f"{flow_name}_{int(time.time())}.png")
        os.makedirs("screenshots", exist_ok=True)
        driver.save_screenshot(screenshot_path)
        result = PipelineResult(flow_name, False, error=error_msg, screenshot_path=screenshot_path, file_name=file_name)
        log_flow_outcome(result)
        return "FORM_ERROR"
        
    finally:
        if smoke_test:
            driver.quit()



# Only allow English, Hindi, Vietnamese, Bahasa Indonesia
LANGS_ENABLED = {"en", "hi", "vi", "id"}


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.
    Falls back to English if not in LANGS_ENABLED or if unknown.
    Ensures deterministic results (UTF-8 safe).
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a UTF-8 string")

    try:
        # detect_langs gives probabilities
        langs = detect_langs(text)
        if not langs:
            raise LangDetectException("No language detected")

        # pick top candidate
        top = langs[0]
        lang = top.lang
        confidence = top.prob

        # Check against allowed set
        if lang not in LANGS_ENABLED:
            print(f"Language '{lang}' not enabled. Falling back to English.")
            return "not found"

        # If confidence too low, fallback
        if confidence < 0.70:  # configurable threshold
            print(f"Low confidence ({confidence:.2f}) for '{lang}'. Falling back to English.")
            return "en"

        return lang

    except LangDetectException:
        print("Language detection failed. Falling back to English.")
        return "not found"

def process_request(user_data, category, file_path, processed_dir, screenshots_dir):
    """
    Process user request based on category.
    - For maintenance_request → fills details in web form.
    - For it_request → creates ServiceNow incident.
    - Moves the processed file after completion.
    """
    try:
        if category == "maintenance_request":
            SMOKE_TEST = os.getenv("SMOKE_TEST", "False").lower() == "true"
            result= fill_details(user_data, SMOKE_TEST, os.path.basename(file_path), screenshots_dir)
            print("Maintenance request processed successfully.")
            if result in ["FORM_ERROR", "FORM_ANTIBOT"] :
                return False
            
        elif category == "it_request":  
            try:
                    response = create_servicenow_incident(user_data)
                    incident_number = response.get("result", {}).get("number", "UNKNOWN_INCIDENT")
                    # Log successful outcome
                    result = PipelineResult("it_request", True, reference=incident_number, file_name=os.path.basename(file_path))
                    log_flow_outcome(result)
            except Exception as e:
                    print(f"Failed to create ServiceNow incident: {e}")
                    result = PipelineResult("it_request", False, error=f"Failed to create ServiceNow incident: {e}", file_name=os.path.basename(file_path))
                    log_flow_outcome(result)
                    return False
        elif category == "visitor_check_in":
            try:
                csv_path = os.getenv("HOSTS_CSV_PATH")
                if not csv_path:
                    print("[ERROR] CSV path for host lookup not provided.")
                    result = PipelineResult("visitor_check_in", False, error="CSV path not provided", file_name=os.path.basename(file_path))
                    log_flow_outcome(result)
                    return False

                success, message = send_visitor_notification(user_data, csv_path)

                if success:
                    print(f"Visitor check-in email sent for {user_data.get('full_name', 'Unknown Visitor')}.")
                    result = PipelineResult("visitor_check_in", True, reference=message, file_name=os.path.basename(file_path))
                    log_flow_outcome(result)
                else:
                    print(f"Failed to send visitor email for {user_data.get('full_name', 'Unknown Visitor')}.")
                    result = PipelineResult("visitor_check_in", False, error=message, file_name=os.path.basename(file_path))
                    log_flow_outcome(result)
                    return False

                
                

            except Exception as e:
                error_msg = f"Failed to send visitor check-in email: {e}"
                print(error_msg)
                result = PipelineResult("visitor_check_in", False, error=error_msg, file_name=os.path.basename(file_path))
                log_flow_outcome(result)
                return False


        else:
            print(f"Unknown category: {category}")
            return False

        # Move file to processed folder
        file_name = os.path.basename(file_path)
        shutil.move(file_path, os.path.join(processed_dir, file_name))
        print(f"Moved {file_name} → {processed_dir}")

        return True

    except Exception as e:
        print(f"Error while processing request: {e}")
        error_msg=f"Error while processing request: {e}"
        result = PipelineResult(category, False, error=error_msg, file_name=os.path.basename(file_path))
        log_flow_outcome(result)
        return False




# ------------------ Single Instance Lock ------------------
def single_instance_lock():
    lock_path = os.path.join(tempfile.gettempdir(), "collagis_automation.lock")
    try:
        lock_file = open(lock_path, "w")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(f"[LOCK] Acquired lock at {lock_path}")
        return lock_file
    except (OSError, IOError):
        print(f"[LOCK] Another instance is already running (lock: {lock_path})")
        sys.exit(0)


# ------------------ File Hashing ------------------
def file_hash(file_path):
    """
    Generate a SHA256 hash based on the file name only (not contents).
    """
    # Use only the file name (not full path) for stable hashing
    file_name = os.path.basename(file_path)
    return hashlib.sha256(file_name.encode("utf-8")).hexdigest()

# ------------------ File Processing ------------------
def process_file(file_path, processed_dir, failed_dir, screenshots_dir):
    file_name = os.path.basename(file_path)
    print(f"\nProcessing File: {file_name}")
    flow_name = "file_processing"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_data = f.read()

        # ---- pipeline ----
        lang_code = detect_language(file_data)
        print(f"Detected Language: {lang_code}")
        
        if lang_code == "not found":
            msg = f"Unsupported or unknown language for {file_name}"
            print(f"Skipping {file_name}: Unsupported or unknown language.")
            shutil.move(file_path, os.path.join(failed_dir, file_name))
            print(f"Moved {file_name} → {failed_dir}")
            result = PipelineResult(flow_name, False, error=msg, file_name=file_name)
            log_flow_outcome(result)
            return False
        
        improved_transcript = translate_improve_transcript(file_data)
        print("Transcript:", improved_transcript)

        category = classify_transcript(improved_transcript)
        print("Category:", category)
        
        if category == "not_found":
            msg = f"Category not identified for {file_name}"
            print(f"[ERROR] {msg}")
            shutil.move(file_path, os.path.join(failed_dir, file_name))
            print(f"Moved {file_name} → {failed_dir}")
            result = PipelineResult(flow_name, False, error=msg, file_name=file_name)
            log_flow_outcome(result)
            return False

        user_data = extract_user_data(improved_transcript, category, file_name)
        print("User Data:", user_data)
        if not user_data:
            print(f"Skipping {file_name}: No user data extracted.")
            shutil.move(file_path, os.path.join(failed_dir, file_name))
            print(f"Moved {file_name} → {failed_dir}")
            return False
        
        result= process_request(user_data, category, file_path, processed_dir, screenshots_dir)
        if not result:
            shutil.move(file_path, os.path.join(failed_dir, file_name))
            print(f"Moved {file_name} → {failed_dir}")
        return result
            

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[ERROR] Error processing {file_name}: {error_msg}")
        shutil.move(file_path, os.path.join(failed_dir, file_name))
        print(f"Moved {file_name} → {failed_dir}")

        result = PipelineResult(flow_name, False, error=error_msg, file_name=file_name)
        log_flow_outcome(result)
        return False

# ------------------ Main ------------------
def main():
    folder_path = os.getenv("TRANSCRIPTS_FOLDER")
    processed_dir = os.path.join(folder_path, "processed")
    failed_dir = os.path.join(folder_path, "failed")
    screenshots_dir = os.path.join(folder_path, "screenshots")
    
    reports_file = os.getenv("REPORTS_FILE")
    error_file = os.getenv("ERROR_FILE")

    # Derive base reports directory from the report file path
    report_dir = os.path.dirname(reports_file) if reports_file else os.path.join(folder_path, "reports")

    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(screenshots_dir, exist_ok=True)

    # Ensure only one instance is running
    lock_file = single_instance_lock()

    # macOS dir fix
    if platform.system() == "Darwin":
        dir = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1])
        os.chdir(dir)

    cleanup_days = int(os.getenv("LEDGER_CLEANUP_DAYS", "90"))
    try:
        auto_cleanup(days=cleanup_days)
    except Exception as e:
        print(f"[WARN] Auto cleanup skipped: {e}")
    # Load already processed hashes (now from SQLite!)
    # Read env variable and convert to boolean
    load_all_hashes = os.getenv("LOAD_ALL_HASHES", "False").lower() in ("true", "1", "yes")

    
    # set False for large datasets

    # Load processed hashes
    processed_hashes = load_ledger(load_all=load_all_hashes)

    # Find all log files
    log_files = sorted(glob.glob(os.path.join(folder_path, "*.txt")))
    print("hello: ", load_all_hashes)

    # Filter unprocessed files
    if load_all_hashes:
        # Small dataset: compare with in-memory set
        unprocessed_files = [(f, file_hash(f)) for f in log_files if file_hash(f) not in processed_hashes]
    else:
        # Large dataset: check each file lazily
        print("Large dataset mode")
        unprocessed_files = []
        for f in log_files:
            h = file_hash(f)
            if not is_processed(h):
                unprocessed_files.append((f, h))

    if not unprocessed_files:
        print(f"No new log files found in {folder_path}.")
        return

    # Batch size from environment variable (default=10)
    batch_size = int(os.getenv("BATCH_SIZE", "10"))
    files_to_process = unprocessed_files[:batch_size]

    print(f"Found {len(files_to_process)} file(s) to process this run (batch size = {batch_size}).\n")

    for file_path, h in files_to_process:
        success = process_file(file_path, processed_dir, failed_dir, screenshots_dir)
        if success:
            processed_hashes.add(h)

    # Save updated ledger
    save_ledger(processed_hashes)

    # Release lock when done
    lock_file.close()


if __name__ == "__main__":
    main()



#python -m v4.automation_script_v4