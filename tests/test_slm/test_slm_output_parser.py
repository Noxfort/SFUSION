import pytest
from src.slm.slm_output_parser import SLMOutputParser

def test_extract_last_json():
    text = "Some text before { 'invalid': json } { \"valid\": \"json\" } text after"
    result = SLMOutputParser.extract_last_json(text)
    assert result == {"valid": "json"}

def test_extract_last_json_none():
    assert SLMOutputParser.extract_last_json("No json here") == {}

def test_extract_thinking_with_tags():
    text = "<think>I am thinking</think>\n{\"data\": \"value\"}"
    assert SLMOutputParser.extract_thinking(text) == "I am thinking"

def test_extract_thinking_no_tags():
    text = "I am thinking about this.\n{\"data\": \"value\"}"
    assert SLMOutputParser.extract_thinking(text) == "I am thinking about this."

def test_build_schema_data():
    raw = {"valid": "123", "empty": "", "null_str": "NULL", "none_str": "None", "real_null": None}
    clean = SLMOutputParser.build_schema_data(raw)
    assert "valid" in clean
    assert "empty" not in clean
    assert "null_str" not in clean

def test_fallback_line_parse():
    text = "speed_col=v\nflow_col=NULL\nintensity_col=k"
    parsed = SLMOutputParser.fallback_line_parse(text)
    assert parsed.get("speed_col") == "v"
    assert "flow_col" not in parsed
    assert parsed.get("intensity_col") == "k"

def test_parse_full():
    text = "<think>Reasoning...</think>\n{\"speed_col\": \"v\"}"
    thinking, data = SLMOutputParser.parse(text)
    assert thinking == "Reasoning..."
    assert data == {"speed_col": "v"}

def test_parse_fallback():
    text = "<think>Reasoning...</think>\nspeed_col=v"
    thinking, data = SLMOutputParser.parse(text)
    assert thinking == "Reasoning..."
    assert data == {"speed_col": "v"}
