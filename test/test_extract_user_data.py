import pytest
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
from deepeval import evaluate
from dotenv import load_dotenv
load_dotenv()
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from v4.extract_data_v4 import extract_user_data


def test_extract_user_data_maintenance_semantic():
    """
    Semantic test for maintenance_request extraction.
    Ensures the LLM correctly identifies user details, issue type, and related fields.
    Optional fields (appointment_times, issue_text) are handled gracefully.
    """
    transcript = """
    John Doe called to report that the lights in the carport keep flickering, 
    and sometimes when he turns on the switch, there is a small spark. 
    The issue is electrical and located outside his home in the carport area. 
    He lives at 87 McPherson Road, Yallambie, Victoria, 3690. 
    His phone number is 0512-296-184 and his email is johndoe1@gmail.com. 
    He mentioned that this issue has been raised before within the last six months.
    """

    expected_output = {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "0512-296-184",
        "email": "johndoe1@gmail.com",
        "address": "87 McPherson Road, Yallambie, Victoria, 3690",
        "repair_type": "My Home",
        "issue_location": "Outside",
        "issue_area": "Carport",
        "issue_type": "Electrical",
        "issue_detail": "Other",
        "previous_issue": "Yes",
        "issue_text": "lights in the carport flicker and a small spark appears when turning on the switch",
        "appointment_times": None
    }

    actual_output = extract_user_data(transcript, "maintenance_request")

    actual_text = str(actual_output)
    expected_text = str(expected_output)

    metric = AnswerRelevancyMetric(threshold=0.7)

    test_case = LLMTestCase(
        input=transcript,
        actual_output=actual_text,
        expected_output=expected_text,
        retrieval_context=["maintenance_request extraction"]
    )

    result = evaluate([test_case], metrics=[metric])
    test_result = result.test_results[0]
    metric_result = test_result.metrics_data[0]
    score = metric_result.score
    reason = metric_result.reason

    print(f"Answer Relevancy Score: {score:.2f}")
    print(f"Reason: {reason}")

    assert score >= 0.7, f"Extraction accuracy below threshold (score={score:.2f})"


def test_extract_user_data_it_request_semantic():
    """
    Semantic test for it_request extraction.
    Ensures the LLM correctly identifies caller_id, short_description, and comments.
    """
    transcript = """
    Abel Tuter reported that he cannot connect to the office WiFi 
    even after restarting his laptop. He said this issue started today.
    """

    expected_output = {
        "caller_id": "abel.tuter",
        "short_description": "Unable to connect to WiFi",
        "comments": "User unable to connect to office WiFi after troubleshooting",
        "impact": 2,
        "urgency": 2
    }

    actual_output = extract_user_data(transcript, "it_request")

    actual_text = str(actual_output)
    expected_text = str(expected_output)

    metric = AnswerRelevancyMetric(threshold=0.7)

    test_case = LLMTestCase(
        input=transcript,
        actual_output=actual_text,
        expected_output=expected_text,
        retrieval_context=["it_request extraction"]
    )

    result = evaluate([test_case], metrics=[metric])
    test_result = result.test_results[0]
    metric_result = test_result.metrics_data[0]
    score = metric_result.score
    reason = metric_result.reason

    print(f"Answer Relevancy Score: {score:.2f}")
    print(f"Reason: {reason}")

    assert score >= 0.7, f"Semantic mismatch in it_request (score={score:.2f})"



def test_extract_user_data_unknown_category():
    """
    Ensures function returns empty dict for unsupported categories.
    """
    transcript = "This is a random unrelated message."
    result = extract_user_data(transcript, "visitor_request")

    assert result == {}, "Expected empty dict for unsupported category"

def test_extract_user_data_visitor_checkin_semantic():
    """
    Semantic test for visitor_check_in extraction.
    Ensures the LLM correctly identifies visitor details such as name, company, purpose, host, and notes.
    """
    transcript = """
    Alice Johnson arrived from TechCorp to meet John Smith 
    for a Level 2 meeting area discussion about partnership expansion. 
    She checked in at 10:15 AM and mentioned she would need WiFi access during her stay.
    """

    expected_output = {
        "full_name": "Alice Johnson",
        "company": "TechCorp",
        "purpose": "Meeting about partnership expansion",
        "check_in_time": "10:15 AM",
        "notes": "Needs WiFi access during her stay",
        "host_name": "John Smith"
    }

    actual_output = extract_user_data(transcript, "visitor_check_in")

    actual_text = str(actual_output)
    expected_text = str(expected_output)

    metric = AnswerRelevancyMetric(threshold=0.7)

    test_case = LLMTestCase(
        input=transcript,
        actual_output=actual_text,
        expected_output=expected_text,
        retrieval_context=["visitor_check_in extraction"]
    )

    result = evaluate([test_case], metrics=[metric])
    test_result = result.test_results[0]
    metric_result = test_result.metrics_data[0]
    score = metric_result.score
    reason = metric_result.reason

    print(f"Answer Relevancy Score: {score:.2f}")
    print(f"Reason: {reason}")

    assert score >= 0.7, f"Semantic mismatch in visitor_check_in (score={score:.2f})"


#pytest -v test/test_extract_user_data.py