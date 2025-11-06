# test_detect_language.py
import json
import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from v4.automation_script_v4 import detect_language

@pytest.mark.parametrize("case", json.load(open("golden.json", encoding="utf-8")))
def test_language_detection(case):
    text = case["text"]
    expected = case["expected"]
    detected = detect_language(text)
    assert detected == expected, f"Text: {text}, Expected: {expected}, Got: {detected}"
