import datetime
import os, json
import traceback
import csv
from dotenv import load_dotenv
load_dotenv()

REPORTS_FILE = os.getenv("REPORTS_FILE", "./assets/reports/flow_reports.json")
CSV_FILE = os.getenv("ERROR_FILE", "./assets/reports/error_report.csv")

class PipelineResult:
    def __init__(self, flow_name, success, reference=None, error=None, screenshot_path=None, file_name=None):
        self.flow_name = flow_name
        self.success = success
        self.reference = reference
        self.error = error
        self.screenshot_path = screenshot_path
        self.timestamp = datetime.datetime.now().isoformat()
        self.file_name = file_name

def log_flow_outcome(result: PipelineResult):
    """Append pipeline result to JSON log and log errors to CSV if failed."""
    log_entry = {
        "flow": result.flow_name,
        "success": result.success,
        "reference": result.reference,
        "error": result.error,
        "screenshot_path": result.screenshot_path,
        "timestamp": result.timestamp
    }
    if getattr(result, "file_name", None): 
        log_entry["file_name"] = result.file_name

    # --- Write to JSON report ---
    try:
        if os.path.exists(REPORTS_FILE):
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
                except json.JSONDecodeError:
                    # Handle empty or invalid JSON
                    existing = []
        else:
            existing = []

        existing.append(log_entry)

        os.makedirs(os.path.dirname(REPORTS_FILE), exist_ok=True)
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    except Exception as e:
        print(f"[WARN] Could not write to {REPORTS_FILE}: {e}")

    # --- Write error report to CSV if failed ---
    try:
        if not result.success:
            # os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

            file_exists = os.path.exists(CSV_FILE)
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Flow", "File Name", "Error"])
                writer.writerow([
                    result.timestamp,
                    result.flow_name,
                    result.file_name or "",
                    result.error or "Unknown error"
                ])
    except Exception as e:
        print(f"[WARN] Could not write to error_report.csv: {e}")
